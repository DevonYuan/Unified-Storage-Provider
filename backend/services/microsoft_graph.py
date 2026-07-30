"""Microsoft Graph service for OmniDrive - handles OneDrive API operations."""

import httpx
import json
from typing import Optional, List, Dict, Any
from fastapi import UploadFile
from sqlalchemy.orm import Session

from services.microsoft_oauth import refresh_access_token


GRAPH_BASE = "https://graph.microsoft.com/v1.0"


class MicrosoftGraphError(Exception):
    """Microsoft Graph API related errors."""
    pass


async def get_valid_access_token(account: "ConnectedAccount", db: Session) -> str:
    """
    Get a valid access token for a OneDrive account.

    Currently returns the stored access token.
    In production, should check expiry and refresh if needed.
    """
    if not account.access_token:
        raise MicrosoftGraphError("No access token available for this account")

    return account.access_token


async def list_drive_files(
    account: "ConnectedAccount",
    db: Session,
    parent_id: str = "root",
    page_size: int = 100,
) -> List[Dict[str, Any]]:
    """
    List files and folders from OneDrive.

    Args:
        account: ConnectedAccount with OneDrive credentials
        db: Database session
        parent_id: Parent folder ID to list (default: "root")
        page_size: Number of items per page

    Returns:
        List of file/folder dictionaries in FileItem-compatible format
    """
    access_token = await get_valid_access_token(account, db)

    # Build the URL — root is special-cased in Microsoft Graph
    if parent_id == "root":
        url = f"{GRAPH_BASE}/me/drive/root/children"
    else:
        url = f"{GRAPH_BASE}/me/drive/items/{parent_id}/children"

    params = {
        "$top": page_size,
        "$orderby": "lastModifiedDateTime desc",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            url,
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
                        url,
                        headers={"Authorization": f"Bearer {token_response['access_token']}"},
                        params=params,
                    )
                except Exception as e:
                    raise MicrosoftGraphError(f"Failed to refresh access token: {e}")
            else:
                raise MicrosoftGraphError("Access token expired and no refresh token available")

        if response.status_code != 200:
            error_data = response.json()
            raise MicrosoftGraphError(
                f"Microsoft Graph API error: {error_data.get('error', {}).get('message', 'Unknown error')}"
            )

        data = response.json()
        items = data.get("value", [])

        # Map Microsoft Graph fields to our provider-agnostic format
        return [_ms_item_to_fileitem(item) for item in items]


async def get_file_metadata(
    account: "ConnectedAccount",
    db: Session,
    file_id: str,
) -> Dict[str, Any]:
    """
    Get metadata for a specific file/folder from OneDrive.
    """
    access_token = await get_valid_access_token(account, db)

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{GRAPH_BASE}/me/drive/items/{file_id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        if response.status_code != 200:
            error_data = response.json()
            raise MicrosoftGraphError(
                f"Microsoft Graph API error: {error_data.get('error', {}).get('message', 'Unknown error')}"
            )

        return _ms_item_to_fileitem(response.json())


async def upload_drive_file(
    account: "ConnectedAccount",
    db: Session,
    file: UploadFile,
    parent_id: str = "root",
) -> Dict[str, Any]:
    """
    Upload a file to OneDrive.

    Args:
        account: ConnectedAccount with OneDrive credentials
        db: Database session
        file: UploadFile object containing file data
        parent_id: Parent folder ID to upload to (default: "root")

    Returns:
        Dictionary containing file metadata in FileItem-compatible format
    """
    access_token = await get_valid_access_token(account, db)

    content = await file.read()
    await file.seek(0)

    # Build upload URL based on parent
    if parent_id == "root":
        url = f"{GRAPH_BASE}/me/drive/root:/{file.filename}:/content"
    else:
        url = f"{GRAPH_BASE}/me/drive/items/{parent_id}:/{file.filename}:/content"

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.put(
            url,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": file.content_type or "application/octet-stream",
            },
            content=content,
        )

        if response.status_code == 401:
            if account.refresh_token:
                try:
                    token_response = await refresh_access_token(account.refresh_token)
                    account.access_token = token_response["access_token"]
                    db.commit()

                    response = await client.put(
                        url,
                        headers={
                            "Authorization": f"Bearer {token_response['access_token']}",
                            "Content-Type": file.content_type or "application/octet-stream",
                        },
                        content=content,
                    )
                except Exception as e:
                    raise MicrosoftGraphError(f"Failed to refresh access token: {e}")
            else:
                raise MicrosoftGraphError("Access token expired and no refresh token available")

        if response.status_code not in (200, 201):
            error_data = response.json()
            raise MicrosoftGraphError(
                f"Microsoft Graph API error: {error_data.get('error', {}).get('message', 'Unknown error')}"
            )

        return _ms_item_to_fileitem(response.json())


def _ms_item_to_fileitem(ms_item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Translate a Microsoft Graph driveItem into our provider-agnostic format.

    Maps fields so the storage router can use the same FileItem model
    regardless of provider.
    """
    # Determine MIME type
    is_folder = "folder" in ms_item
    if is_folder:
        mime_type = "application/vnd.google-apps.folder"  # reuse folder convention
    else:
        file_info = ms_item.get("file", {})
        mime_type = file_info.get("mimeType", "application/octet-stream")

    # Size: Microsoft returns int (bytes)
    size = ms_item.get("size")

    # Modified time
    modified_time = ms_item.get("lastModifiedDateTime")

    # Thumbnail: pick first available small/medium thumbnail
    thumbnails = ms_item.get("thumbnails", [])
    thumbnail_link = None
    if thumbnails:
        thumb = thumbnails[0]
        thumbnail_link = thumb.get("medium", {}).get("url") or thumb.get("small", {}).get("url")

    # Web link
    web_view_link = ms_item.get("webUrl")

    # Item count for folders
    folder_data = ms_item.get("folder", {})
    item_count = folder_data.get("childCount")

    return {
        "id": ms_item.get("id", ""),
        "name": ms_item.get("name", ""),
        "mimeType": mime_type,
        "size": str(size) if size is not None else None,
        "modifiedTime": modified_time,
        "thumbnailLink": thumbnail_link,
        "webViewLink": web_view_link,
        "is_folder": is_folder,
        "item_count": item_count,
    }
