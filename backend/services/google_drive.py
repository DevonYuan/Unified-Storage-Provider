"""Google Drive service for OmniDrive - handles Google Drive API operations."""

import httpx
import json
from typing import Optional, List, Dict, Any
from fastapi import UploadFile
from sqlalchemy.orm import Session

from services.google_oauth import refresh_access_token


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

    all_files = []
    page_token = None

    async with httpx.AsyncClient(timeout=30.0) as client:
        while True:
            params = {
                "q": f"'{parent_id}' in parents and trashed = false",
                "pageSize": page_size,
                "fields": "files(id,name,mimeType,size,modifiedTime,thumbnailLink,webViewLink,parents),nextPageToken",
                "orderBy": "modifiedTime desc",
            }

            if page_token:
                params["pageToken"] = page_token

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
                    except Exception as e:
                        raise GoogleDriveError(f"Failed to refresh access token: {e}")
                else:
                    raise GoogleDriveError("Access token expired and no refresh token available")

            if response.status_code != 200:
                try:
                    error_data = response.json()
                    error_msg = error_data.get('error', {}).get('message', 'Unknown error')
                except (json.JSONDecodeError, ValueError):
                    error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                raise GoogleDriveError(f"Google Drive API error: {error_msg}")

            data = response.json()
            files = data.get("files", [])
            all_files.extend(files)

            page_token = data.get("nextPageToken")
            if not page_token:
                break

    return all_files


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

        if response.status_code == 401:
            if account.refresh_token:
                try:
                    token_response = await refresh_access_token(account.refresh_token)
                    account.access_token = token_response["access_token"]
                    db.commit()

                    response = await client.get(
                        f"https://www.googleapis.com/drive/v3/files/{file_id}",
                        headers={"Authorization": f"Bearer {token_response['access_token']}"},
                        params={
                            "fields": "id,name,mimeType,size,modifiedTime,thumbnailLink,webViewLink,parents"
                        },
                    )
                except Exception as e:
                    raise GoogleDriveError(f"Failed to refresh access token: {e}")
            else:
                raise GoogleDriveError("Access token expired and no refresh token available")

        if response.status_code != 200:
            try:
                error_data = response.json()
                error_msg = error_data.get('error', {}).get('message', 'Unknown error')
            except (json.JSONDecodeError, ValueError):
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
            raise GoogleDriveError(f"Google Drive API error: {error_msg}")

        return response.json()


async def upload_drive_file(
    account: "ConnectedAccount",
    db: Session,
    file: UploadFile,
    parent_id: str = "root"
) -> Dict[str, Any]:
    """
    Upload a file to Google Drive.

    Args:
        account: ConnectedAccount with Google Drive credentials
        db: Database session
        file: UploadFile object containing file data
        parent_id: Parent folder ID to upload to (default: "root")

    Returns:
        Dictionary containing file metadata
    """
    access_token = await get_valid_access_token(account, db)

    # Read file content
    content = await file.read()

    # Prepare file metadata
    file_metadata = {
        "name": file.filename,
        "parents": [parent_id] if parent_id != "root" else []
    }

    # Remove empty parents array if root
    if parent_id == "root":
        del file_metadata["parents"]

    async with httpx.AsyncClient(timeout=60.0) as client:
        # Prepare multipart form data
        files = {
            'data': ('metadata', json.dumps(file_metadata), 'application/json'),
            'file': (file.filename, content, file.content_type or 'application/octet-stream')
        }

        response = await client.post(
            "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart",
            headers={"Authorization": f"Bearer {access_token}"},
            files=files
        )

        # Reset file pointer for potential reuse
        await file.seek(0)

        if response.status_code == 401:
            if account.refresh_token:
                try:
                    token_response = await refresh_access_token(account.refresh_token)
                    account.access_token = token_response["access_token"]
                    db.commit()

                    # Retry with new token
                    files = {
                        'data': ('metadata', json.dumps(file_metadata), 'application/json'),
                        'file': (file.filename, content, file.content_type or 'application/octet-stream')
                    }

                    response = await client.post(
                        "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart",
                        headers={"Authorization": f"Bearer {token_response['access_token']}"},
                        files=files
                    )
                except Exception as e:
                    raise GoogleDriveError(f"Failed to refresh access token: {e}")
            else:
                raise GoogleDriveError("Access token expired and no refresh token available")

        if response.status_code != 200:
            try:
                error_data = response.json()
                error_msg = error_data.get('error', {}).get('message', 'Unknown error')
            except (json.JSONDecodeError, ValueError):
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
            raise GoogleDriveError(f"Google Drive API error: {error_msg}")

        return response.json()


