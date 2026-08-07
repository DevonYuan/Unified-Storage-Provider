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
            try:
                error_data = response.json()
                error_msg = error_data.get('error', {}).get('message', 'Unknown error')
            except Exception:
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
            raise MicrosoftGraphError(f"Microsoft Graph API error: {error_msg}")

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

        if response.status_code == 401:
            if account.refresh_token:
                try:
                    token_response = await refresh_access_token(account.refresh_token)
                    account.access_token = token_response["access_token"]
                    db.commit()

                    response = await client.get(
                        f"{GRAPH_BASE}/me/drive/items/{file_id}",
                        headers={"Authorization": f"Bearer {token_response['access_token']}"},
                    )
                except Exception as e:
                    raise MicrosoftGraphError(f"Failed to refresh access token: {e}")
            else:
                raise MicrosoftGraphError("Access token expired and no refresh token available")

        if response.status_code != 200:
            try:
                error_data = response.json()
                error_msg = error_data.get('error', {}).get('message', 'Unknown error')
            except Exception:
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
            raise MicrosoftGraphError(f"Microsoft Graph API error: {error_msg}")

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
            try:
                error_data = response.json()
                error_msg = error_data.get('error', {}).get('message', 'Unknown error')
            except Exception:
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
            raise MicrosoftGraphError(
                f"Microsoft Graph API error: {error_msg}"
            )

        return _ms_item_to_fileitem(response.json())


