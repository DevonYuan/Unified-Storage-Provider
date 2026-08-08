"""Authentication router for OmniDrive - OAuth flows for cloud providers."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse, HTMLResponse


def _js_redirect(url: str) -> HTMLResponse:
    """Return an HTML page that navigates back to the Electron frontend.

    Uses Electron's IPC (via preload script) to avoid Chromium's
    cross-protocol redirect block (http→file://).
    """
    # Extract the hash from the target URL for the frontend route
    hash_part = url.split("#")[1] if "#" in url else ""
    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>OmniDrive</title>
<style>body{{background:#0a0a0a;color:#fafafa;font-family:system-ui,sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;margin:0}}p{{font-size:14px;color:#8a8a8a}}</style></head>
<body>
<p>Authentication complete — returning to OmniDrive…</p>
<script>
(function() {{
  if (window.omnidrive && window.omnidrive.navigateTo) {{
    window.omnidrive.navigateTo('{hash_part}');
  }} else {{
    window.location.href = 'http://localhost:5173/#/{hash_part}';
  }}
}})();
</script>
</body></html>"""
    return HTMLResponse(content=html)
from sqlalchemy.orm import Session
from pydantic import BaseModel, HttpUrl
from typing import Optional
from datetime import datetime, timedelta

from database_driver import get_db
from models import ConnectedAccount, ProviderType
from services.google_oauth import (
    build_authorization_url,
    validate_state,
    exchange_code_for_tokens,
    get_user_info,
    store_refresh_token,
    get_keyring_key,
    GoogleOAuthError,
)
from services.microsoft_oauth import (
    build_authorization_url as build_ms_auth_url,
    validate_state as validate_ms_state,
    exchange_code_for_tokens as exchange_ms_code,
    get_user_info as get_ms_user_info,
    store_refresh_token as store_ms_refresh_token,
    get_keyring_key as get_ms_keyring_key,
    MicrosoftOAuthError,
)
from config import get_config

router = APIRouter(prefix="/auth", tags=["Authentication"])


class OAuthStartRequest(BaseModel):
    provider: ProviderType
    redirect_uri: str
    frontend_url: str = ""


class OAuthStartResponse(BaseModel):
    auth_url: str
    state: str


class AccountResponse(BaseModel):
    id: int
    provider: ProviderType
    display_name: str
    keyring_key: str
    token_expiry: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AccountListResponse(BaseModel):
    accounts: list[AccountResponse]


@router.post("/oauth/start", response_model=OAuthStartResponse)
def start_oauth(request: OAuthStartRequest):
    """
    Initiate OAuth flow for a cloud storage provider.
    Returns the authorization URL and state parameter.
    """
    if request.provider == ProviderType.GOOGLE_DRIVE:
        auth_url, state = build_authorization_url(request.redirect_uri, request.frontend_url)
    elif request.provider == ProviderType.ONEDRIVE:
        auth_url, state = build_ms_auth_url(request.redirect_uri, request.frontend_url)
    else:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=f"OAuth flow for {request.provider.value} not implemented yet"
        )

    return OAuthStartResponse(auth_url=auth_url, state=state)


@router.get("/google/callback")
async def google_oauth_callback(code: str, state: str, db: Session = Depends(get_db)):
    """
    Handle OAuth callback from Google (redirect endpoint).
    This is the actual redirect URI registered in Google Cloud Console.
    Exchanges authorization code for tokens and stores them securely.
    """
    # Validate state parameter (CSRF protection)
    state_data = validate_state(state)
    if not state_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OAuth state parameter"
        )
    redirect_uri = state_data["redirect_uri"]
    frontend_url = state_data.get("frontend_url", "http://localhost:5173")

    # Verify the redirect URI matches our backend callback URL
    config = get_config()
    expected_redirect_uri = config.google_oauth.redirect_uri
    if redirect_uri != expected_redirect_uri:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Redirect URI mismatch"
        )

    try:
        # Exchange authorization code for tokens
        token_response = await exchange_code_for_tokens(code, redirect_uri)

        # Get user info from Google
        user_info = await get_user_info(token_response["access_token"])

        # Store refresh token securely in keyring
        keyring_key = get_keyring_key(user_info["id"])
        if token_response.get("refresh_token"):
            store_refresh_token(keyring_key, token_response["refresh_token"])

        # Calculate token expiry
        token_expiry = datetime.utcnow() + timedelta(seconds=token_response["expires_in"])

        # Create or update connected account
        existing_account = db.query(ConnectedAccount).filter(
            ConnectedAccount.provider == ProviderType.GOOGLE_DRIVE,
            ConnectedAccount.keyring_key == keyring_key
        ).first()

        if existing_account:
            account = existing_account
            account.display_name = user_info["email"]
            account.access_token = token_response["access_token"]
            account.refresh_token = token_response.get("refresh_token")
            account.token_expiry = token_expiry
            account.updated_at = datetime.utcnow()

            # Clean up any stale duplicate accounts for the same provider + keyring_key
            duplicates = db.query(ConnectedAccount).filter(
                ConnectedAccount.provider == ProviderType.GOOGLE_DRIVE,
                ConnectedAccount.keyring_key == keyring_key,
                ConnectedAccount.id != existing_account.id,
            ).all()
            for dup in duplicates:
                db.delete(dup)
        else:
            account = ConnectedAccount(
                provider=ProviderType.GOOGLE_DRIVE,
                display_name=user_info["email"],
                keyring_key=keyring_key,
                access_token=token_response["access_token"],
                refresh_token=token_response.get("refresh_token"),
                token_expiry=token_expiry,
            )
            db.add(account)

        db.commit()
        db.refresh(account)

        # Redirect back to frontend (works for both dev server and packaged Electron)
        target = f"{frontend_url}#/home" if existing_account else f"{frontend_url}#/signup"
        return _js_redirect(target)

    except GoogleOAuthError as e:
        target = f"{frontend_url}#/signup?error={e}"
        return _js_redirect(target)
    except Exception as e:
        target = f"{frontend_url}#/signup?error=OAuth callback failed: {str(e)}"
        return _js_redirect(target)