async def create_drive_folder(
    account: "ConnectedAccount",
    db: Session,
    folder_name: str,
    parent_id: str = "root",
) -> Dict[str, Any]:
    """Create a new folder in Google Drive."""
    access_token = await get_valid_access_token(account, db)

    file_metadata = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id] if parent_id != "root" else [],
    }
    if parent_id == "root":
        del file_metadata["parents"]

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "https://www.googleapis.com/drive/v3/files",
            headers={"Authorization": f"Bearer {access_token}"},
            json=file_metadata,
        )

        if response.status_code == 401:
            if account.refresh_token:
                try:
                    token_response = await refresh_access_token(account.refresh_token)
                    account.access_token = token_response["access_token"]
                    db.commit()
                    response = await client.post(
                        "https://www.googleapis.com/drive/v3/files",
                        headers={"Authorization": f"Bearer {token_response['access_token']}"},
                        json=file_metadata,
                    )
                except Exception as e:
                    raise GoogleDriveError(f"Failed to refresh access token: {e}")
            else:
                raise GoogleDriveError("Access token expired and no refresh token available")

        if response.status_code != 200:
            try:
                error_data = response.json()
                error_msg = error_data.get('error', {}).get('message', 'Unknown error')
            except (json.JSONDecodeError, ValueError):
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
            raise GoogleDriveError(f"Google Drive API error: {error_msg}")

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


async def upload_file_to_drive(
    account: "ConnectedAccount",
    db: Session,
    file_data: bytes,
    filename: str,
    mime_type: str,
    parent_id: str = "root"
) -> Dict[str, Any]:
    """
    Upload a file to Google Drive.

    Args:
        account: ConnectedAccount with Google Drive credentials
        db: Database session
        file_data: File content as bytes
        filename: Name of the file to upload
        mime_type: MIME type of the file
        parent_id: Parent folder ID to upload to (default: "root")

    Returns:
        Dictionary containing file metadata
    """
    access_token = await get_valid_access_token(account, db)

    # Prepare file metadata
    file_metadata = {
        "name": filename,
        "parents": [parent_id]
    }

    # Prepare media content
    from io import BytesIO
    media_content = BytesIO(file_data)

    # Upload file
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Prepare multipart form data
        files = {
            'data': ('metadata', json.dumps(file_metadata), 'application/json'),
            'file': (filename, media_content, mime_type)
        }

        response = await client.post(
            "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart",
            headers={"Authorization": f"Bearer {access_token}"},
            files=files
        )

        if response.status_code == 401:
            if account.refresh_token:
                try:
                    token_response = await refresh_access_token(account.refresh_token)
                    account.access_token = token_response["access_token"]
                    db.commit()

                    # Retry with new token
                    files = {
                        'data': ('metadata', json.dumps(file_metadata), 'application/json'),
                        'file': (filename, media_content, mime_type)
                    }

                    response = await client.post(
                        "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart",
                        headers={"Authorization": f"Bearer {token_response['access_token']}"},
                        files=files
                    )
                except Exception:
                    raise GoogleDriveError("Failed to refresh access token")
            else:
                raise GoogleDriveError("Access token expired and no refresh token available")

        if response.status_code != 200:
            try:
                error_data = response.json()
                error_msg = error_data.get('error', {}).get('message', 'Unknown error')
            except (json.JSONDecodeError, ValueError):
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
            raise GoogleDriveError(f"Google Drive API error: {error_msg}")

        # Get the uploaded file metadata
        file_id = response.json().get("id")
        if file_id:
            return await get_file_metadata(account, db, file_id)
        else:
            raise GoogleDriveError("Failed to retrieve uploaded file metadata")