async def create_drive_folder(
    account: "ConnectedAccount",
    db: Session,
    folder_name: str,
    parent_id: str = "root",
) -> Dict[str, Any]:
    """Create a new folder in OneDrive."""
    access_token = await get_valid_access_token(account, db)

    if parent_id == "root":
        url = f"{GRAPH_BASE}/me/drive/root/children"
    else:
        url = f"{GRAPH_BASE}/me/drive/items/{parent_id}/children"

    body = {
        "name": folder_name,
        "folder": {},
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            url,
            headers={"Authorization": f"Bearer {access_token}"},
            json=body,
        )

        if response.status_code == 401:
            if account.refresh_token:
                try:
                    token_response = await refresh_access_token(account.refresh_token)
                    account.access_token = token_response["access_token"]
                    db.commit()
                    response = await client.post(
                        url,
                        headers={"Authorization": f"Bearer {token_response['access_token']}"},
                        json=body,
                    )
                except Exception as e:
                    raise MicrosoftGraphError(f"Failed to refresh access token: {e}")
            else:
                raise MicrosoftGraphError("Access token expired and no refresh token available")

        if response.status_code not in (200, 201):
            try:
                error_data = response.json()
                error_msg = error_data.get('error', {}).get('message', 'Unknown error')
            except Exception:
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
            raise MicrosoftGraphError(
                f"Microsoft Graph API error: {error_msg}"
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


async def delete_drive_file(
    account: "ConnectedAccount",
    db: Session,
    file_id: str,
) -> None:
    """Delete a file or folder from OneDrive."""
    access_token = await get_valid_access_token(account, db)

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.delete(
            f"{GRAPH_BASE}/me/drive/items/{file_id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        if response.status_code == 401:
            if account.refresh_token:
                try:
                    token_response = await refresh_access_token(account.refresh_token)
                    account.access_token = token_response["access_token"]
                    db.commit()
                    response = await client.delete(
                        f"{GRAPH_BASE}/me/drive/items/{file_id}",
                        headers={"Authorization": f"Bearer {token_response['access_token']}"},
                    )
                except Exception as e:
                    raise MicrosoftGraphError(f"Failed to refresh access token: {e}")
            else:
                raise MicrosoftGraphError("Access token expired and no refresh token available")

        if response.status_code not in (200, 204):
            try:
                error_data = response.json()
                error_msg = error_data.get('error', {}).get('message', 'Unknown error')
            except Exception:
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
            raise MicrosoftGraphError(
                f"Microsoft Graph API error: {error_msg}"
            )


async def download_drive_file(
    account: "ConnectedAccount",
    db: Session,
    file_id: str,
    download_format: str = None,
) -> tuple:
    """Download a file from OneDrive. Pass download_format='zip' for folder zip downloads."""
    access_token = await get_valid_access_token(account, db)

    async with httpx.AsyncClient(timeout=120.0) as client:
        # Get metadata for filename
        meta_response = await client.get(
            f"{GRAPH_BASE}/me/drive/items/{file_id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        if meta_response.status_code == 401:
            if account.refresh_token:
                try:
                    token_response = await refresh_access_token(account.refresh_token)
                    account.access_token = token_response["access_token"]
                    db.commit()
                    access_token = token_response["access_token"]
                    meta_response = await client.get(
                        f"{GRAPH_BASE}/me/drive/items/{file_id}",
                        headers={"Authorization": f"Bearer {access_token}"},
                    )
                except Exception as e:
                    raise MicrosoftGraphError(f"Failed to refresh access token: {e}")
            else:
                raise MicrosoftGraphError("Access token expired and no refresh token available")

        if meta_response.status_code != 200:
            try:
                error_data = meta_response.json()
                error_msg = error_data.get('error', {}).get('message', 'Unknown error')
            except Exception:
                error_msg = f"HTTP {meta_response.status_code}"
            raise MicrosoftGraphError(f"Failed to fetch file metadata: {error_msg}")

        try:
            meta = meta_response.json()
        except Exception:
            raise MicrosoftGraphError("Failed to parse file metadata response")
        filename = meta.get("name", "download")
        if download_format == "zip":
            filename = f"{filename}.zip"
        file_info = meta.get("file", {})
        mime_type = file_info.get("mimeType", "application/octet-stream")
        if download_format == "zip":
            mime_type = "application/zip"

        # ZIP format: use the /content?format=zip endpoint (no pre-auth URL available)
        if download_format == "zip":
            content_url = f"{GRAPH_BASE}/me/drive/items/{file_id}/content?format=zip"
            response = await client.get(
                content_url,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if response.status_code == 401:
                if account.refresh_token:
                    try:
                        token_response = await refresh_access_token(account.refresh_token)
                        account.access_token = token_response["access_token"]
                        db.commit()
                        response = await client.get(
                            content_url,
                            headers={"Authorization": f"Bearer {token_response['access_token']}"},
                        )
                    except Exception as e:
                        raise MicrosoftGraphError(f"Failed to refresh access token: {e}")
                else:
                    raise MicrosoftGraphError("Access token expired and no refresh token available")
        else:
            # Prefer the pre-authenticated download URL from metadata.
            # The /content endpoint returns a 302 redirect which httpx may not follow.
            download_url = meta.get("@microsoft.graph.downloadUrl")
            if download_url:
                # Download from the pre-authenticated URL (no auth header needed)
                response = await client.get(download_url)
                # If the pre-auth URL expired, fall back to /content endpoint
                if response.status_code != 200:
                    response = await client.get(
                        f"{GRAPH_BASE}/me/drive/items/{file_id}/content",
                        headers={"Authorization": f"Bearer {access_token}"},
                    )
            else:
                # Fall back to /content endpoint
                response = await client.get(
                    f"{GRAPH_BASE}/me/drive/items/{file_id}/content",
                    headers={"Authorization": f"Bearer {access_token}"},
                )

                if response.status_code == 401:
                    if account.refresh_token:
                        try:
                            token_response = await refresh_access_token(account.refresh_token)
                            account.access_token = token_response["access_token"]
                            db.commit()
                            response = await client.get(
                                f"{GRAPH_BASE}/me/drive/items/{file_id}/content",
                                headers={"Authorization": f"Bearer {token_response['access_token']}"},
                            )
                        except Exception as e:
                            raise MicrosoftGraphError(f"Failed to refresh access token: {e}")
                    else:
                        raise MicrosoftGraphError("Access token expired and no refresh token available")

        if response.status_code != 200:
            try:
                error_data = response.json()
                error_msg = error_data.get('error', {}).get('message', 'Unknown error')
            except Exception:
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
            raise MicrosoftGraphError(
                f"Microsoft Graph API error: {error_msg}"
            )

        return response.content, filename, mime_type


async def move_drive_file(
    account: "ConnectedAccount",
    db: Session,
    file_id: str,
    new_parent_id: str,
) -> Dict[str, Any]:
    """Move a file or folder to a different parent folder in OneDrive."""
    access_token = await get_valid_access_token(account, db)

    body = {}
    if new_parent_id and new_parent_id != "root":
        body["parentReference"] = {"id": new_parent_id}

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.patch(
            f"{GRAPH_BASE}/me/drive/items/{file_id}",
            headers={"Authorization": f"Bearer {access_token}"},
            json=body,
        )

        if response.status_code == 401:
            if account.refresh_token:
                try:
                    token_response = await refresh_access_token(account.refresh_token)
                    account.access_token = token_response["access_token"]
                    db.commit()
                    response = await client.patch(
                        f"{GRAPH_BASE}/me/drive/items/{file_id}",
                        headers={"Authorization": f"Bearer {token_response['access_token']}"},
                        json=body,
                    )
                except Exception as e:
                    raise MicrosoftGraphError(f"Failed to refresh access token: {e}")
            else:
                raise MicrosoftGraphError("Access token expired and no refresh token available")

        if response.status_code not in (200, 201):
            try:
                error_data = response.json()
                error_msg = error_data.get('error', {}).get('message', 'Unknown error')
            except Exception:
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
            raise MicrosoftGraphError(
                f"Microsoft Graph move error: {error_msg}"
            )

        return _ms_item_to_fileitem(response.json())


async def copy_drive_file(
    account: "ConnectedAccount",
    db: Session,
    file_id: str,
    new_parent_id: str,
) -> Dict[str, Any]:
    """Copy a file or folder to a different folder in OneDrive.

    Uses Microsoft Graph's async copy endpoint. For folders or large files
    this returns 202 Accepted — we poll the monitor URL until completion.
    """
    access_token = await get_valid_access_token(account, db)

    # Fetch the original item's name so we can generate a conflict-free copy name
    meta = await get_file_metadata(account, db, file_id)
    original_name = meta.get("name", "copy")

    # Generate a copy name: "file.txt" → "file - Copy.txt"
    dot_idx = original_name.rfind(".")
    if dot_idx > 0:
        copy_name = f"{original_name[:dot_idx]} - Copy{original_name[dot_idx:]}"
    else:
        copy_name = f"{original_name} - Copy"

    # Always include parentReference — empty body causes a 500 from Microsoft.
    body: Dict[str, Any] = {
        "parentReference": {"id": new_parent_id} if new_parent_id and new_parent_id != "root" else {"path": "/drive/root:"},
        "name": copy_name,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{GRAPH_BASE}/me/drive/items/{file_id}/copy",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Prefer": "respond-async",
            },
            json=body,
        )

        if response.status_code == 401:
            if account.refresh_token:
                try:
                    token_response = await refresh_access_token(account.refresh_token)
                    account.access_token = token_response["access_token"]
                    db.commit()
                    response = await client.post(
                        f"{GRAPH_BASE}/me/drive/items/{file_id}/copy",
                        headers={
                            "Authorization": f"Bearer {token_response['access_token']}",
                            "Prefer": "respond-async",
                        },
                        json=body,
                    )
                except Exception as e:
                    raise MicrosoftGraphError(f"Failed to refresh access token: {e}")
            else:
                raise MicrosoftGraphError("Access token expired and no refresh token available")

        if response.status_code == 202:
            # Async copy — poll the monitor URL
            monitor_url = response.headers.get("Location")
            if monitor_url:
                import asyncio
                poll_token = access_token
                for _ in range(60):  # poll up to 60 seconds for large folders
                    await asyncio.sleep(1)
                    poll = await client.get(
                        monitor_url,
                        headers={"Authorization": f"Bearer {poll_token}"},
                    )
                    if poll.status_code in (200, 201):
                        return _ms_item_to_fileitem(poll.json())
                    elif poll.status_code == 401:
                        # Token expired during polling — refresh and retry
                        if account.refresh_token:
                            try:
                                token_response = await refresh_access_token(account.refresh_token)
                                poll_token = token_response["access_token"]
                                account.access_token = poll_token
                                db.commit()
                                # Retry immediately with new token
                                poll = await client.get(
                                    monitor_url,
                                    headers={"Authorization": f"Bearer {poll_token}"},
                                )
                                if poll.status_code in (200, 201):
                                    return _ms_item_to_fileitem(poll.json())
                                elif poll.status_code >= 400:
                                    error_data = poll.json()
                                    raise MicrosoftGraphError(
                                        f"Copy failed during polling: {error_data.get('error', {}).get('message', 'Unknown error')}"
                                    )
                            except Exception as e:
                                raise MicrosoftGraphError(f"Token refresh failed during copy: {e}")
                        else:
                            raise MicrosoftGraphError("Access token expired during copy and no refresh token available")
                    elif poll.status_code >= 400:
                        error_data = poll.json()
                        raise MicrosoftGraphError(
                            f"Copy failed during polling: {error_data.get('error', {}).get('message', 'Unknown error')}"
                        )
                raise MicrosoftGraphError("Copy operation timed out after 60 seconds")
            raise MicrosoftGraphError("No monitor URL returned for async copy")

        if response.status_code in (200, 201):
            return _ms_item_to_fileitem(response.json())

        # Try to extract a useful error message
        try:
            error_data = response.json()
            msg = error_data.get("error", {}).get("message", "Unknown error")
        except Exception:
            msg = f"HTTP {response.status_code}"
        raise MicrosoftGraphError(f"Microsoft Graph copy error: {msg}")


async def get_storage_quota(
    account: "ConnectedAccount",
    db: Session,
) -> Dict[str, Any]:
    """Get storage quota information from OneDrive.

    Returns dict with total_space, used_space, available_space (all in bytes).
    """
    access_token = await get_valid_access_token(account, db)

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{GRAPH_BASE}/me/drive",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"$select": "quota"},
        )

        if response.status_code == 401:
            if account.refresh_token:
                try:
                    token_response = await refresh_access_token(account.refresh_token)
                    account.access_token = token_response["access_token"]
                    db.commit()
                    response = await client.get(
                        f"{GRAPH_BASE}/me/drive",
                        headers={"Authorization": f"Bearer {token_response['access_token']}"},
                        params={"$select": "quota"},
                    )
                except Exception as e:
                    raise MicrosoftGraphError(f"Failed to refresh access token: {e}")
            else:
                raise MicrosoftGraphError("Access token expired and no refresh token available")

        if response.status_code != 200:
            try:
                error_data = response.json()
                error_msg = error_data.get('error', {}).get('message', 'Unknown error')
            except Exception:
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
            raise MicrosoftGraphError(f"Microsoft Graph API error: {error_msg}")

        try:
            data = response.json()
        except Exception:
            raise MicrosoftGraphError("Failed to parse quota response")

        quota = data.get("quota", {})
        return {
            "total_space": quota.get("total"),
            "used_space": quota.get("used"),
            "available_space": quota.get("remaining"),
        }


async def list_trash_files(
    account: "ConnectedAccount",
    db: Session,
) -> List[Dict[str, Any]]:
    """List files in OneDrive recycle bin."""
    access_token = await get_valid_access_token(account, db)

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{GRAPH_BASE}/me/drive/recycleBin",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"$top": 100, "$orderby": "deletedDateTime desc"},
        )

        if response.status_code == 401:
            if account.refresh_token:
                try:
                    token_response = await refresh_access_token(account.refresh_token)
                    account.access_token = token_response["access_token"]
                    db.commit()
                    response = await client.get(
                        f"{GRAPH_BASE}/me/drive/recycleBin",
                        headers={"Authorization": f"Bearer {token_response['access_token']}"},
                        params={"$top": 100, "$orderby": "deletedDateTime desc"},
                    )
                except Exception as e:
                    raise MicrosoftGraphError(f"Failed to refresh access token: {e}")
            else:
                raise MicrosoftGraphError("Access token expired and no refresh token available")

        if response.status_code != 200:
            try:
                error_data = response.json()
                error_msg = error_data.get('error', {}).get('message', 'Unknown error')
            except Exception:
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
            raise MicrosoftGraphError(f"Microsoft Graph API error: {error_msg}")

        try:
            data = response.json()
        except Exception:
            raise MicrosoftGraphError("Failed to parse trash response")

        return [_ms_item_to_fileitem(item) for item in data.get("value", [])]


async def restore_from_trash(
    account: "ConnectedAccount",
    db: Session,
    file_id: str,
) -> Dict[str, Any]:
    """Restore a file from OneDrive recycle bin."""
    access_token = await get_valid_access_token(account, db)

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.patch(
            f"{GRAPH_BASE}/me/drive/recycleBin/items/{file_id}/restore",
            headers={"Authorization": f"Bearer {access_token}"},
            json={},
        )

        if response.status_code == 401:
            if account.refresh_token:
                try:
                    token_response = await refresh_access_token(account.refresh_token)
                    account.access_token = token_response["access_token"]
                    db.commit()
                    response = await client.patch(
                        f"{GRAPH_BASE}/me/drive/recycleBin/items/{file_id}/restore",
                        headers={"Authorization": f"Bearer {token_response['access_token']}"},
                        json={},
                    )
                except Exception as e:
                    raise MicrosoftGraphError(f"Failed to refresh access token: {e}")
            else:
                raise MicrosoftGraphError("Access token expired and no refresh token available")

        if response.status_code not in (200, 201, 204):
            try:
                error_data = response.json()
                error_msg = error_data.get('error', {}).get('message', 'Unknown error')
            except Exception:
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
            raise MicrosoftGraphError(f"Microsoft Graph API error: {error_msg}")

        return _ms_item_to_fileitem(response.json()) if response.status_code in (200, 201) else {"status": "restored"}


async def rename_drive_file(
    account: "ConnectedAccount",
    db: Session,
    file_id: str,
    new_name: str,
) -> Dict[str, Any]:
    """Rename a file or folder in OneDrive."""
    access_token = await get_valid_access_token(account, db)

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.patch(
            f"{GRAPH_BASE}/me/drive/items/{file_id}",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"name": new_name},
        )

        if response.status_code == 401:
            if account.refresh_token:
                try:
                    token_response = await refresh_access_token(account.refresh_token)
                    account.access_token = token_response["access_token"]
                    db.commit()
                    response = await client.patch(
                        f"{GRAPH_BASE}/me/drive/items/{file_id}",
                        headers={"Authorization": f"Bearer {token_response['access_token']}"},
                        json={"name": new_name},
                    )
                except Exception as e:
                    raise MicrosoftGraphError(f"Failed to refresh access token: {e}")
            else:
                raise MicrosoftGraphError("Access token expired and no refresh token available")

        if response.status_code != 200:
            try:
                error_data = response.json()
                error_msg = error_data.get('error', {}).get('message', 'Unknown error')
            except Exception:
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
            raise MicrosoftGraphError(f"Microsoft Graph rename error: {error_msg}")

        try:
            return _ms_item_to_fileitem(response.json())
        except Exception:
            raise MicrosoftGraphError("Provider returned invalid JSON")
