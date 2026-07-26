"""Authentication router for OmniDrive - OAuth flows for cloud providers."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, HttpUrl
from typing import Optional
from datetime import datetime

from database_driver import get_db
from models import ConnectedAccount, ProviderType

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
    # TODO: Implement OAuth flow for Google Drive and Microsoft OneDrive
    # This will be implemented in Phase 2 (Google) and Phase 3 (OneDrive)
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"OAuth flow for {request.provider.value} not implemented yet"
    )


@router.post("/oauth/callback")
def oauth_callback(request: OAuthCallbackRequest):
    """
    Handle OAuth callback from provider.
    Exchanges authorization code for tokens and stores them securely.
    """
    # TODO: Implement OAuth callback handling
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"OAuth callback for {request.provider.value} not implemented yet"
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