async def delete_drive_file(
    account: "ConnectedAccount",
    db: Session,
    file_id: str,
) -> None:
    """Delete a file or folder from Google Drive."""
    access_token = await get_valid_access_token(account, db)

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.delete(
            f"https://www.googleapis.com/drive/v3/files/{file_id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        if response.status_code == 401:
            if account.refresh_token:
                try:
                    token_response = await refresh_access_token(account.refresh_token)
                    account.access_token = token_response["access_token"]
                    db.commit()
                    response = await client.delete(
                        f"https://www.googleapis.com/drive/v3/files/{file_id}",
                        headers={"Authorization": f"Bearer {token_response['access_token']}"},
                    )
                except Exception as e:
                    raise GoogleDriveError(f"Failed to refresh access token: {e}")
            else:
                raise GoogleDriveError("Access token expired and no refresh token available")

        if response.status_code not in (200, 204):
            try:
                error_data = response.json()
                error_msg = error_data.get('error', {}).get('message', 'Unknown error')
            except (json.JSONDecodeError, ValueError):
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
            raise GoogleDriveError(f"Google Drive API error: {error_msg}")


async def download_drive_file(
    account: "ConnectedAccount",
    db: Session,
    file_id: str,
) -> tuple:
    """Download a file from Google Drive. Returns (content_bytes, filename, mime_type)."""
    access_token = await get_valid_access_token(account, db)

    async with httpx.AsyncClient(timeout=120.0) as client:
        # First get file metadata for the name and mime type
        meta = await get_file_metadata(account, db, file_id)
        # Re-read token in case get_file_metadata refreshed it
        access_token = account.access_token
        filename = meta.get("name", "download")
        mime_type = meta.get("mimeType", "application/octet-stream")

        # Download the file content
        response = await client.get(
            f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        if response.status_code == 401:
            if account.refresh_token:
                try:
                    token_response = await refresh_access_token(account.refresh_token)
                    account.access_token = token_response["access_token"]
                    db.commit()
                    response = await client.get(
                        f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media",
                        headers={"Authorization": f"Bearer {token_response['access_token']}"},
                    )
                except Exception as e:
                    raise GoogleDriveError(f"Failed to refresh access token: {e}")
            else:
                raise GoogleDriveError("Access token expired and no refresh token available")

        if response.status_code != 200:
            try:
                error_data = response.json()
                error_msg = error_data.get('error', {}).get('message', 'Unknown error')
            except (json.JSONDecodeError, ValueError):
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
            raise GoogleDriveError(f"Google Drive API error: {error_msg}")

        return response.content, filename, mime_type


async def move_drive_file(
    account: "ConnectedAccount",
    db: Session,
    file_id: str,
    new_parent_id: str,
) -> Dict[str, Any]:
    """Move a file or folder to a different parent folder in Google Drive."""
    access_token = await get_valid_access_token(account, db)

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Get current parents first
        meta = await get_file_metadata(account, db, file_id)
        old_parents = meta.get("parents", [])

        params = {}
        if old_parents:
            params["removeParents"] = ",".join(old_parents)
        if new_parent_id and new_parent_id != "root":
            params["addParents"] = new_parent_id

        response = await client.patch(
            f"https://www.googleapis.com/drive/v3/files/{file_id}",
            headers={"Authorization": f"Bearer {access_token}"},
            params=params,
        )

        if response.status_code == 401:
            if account.refresh_token:
                try:
                    token_response = await refresh_access_token(account.refresh_token)
                    account.access_token = token_response["access_token"]
                    db.commit()
                    response = await client.patch(
                        f"https://www.googleapis.com/drive/v3/files/{file_id}",
                        headers={"Authorization": f"Bearer {token_response['access_token']}"},
                        params=params,
                    )
                except Exception as e:
                    raise GoogleDriveError(f"Failed to refresh access token: {e}")
            else:
                raise GoogleDriveError("Access token expired and no refresh token available")

        if response.status_code != 200:
            try:
                error_data = response.json()
                error_msg = error_data.get('error', {}).get('message', 'Unknown error')
            except (json.JSONDecodeError, ValueError):
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
            raise GoogleDriveError(f"Google Drive API error: {error_msg}")

        return response.json()


async def copy_drive_file(
    account: "ConnectedAccount",
    db: Session,
    file_id: str,
    new_parent_id: str,
) -> Dict[str, Any]:
    """Copy a file to a different folder in Google Drive."""
    access_token = await get_valid_access_token(account, db)

    body = {}
    if new_parent_id and new_parent_id != "root":
        body["parents"] = [new_parent_id]

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"https://www.googleapis.com/drive/v3/files/{file_id}/copy",
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
                        f"https://www.googleapis.com/drive/v3/files/{file_id}/copy",
                        headers={"Authorization": f"Bearer {token_response['access_token']}"},
                        json=body,
                    )
                except Exception as e:
                    raise GoogleDriveError(f"Failed to refresh access token: {e}")
            else:
                raise GoogleDriveError("Access token expired and no refresh token available")

        if response.status_code != 200:
            try:
                error_data = response.json()
                error_msg = error_data.get('error', {}).get('message', 'Unknown error')
            except (json.JSONDecodeError, ValueError):
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
            raise GoogleDriveError(f"Google Drive copy error: {error_msg}")

        return response.json()


async def get_storage_quota(
    account: "ConnectedAccount",
    db: Session,
) -> Dict[str, Any]:
    """Get storage quota information from Google Drive.

    Returns dict with total_space, used_space, available_space (all in bytes).
    """
    access_token = await get_valid_access_token(account, db)

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            "https://www.googleapis.com/drive/v3/about",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"fields": "storageQuota"},
        )

        if response.status_code == 401:
            if account.refresh_token:
                try:
                    token_response = await refresh_access_token(account.refresh_token)
                    account.access_token = token_response["access_token"]
                    db.commit()
                    response = await client.get(
                        "https://www.googleapis.com/drive/v3/about",
                        headers={"Authorization": f"Bearer {token_response['access_token']}"},
                        params={"fields": "storageQuota"},
                    )
                except Exception as e:
                    raise GoogleDriveError(f"Failed to refresh access token: {e}")
            else:
                raise GoogleDriveError("Access token expired and no refresh token available")

        if response.status_code != 200:
            try:
                error_data = response.json()
                error_msg = error_data.get('error', {}).get('message', 'Unknown error')
            except (json.JSONDecodeError, ValueError):
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
            raise GoogleDriveError(f"Google Drive API error: {error_msg}")

        try:
            data = response.json()
        except Exception:
            raise GoogleDriveError("Failed to parse quota response")

        quota = data.get("storageQuota", {})
        return {
            "total_space": int(quota.get("limit", 0)) if quota.get("limit") else None,
            "used_space": int(quota.get("usage", 0)),
            "available_space": int(quota.get("limit", 0)) - int(quota.get("usage", 0)) if quota.get("limit") else None,
        }