@router.get("/microsoft/callback")
async def microsoft_oauth_callback(code: str, state: str, db: Session = Depends(get_db)):
    """
    Handle OAuth callback from Microsoft (redirect endpoint).
    This is the actual redirect URI registered in Azure AD.
    Exchanges authorization code for tokens and stores them securely.
    """
    # Validate state parameter (CSRF protection)
    state_data = validate_ms_state(state)
    if not state_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OAuth state parameter"
        )
    redirect_uri = state_data["redirect_uri"]
    frontend_url = state_data.get("frontend_url", "http://localhost:5173")

    # Verify the redirect URI matches our backend callback URL
    config = get_config()
    expected_redirect_uri = config.microsoft_oauth.redirect_uri
    if redirect_uri != expected_redirect_uri:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Redirect URI mismatch"
        )

    try:
        # Exchange authorization code for tokens
        token_response = await exchange_ms_code(code, redirect_uri)

        # Get user info from Microsoft Graph
        user_info = await get_ms_user_info(token_response["access_token"])

        # Microsoft returns userPrincipalName or mail
        user_id = user_info.get("id", "")
        email = user_info.get("mail") or user_info.get("userPrincipalName", "Unknown")

        # Store refresh token securely in keyring
        keyring_key = get_ms_keyring_key(user_id)
        if token_response.get("refresh_token"):
            store_ms_refresh_token(keyring_key, token_response["refresh_token"])

        # Calculate token expiry
        token_expiry = datetime.utcnow() + timedelta(seconds=token_response["expires_in"])

        # Create or update connected account
        existing_account = db.query(ConnectedAccount).filter(
            ConnectedAccount.provider == ProviderType.ONEDRIVE,
            ConnectedAccount.keyring_key == keyring_key
        ).first()

        if existing_account:
            account = existing_account
            account.display_name = email
            account.access_token = token_response["access_token"]
            account.refresh_token = token_response.get("refresh_token")
            account.token_expiry = token_expiry
            account.updated_at = datetime.utcnow()

            # Clean up any stale duplicate accounts for the same provider + keyring_key
            duplicates = db.query(ConnectedAccount).filter(
                ConnectedAccount.provider == ProviderType.ONEDRIVE,
                ConnectedAccount.keyring_key == keyring_key,
                ConnectedAccount.id != existing_account.id,
            ).all()
            for dup in duplicates:
                db.delete(dup)
        else:
            account = ConnectedAccount(
                provider=ProviderType.ONEDRIVE,
                display_name=email,
                keyring_key=keyring_key,
                access_token=token_response["access_token"],
                refresh_token=token_response.get("refresh_token"),
                token_expiry=token_expiry,
            )
            db.add(account)

        db.commit()
        db.refresh(account)

        # Redirect back to frontend (works for both dev server and packaged Electron)
        target = f"{frontend_url}#/home" if existing_account else f"{frontend_url}#/signup"
        return _js_redirect(target)

    except MicrosoftOAuthError as e:
        target = f"{frontend_url}#/signup?error={e}"
        return _js_redirect(target)
    except Exception as e:
        target = f"{frontend_url}#/signup?error=OAuth callback failed: {str(e)}"
        return _js_redirect(target)


@router.get("/accounts", response_model=AccountListResponse)
def list_accounts(db: Session = Depends(get_db)):
    """List all connected cloud storage accounts."""
    accounts = db.query(ConnectedAccount).all()
    return {"accounts": [AccountResponse.model_validate(a) for a in accounts]}


@router.get("/accounts/{account_id}", response_model=AccountResponse)
def get_account(account_id: int, db: Session = Depends(get_db)):
    """Get a specific connected account by ID."""
    account = db.query(ConnectedAccount).filter(ConnectedAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return AccountResponse.model_validate(account)


@router.delete("/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(account_id: int, db: Session = Depends(get_db)):
    """Disconnect and remove a cloud storage account."""
    account = db.query(ConnectedAccount).filter(ConnectedAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    # TODO: Also remove tokens from keyring
    db.delete(account)
    db.commit()
    return None