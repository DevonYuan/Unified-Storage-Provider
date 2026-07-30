"""Storage router for OmniDrive - manages storage account operations."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi import File, UploadFile
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

from database_driver import get_db
from models import ConnectedAccount, ProviderType
from services.google_drive import list_drive_files, GoogleDriveError, upload_drive_file
from services.microsoft_graph import (
    list_drive_files as list_ms_files,
    MicrosoftGraphError,
    upload_drive_file as upload_ms_file,
)


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


def get_mime_type_category(mime_type: str) -> str:
    """Categorize a MIME type into a display category."""
    if mime_type == "application/vnd.google-apps.folder":
        return "folder"
    elif mime_type.startswith("image/"):
        return "image"
    elif mime_type.startswith("video/"):
        return "video"
    elif mime_type.startswith("audio/"):
        return "audio"
    elif mime_type == "application/pdf":
        return "pdf"
    elif mime_type in [
        "application/vnd.google-apps.document",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
        "text/plain",
        "text/markdown",
    ]:
        return "document"
    elif mime_type in [
        "application/vnd.google-apps.spreadsheet",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel",
        "text/csv",
    ]:
        return "spreadsheet"
    elif mime_type in [
        "application/vnd.google-apps.presentation",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/vnd.ms-powerpoint",
    ]:
        return "presentation"
    elif mime_type in [
        "application/zip",
        "application/x-rar-compressed",
        "application/x-7z-compressed",
        "application/gzip",
        "application/x-tar",
    ]:
        return "archive"
    elif mime_type in [
        "application/javascript",
        "application/typescript",
        "application/json",
        "text/html",
        "text/css",
        "text/x-python",
        "text/x-java-source",
        "text/x-c",
        "text/x-cpp",
    ]:
        return "code"
    else:
        return "other"


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    if size_bytes is None:
        return ""

    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024:
            if size_bytes >= 10 or unit == "B":
                return f"{size_bytes:.1f} {unit}"
            return f"{size_bytes:.0f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


def format_modified_time(modified_time: str) -> str:
    """Format RFC3339 timestamp to relative time or short date."""
    if not modified_time:
        return ""
    try:
        from datetime import datetime, timezone
        dt = datetime.fromisoformat(modified_time.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        diff = now - dt

        if diff.days > 365:
            return dt.strftime("%b %d, %Y")
        elif diff.days > 30:
            return dt.strftime("%b %d")
        elif diff.days > 0:
            return f"{diff.days}d ago"
        elif diff.seconds > 3600:
            return f"{diff.seconds // 3600}h ago"
        elif diff.seconds > 60:
            return f"{diff.seconds // 60}m ago"
        else:
            return "Just now"
    except Exception:
        return modified_time[:10] if modified_time else ""


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

    if account.provider == ProviderType.GOOGLE_DRIVE:
        try:
            files = await list_drive_files(account, db, parent_id=parent_id, page_size=page_size)
        except GoogleDriveError as e:
            raise HTTPException(status_code=400, detail=str(e))
    elif account.provider == ProviderType.ONEDRIVE:
        try:
            files = await list_ms_files(account, db, parent_id=parent_id, page_size=page_size)
        except MicrosoftGraphError as e:
            raise HTTPException(status_code=400, detail=str(e))
    else:
        raise HTTPException(status_code=400, detail=f"File listing not supported for {account.provider.value}")

    items = []
    for f in files:
        mime_type = f.get("mimeType", "")
        category = get_mime_type_category(mime_type)
        is_folder = category == "folder"
        size = f.get("size")
        modified_time = f.get("modifiedTime")

        items.append(FileItem(
            id=f.get("id", ""),
            name=f.get("name", ""),
            mime_type=mime_type,
            category=category,
            size=size if size else None,
            size_formatted=format_file_size(int(size)) if size else None,
            modified_time=modified_time,
            modified_time_formatted=format_modified_time(modified_time) if modified_time else None,
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


@router.post("/{account_id}/files/upload")
async def upload_file(
    account_id: int,
    file: UploadFile = File(...),
    parent_id: str = "root",
    db: Session = Depends(get_db)
):
    """Upload a file to a connected storage account."""
    account = db.query(ConnectedAccount).filter(ConnectedAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    if account.provider == ProviderType.GOOGLE_DRIVE:
        try:
            uploaded_file = await upload_drive_file(account, db, file, parent_id)
        except GoogleDriveError as e:
            raise HTTPException(status_code=400, detail=str(e))
    elif account.provider == ProviderType.ONEDRIVE:
        try:
            uploaded_file = await upload_ms_file(account, db, file, parent_id)
        except MicrosoftGraphError as e:
            raise HTTPException(status_code=400, detail=str(e))
    else:
        raise HTTPException(status_code=400, detail=f"File upload not supported for {account.provider.value}")

    # Return file metadata in the same format as list_files
    mime_type = uploaded_file.get("mimeType", "")
    category = get_mime_type_category(mime_type)
    is_folder = category == "folder"
    size = uploaded_file.get("size")
    modified_time = uploaded_file.get("modifiedTime")

    file_item = FileItem(
        id=uploaded_file.get("id", ""),
        name=uploaded_file.get("name", ""),
        mime_type=mime_type,
        category=category,
        size=size if size else None,
        size_formatted=format_file_size(int(size)) if size else None,
        modified_time=modified_time,
        modified_time_formatted=format_modified_time(modified_time) if modified_time else None,
        thumbnail_link=uploaded_file.get("thumbnailLink"),
        web_view_link=uploaded_file.get("webViewLink"),
        is_folder=is_folder,
        item_count=None
    )

    return file_item