async def list_trash_files(
    account: "ConnectedAccount",
    db: Session,
) -> List[Dict[str, Any]]:
    """List files in Google Drive trash."""
    access_token = await get_valid_access_token(account, db)

    all_files = []
    page_token = None

    async with httpx.AsyncClient(timeout=30.0) as client:
        while True:
            params = {
                "q": "trashed = true",
                "pageSize": 100,
                "fields": "files(id,name,mimeType,size,modifiedTime,thumbnailLink,webViewLink,parents),nextPageToken",
                "orderBy": "modifiedTime desc",
            }
            if page_token:
                params["pageToken"] = page_token

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
                    except Exception as e:
                        raise GoogleDriveError(f"Failed to refresh access token: {e}")
                else:
                    raise GoogleDriveError("Access token expired and no refresh token available")

            if response.status_code != 200:
                try:
                    error_data = response.json()
                    error_msg = error_data.get('error', {}).get('message', 'Unknown error')
                except (json.JSONDecodeError, ValueError):
                    error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                raise GoogleDriveError(f"Google Drive API error: {error_msg}")

            data = response.json()
            files = data.get("files", [])
            all_files.extend(files)

            page_token = data.get("nextPageToken")
            if not page_token:
                break

    return all_files


async def restore_from_trash(
    account: "ConnectedAccount",
    db: Session,
    file_id: str,
) -> Dict[str, Any]:
    """Restore a file from Google Drive trash (untrash it)."""
    access_token = await get_valid_access_token(account, db)

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.patch(
            f"https://www.googleapis.com/drive/v3/files/{file_id}",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"trashed": False},
        )

        if response.status_code == 401:
            if account.refresh_token:
                try:
                    token_response = await refresh_access_token(account.refresh_token)
                    account.access_token = token_response["access_token"]
                    db.commit()
                    response = await client.patch(
                        f"https://www.googleapis.com/drive/v3/files/{file_id}",
                        headers={"Authorization": f"Bearer {token_response['access_token']}"},
                        json={"trashed": False},
                    )
                except Exception as e:
                    raise GoogleDriveError(f"Failed to refresh access token: {e}")
            else:
                raise GoogleDriveError("Access token expired and no refresh token available")

        if response.status_code != 200:
            try:
                error_data = response.json()
                error_msg = error_data.get('error', {}).get('message', 'Unknown error')
            except (json.JSONDecodeError, ValueError):
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
            raise GoogleDriveError(f"Google Drive API error: {error_msg}")

        return response.json()