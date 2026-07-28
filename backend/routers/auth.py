"""Authentication router for OmniDrive - OAuth flows for cloud providers."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, HttpUrl
from typing import Optional
from datetime import datetime

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
from config import get_config

router = APIRouter(prefix="/auth", tags=["Authentication"])


class OAuthStartRequest(BaseModel):
    provider: ProviderType
    redirect_uri: HttpUrl


class OAuthStartResponse(BaseModel):
    auth_url: str
    state: str


class OAuthCallbackRequest(BaseModel):
    provider: ProviderType
    code: str
    state: str
    redirect_uri: HttpUrl


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
    if request.provider != ProviderType.GOOGLE_DRIVE:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=f"OAuth flow for {request.provider.value} not implemented yet"
        )

    redirect_uri = str(request.redirect_uri)
    auth_url, state = build_authorization_url(redirect_uri)

    return OAuthStartResponse(auth_url=auth_url, state=state)


@router.get("/google/callback")
def google_oauth_callback(code: str, state: str, db: Session = Depends(get_db)):
    """
    Handle OAuth callback from Google (redirect endpoint).
    This is the actual redirect URI registered in Google Cloud Console.
    Exchanges authorization code for tokens and stores them securely.
    """
    # Validate state parameter (CSRF protection)
    redirect_uri = validate_state(state)
    if not redirect_uri:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OAuth state parameter"
        )

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
        import asyncio
        token_response = asyncio.run(exchange_code_for_tokens(code, redirect_uri))

        # Get user info from Google
        user_info = asyncio.run(get_user_info(token_response.access_token))

        # Store refresh token securely in keyring
        keyring_key = get_keyring_key(user_info.id)
        if token_response.refresh_token:
            store_refresh_token(keyring_key, token_response.refresh_token)

        # Calculate token expiry
        from datetime import timedelta
        token_expiry = datetime.utcnow() + timedelta(seconds=token_response.expires_in)

        # Create or update connected account
        existing_account = db.query(ConnectedAccount).filter(
            ConnectedAccount.provider == ProviderType.GOOGLE_DRIVE,
            ConnectedAccount.keyring_key == keyring_key
        ).first()

        if existing_account:
            account = existing_account
            account.display_name = user_info.email
            account.access_token = token_response.access_token
            account.refresh_token = token_response.refresh_token
            account.token_expiry = token_expiry
            account.updated_at = datetime.utcnow()
        else:
            account = ConnectedAccount(
                provider=ProviderType.GOOGLE_DRIVE,
                display_name=user_info.email,
                keyring_key=keyring_key,
                access_token=token_response.access_token,
                refresh_token=token_response.refresh_token,
                token_expiry=token_expiry,
            )
            db.add(account)

        db.commit()
        db.refresh(account)

        # Redirect back to frontend signup page
        frontend_url = "http://localhost:5173/signup"
        return RedirectResponse(url=frontend_url)

    except GoogleOAuthError as e:
        # Redirect to frontend with error
        frontend_url = f"http://localhost:5173/signup?error={e}"
        return RedirectResponse(url=frontend_url)
    except Exception as e:
        # Redirect to frontend with error
        frontend_url = f"http://localhost:5173/signup?error=OAuth callback failed: {str(e)}"
        return RedirectResponse(url=frontend_url)


@router.post("/oauth/callback")
def oauth_callback(request: OAuthCallbackRequest, db: Session = Depends(get_db)):
    """
    Handle OAuth callback from provider.
    Exchanges authorization code for tokens and stores them securely.
    """
    if request.provider != ProviderType.GOOGLE_DRIVE:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=f"OAuth callback for {request.provider.value} not implemented yet"
        )

    # Validate state parameter (CSRF protection)
    redirect_uri = validate_state(request.state)
    if not redirect_uri:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OAuth state parameter"
        )

    # Verify redirect URI matches
    if str(request.redirect_uri) != redirect_uri:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Redirect URI mismatch"
        )

    try:
        # Exchange authorization code for tokens
        import asyncio
        token_response = asyncio.run(exchange_code_for_tokens(request.code, redirect_uri))

        # Get user info from Google
        user_info = asyncio.run(get_user_info(token_response.access_token))

        # Store refresh token securely in keyring
        keyring_key = get_keyring_key(user_info.id)
        if token_response.refresh_token:
            store_refresh_token(keyring_key, token_response.refresh_token)

        # Calculate token expiry
        from datetime import timedelta
        token_expiry = datetime.utcnow() + timedelta(seconds=token_response.expires_in)

        # Create or update connected account
        existing_account = db.query(ConnectedAccount).filter(
            ConnectedAccount.provider == ProviderType.GOOGLE_DRIVE,
            ConnectedAccount.keyring_key == keyring_key
        ).first()

        if existing_account:
            account = existing_account
            account.display_name = user_info.email
            account.access_token = token_response.access_token
            account.refresh_token = token_response.refresh_token
            account.token_expiry = token_expiry
            account.updated_at = datetime.utcnow()
        else:
            account = ConnectedAccount(
                provider=ProviderType.GOOGLE_DRIVE,
                display_name=user_info.email,
                keyring_key=keyring_key,
                access_token=token_response.access_token,
                refresh_token=token_response.refresh_token,
                token_expiry=token_expiry,
            )
            db.add(account)

        db.commit()
        db.refresh(account)

        return AccountResponse.from_orm(account)

    except GoogleOAuthError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OAuth callback failed: {str(e)}"
        )


@router.get("/accounts", response_model=AccountListResponse)
def list_accounts(db: Session = Depends(get_db)):
    """List all connected cloud storage accounts."""
    accounts = db.query(ConnectedAccount).all()
    return {"accounts": accounts}


@router.get("/accounts/{account_id}", response_model=AccountResponse)
def get_account(account_id: int, db: Session = Depends(get_db)):
    """Get a specific connected account by ID."""
    account = db.query(ConnectedAccount).filter(ConnectedAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account


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