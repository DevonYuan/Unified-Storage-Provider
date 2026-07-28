"""Google Drive service for OmniDrive - handles Google Drive API operations."""

import httpx
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from services.google_oauth import refresh_access_token


class GoogleDriveError(Exception):
    """Google Drive API related errors."""
    pass


async def get_valid_access_token(account: "ConnectedAccount", db: Session) -> str:
    """
    Get a valid access token for a Google Drive account, refreshing if needed.
    """
    # For now, we assume the access_token is still valid
    # In production, you'd check expires_at and refresh if needed
    if not account.access_token:
        raise GoogleDriveError("No access token available for this account")

    return account.access_token


async def list_drive_files(
    account: "ConnectedAccount",
    db: Session,
    parent_id: str = "root",
    page_size: int = 100,
    fields: str = "files(id,name,mimeType,size,modifiedTime,thumbnailLink,webViewLink,parents,trashed)"
) -> List[Dict[str, Any]]:
    """
    List files and folders from Google Drive.

    Args:
        account: ConnectedAccount with Google Drive credentials
        db: Database session
        parent_id: Parent folder ID to list (default: "root")
        page_size: Number of items per page
        fields: Fields to request from Google Drive API

    Returns:
        List of file/folder dictionaries
    """
    from models import ConnectedAccount
    access_token = await get_valid_access_token(account, db)

    params = {
        "q": f"'{parent_id}' in parents and trashed = false",
        "pageSize": page_size,
        "fields": fields,
        "orderBy": "modifiedTime desc",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            "https://www.googleapis.com/drive/v3/files",
            headers={"Authorization": f"Bearer {access_token}"},
            params=params
        )

        if response.status_code == 401:
            # Token might be expired, try to refresh
            if account.refresh_token:
                try:
                    token_response = await refresh_access_token(account.refresh_token)
                    account.access_token = token_response.access_token
                    # TODO: Update expires_at
                    db.commit()

                    # Retry with new token
                    response = await client.get(
                        "https://www.googleapis.com/drive/v3/files",
                        headers={"Authorization": f"Bearer {token_response.access_token}"},
                        params=params
                    )
                except Exception:
                    raise GoogleDriveError("Failed to refresh access token")
            else:
                raise GoogleDriveError("Access token expired and no refresh token available")

        if response.status_code != 200:
            error_data = response.json()
            raise GoogleDriveError(f"Google Drive API error: {error_data.get('error', {}).get('message', 'Unknown error')}")

        data = response.json()
        return data.get("files", [])


async def get_file_metadata(
    account: "ConnectedAccount",
    db: Session,
    file_id: str,
    fields: str = "id,name,mimeType,size,modifiedTime,thumbnailLink,webViewLink,parents"
) -> Dict[str, Any]:
    """
    Get metadata for a specific file/folder.
    """
    access_token = await get_valid_access_token(account, db)

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"https://www.googleapis.com/drive/v3/files/{file_id}",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"fields": fields}
        )

        if response.status_code != 200:
            error_data = response.json()
            raise GoogleDriveError(f"Google Drive API error: {error_data.get('error', {}).get('message', 'Unknown error')}")

        return response.json()


def get_mime_type_category(mime_type: str) -> str:
    """
    Categorize a MIME type into a display category.

    Returns: 'folder', 'image', 'video', 'audio', 'document', 'spreadsheet', 'presentation', 'pdf', 'archive', 'code', 'other'
    """
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


def get_file_icon_name(category: str) -> str:
    """
    Get the Lucide icon name for a file category.
    """
    icons = {
        "folder": "Folder",
        "image": "Image",
        "video": "Video",
        "audio": "Music",
        "pdf": "FileText",
        "document": "FileText",
        "spreadsheet": "Table",
        "presentation": "Presentation",
        "archive": "Archive",
        "code": "Code",
        "other": "File",
    }
    return icons.get(category, "File")


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.
    """
    if size_bytes is None:
        return ""

    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}" if size_bytes >= 10 or unit == "B" else f"{size_bytes:.0f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


def format_modified_time(modified_time: str) -> str:
    """
    Format RFC3339 timestamp to relative time or short date.
    """
    from datetime import datetime, timezone
    try:
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