from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import Optional
import io
from fastapi.responses import Response

from ...db.session import get_db
from ...models.user import User
from ...api.deps import get_current_user
from ...services.google_drive_service import GoogleDriveService

router = APIRouter(
    prefix="/google",
    tags=["google-drive"]
)

# Initialize service
drive_service = GoogleDriveService()

@router.get("/oauth/url")
async def get_google_oauth_url(
    current_user: User = Depends(get_current_user),
    state: Optional[str] = None
):
    """Get Google OAuth 2.0 authorization URL."""
    try:
        auth_url = drive_service.get_oauth_url(state=state)
        return {"auth_url": auth_url}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate OAuth URL"
        )

@router.get("/oauth/callback")
async def google_oauth_callback(
    code: str,
    state: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Handle Google OAuth 2.0 callback."""
    try:
        # Exchange authorization code for tokens
        token_data = drive_service.exchange_code_for_tokens(code)

        # Store tokens in database
        success = drive_service.store_tokens(
            user_id=current_user.id,
            access_token=token_data['access_token'],
            refresh_token=token_data['refresh_token'],
            expires_at=token_data['expires_at']
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to store OAuth tokens"
            )

        return {"message": "Google Drive connected successfully"}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to authenticate with Google Drive"
        )

@router.post("/tokens")
async def store_google_tokens(
    token_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Store Google OAuth tokens for the current user."""
    try:
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        expires_at = token_data.get("expires_at")

        if not all([access_token, refresh_token, expires_at]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing required token fields"
            )

        success = drive_service.store_tokens(
            user_id=current_user.id,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to store tokens"
            )

        # Return the token data for confirmation (excluding sensitive data in real apps)
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_at": expires_at
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/tokens")
async def get_google_tokens(
    current_user: User = Depends(get_current_user)
):
    """Get stored Google OAuth tokens for the current user."""
    try:
        tokens = drive_service.get_tokens(current_user.id)
        if not tokens:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No tokens found for user"
            )
        return tokens
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/files")
async def list_google_files(
    parent_id: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """List files in Google Drive."""
    try:
        files = drive_service.list_files(current_user.id, parent_id=parent_id)

        # Transform Google API response to match our expected format
        formatted_files = []
        for file_obj in files:
            # Get parent_id from parents array (first parent or None)
            parent_id_val = None
            if file_obj.get('parents') and len(file_obj['parents']) > 0:
                parent_id_val = file_obj['parents'][0]

            # Convert size to int if present, otherwise None
            size_val = None
            if file_obj.get('size'):
                try:
                    size_val = int(file_obj['size'])
                except (ValueError, TypeError):
                    size_val = None

            formatted_file = {
                "id": file_obj.get('id'),
                "name": file_obj.get('name'),
                "mime_type": file_obj.get('mimeType'),
                "size": size_val,
                "parent_id": parent_id_val,
                "modifiedTime": file_obj.get('modifiedTime')  # Keep as-is for now
            }
            formatted_files.append(formatted_file)

        return {"files": formatted_files}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list files"
        )

@router.post("/files/upload")
async def upload_google_file(
    file: UploadFile = File(...),
    parent_id: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Upload a file to Google Drive."""
    try:
        # Read file content
        file_content = await file.read()
        file_stream = io.BytesIO(file_content)

        # Upload to Google Drive
        result = drive_service.upload_file(
            user_id=current_user.id,
            file_data=file_stream,
            filename=file.filename,
            mime_type=file.content_type or 'application/octet-stream',
            parent_id=parent_id
        )

        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload file"
        )

@router.get("/files/{file_id}/download")
async def download_google_file(
    file_id: str,
    current_user: User = Depends(get_current_user)
):
    """Download a file from Google Drive."""
    try:
        file_content = drive_service.download_file(current_user.id, file_id)

        return Response(
            content=file_content,
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f"attachment; filename={file_id}"
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download file"
        )

@router.post("/folders")
async def create_google_folder(
    folder_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Create a folder in Google Drive."""
    try:
        folder_name = folder_data.get("name")
        parent_id = folder_data.get("parent_id")

        if not folder_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Folder name is required"
            )

        result = drive_service.create_folder(
            user_id=current_user.id,
            folder_name=folder_name,
            parent_id=parent_id
        )

        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create folder"
        )

@router.delete("/files/{file_id}")
async def delete_google_file(
    file_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete a file from Google Drive."""
    try:
        success = drive_service.delete_file(current_user.id, file_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        return {"message": "File deleted successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete file"
        )

@router.patch("/files/{file_id}")
async def rename_google_file(
    file_id: str,
    file_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Rename a file in Google Drive."""
    try:
        new_name = file_data.get("name")
        if not new_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File name is required"
            )

        result = drive_service.rename_file(
            user_id=current_user.id,
            file_id=file_id,
            new_name=new_name
        )

        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to rename file"
        )