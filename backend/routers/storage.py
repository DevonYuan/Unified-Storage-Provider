"""Storage router for OmniDrive - manages storage account operations."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from database_driver import get_db
from models import ConnectedAccount, ProviderType

router = APIRouter(prefix="/storage", tags=["Storage"])


class StorageInfo(BaseModel):
    """Storage information for a connected account."""
    account_id: int
    provider: ProviderType
    display_name: str
    total_space: Optional[int] = None
    used_space: Optional[int] = None
    available_space: Optional[int] = None
    last_synced: Optional[datetime] = None


class StorageListResponse(BaseModel):
    storage_accounts: list[StorageInfo]


@router.get("", response_model=StorageListResponse)
def list_storage_accounts(db: Session = Depends(get_db)):
    """List all connected storage accounts with their info."""
    accounts = db.query(ConnectedAccount).all()
    return StorageListResponse(
        storage_accounts=[
            StorageInfo(
                account_id=acc.id,
                provider=acc.provider,
                display_name=acc.display_name,
                total_space=None,
                used_space=None,
                available_space=None,
                last_synced=None,
            )
            for acc in accounts
        ]
    )


@router.get("/{account_id}", response_model=StorageInfo)
def get_storage_info(account_id: int, db: Session = Depends(get_db)):
    """Get storage information for a specific account."""
    account = db.query(ConnectedAccount).filter(ConnectedAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    return StorageInfo(
        account_id=account.id,
        provider=account.provider,
        display_name=account.display_name,
        total_space=None,
        used_space=None,
        available_space=None,
        last_synced=None,
    )


@router.post("/{account_id}/sync", status_code=status.HTTP_202_ACCEPTED)
def sync_storage(account_id: int, db: Session = Depends(get_db)):
    """Trigger a sync for a storage account (placeholder for future implementation)."""
    account = db.query(ConnectedAccount).filter(ConnectedAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    return {"message": f"Sync triggered for {account.display_name}", "status": "pending"}


@router.get("/accounts/total")
def get_total_storage(db: Session = Depends(get_db)):
    """Get combined storage across all providers (placeholder)."""
    accounts = db.query(ConnectedAccount).all()
    return {
        "total_space": None,
        "used_space": None,
        "available_space": None,
        "account_count": len(accounts),
        "message": "Total storage calculation will be implemented when provider APIs are integrated",
    }