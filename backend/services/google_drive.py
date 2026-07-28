"""Google Drive service for OmniDrive - handles Google Drive API operations."""

import httpx
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session


class GoogleDriveError(Exception):
    """Google Drive API related errors."""
    pass


async def get_valid_access_token(account: "ConnectedAccount", db: Session) -> str:
    """
    Get a valid access token for a Google Drive account.

    Currently returns the stored access token.
    In production, should check expiry and refresh if needed.
    """
    if not account.access_token:
        raise GoogleDriveError("No access token available for this account")

    return account.access_token


async def list_drive_files(
    account: "ConnectedAccount",
    db: Session,
    parent_id: str = "root",
    page_size: int = 100,
) -> List[Dict[str, Any]]:
    """
    List files and folders from Google Drive.

    Args:
        account: ConnectedAccount with Google Drive credentials
        db: Database session
        parent_id: Parent folder ID to list (default: "root")
        page_size: Number of items per page

    Returns:
        List of file/folder dictionaries
    """
    access_token = await get_valid_access_token(account, db)

    params = {
        "q": f"'{parent_id}' in parents and trashed = false",
        "pageSize": page_size,
        "fields": "files(id,name,mimeType,size,modifiedTime,thumbnailLink,webViewLink,parents)",
        "orderBy": "modifiedTime desc",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            "https://www.googleapis.com/drive/v3/files",
            headers={"Authorization": f"Bearer {access_token}"},
            params=params,
        )

        if response.status_code == 401:
            if account.refresh_token:
                try:
                    token_response = await refresh_access_token(account.refresh_token)
                    account.access_token = token_response["access_token"]
                    db.commit()

                    response = await client.get(
                        "https://www.googleapis.com/drive/v3/files",
                        headers={"Authorization": f"Bearer {token_response['access_token']}"},
                        params=params,
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
) -> Dict[str, Any]:
    """
    Get metadata for a specific file/folder.
    """
    access_token = await get_valid_access_token(account, db)

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"https://www.googleapis.com/drive/v3/files/{file_id}",
            headers={"Authorization": f"Bearer {access_token}"},
            params={
                "fields": "id,name,mimeType,size,modifiedTime,thumbnailLink,webViewLink,parents"
            },
        )

        if response.status_code != 200:
            error_data = response.json()
            raise GoogleDriveError(f"Google Drive API error: {error_data.get('error', {}).get('message', 'Unknown error')}")

        return response.json()


def get_mime_type_category(mime_type: str) -> str:
    """
    Categorize a MIME type for display.

    Returns: 'folder', 'image', 'video', 'audio', 'document', 'spreadsheet',
             'presentation', 'pdf', 'archive', 'code', 'other'
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