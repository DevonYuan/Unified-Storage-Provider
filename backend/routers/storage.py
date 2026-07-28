"""Storage router for OmniDrive - manages storage account operations."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

from database_driver import get_db
from models import ConnectedAccount, ProviderType
from services.google_drive import list_drive_files, get_mime_type_category, format_file_size, format_modified_time, GoogleDriveError


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


class FileItem(BaseModel):
    """File/folder item from storage provider."""
    id: str
    name: str
    mime_type: str
    category: str
    size: Optional[int] = None
    size_formatted: Optional[str] = None
    modified_time: Optional[str] = None
    modified_time_formatted: Optional[str] = None
    thumbnail_link: Optional[str] = None
    web_view_link: Optional[str] = None
    is_folder: bool = False
    item_count: Optional[int] = None  # For folders


class FileListResponse(BaseModel):
    """Response for file listing."""
    account_id: int
    provider: ProviderType
    parent_id: str
    items: List[FileItem]
    total_items: int


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


@router.get("/{account_id}/files", response_model=FileListResponse)
async def list_files(account_id: int, parent_id: str = "root", page_size: int = 100, db: Session = Depends(get_db)):
    """List files and folders from a connected storage account."""
    account = db.query(ConnectedAccount).filter(ConnectedAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    if account.provider != ProviderType.GOOGLE_DRIVE:
        raise HTTPException(status_code=400, detail=f"File listing not supported for {account.provider.value}")

    try:
        files = await list_drive_files(account, db, parent_id=parent_id, page_size=page_size)
    except GoogleDriveError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")

    items = []
    for f in files:
        category = get_mime_type_category(f.get("mimeType", ""))
        is_folder = category == "folder"
        items.append(FileItem(
            id=f.get("id", ""),
            name=f.get("name", ""),
            mime_type=f.get("mimeType", ""),
            category=category,
            size=f.get("size") if f.get("size") else None,
            size_formatted=format_file_size(f.get("size")) if f.get("size") else None,
            modified_time=f.get("modifiedTime"),
            modified_time_formatted=format_modified_time(f.get("modifiedTime", "")),
            thumbnail_link=f.get("thumbnailLink"),
            web_view_link=f.get("webViewLink"),
            is_folder=is_folder,
        ))

    return FileListResponse(
        account_id=account.id,
        provider=account.provider,
        parent_id=parent_id,
        items=items,
        total_items=len(items),
    )