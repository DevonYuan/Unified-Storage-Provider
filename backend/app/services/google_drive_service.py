import os
import json
import time
import random
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, BinaryIO
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
import io

from ..core.config import settings
from ..models.google_drive import GoogleOAuthToken, GoogleFile
from ..db.session import SessionLocal
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Google Drive API scopes
SCOPES = [
    'https://www.googleapis.com/auth/drive.file',  # Access to files created by the app
    'https://www.googleapis.com/auth/drive.readonly',  # View access to files
]

class GoogleDriveService:
    def __init__(self):
        self.client_id = settings.GOOGLE_CLIENT_ID
        self.client_secret = settings.GOOGLE_CLIENT_SECRET
        self.redirect_uri = settings.GOOGLE_REDIRECT_URI

    def get_oauth_url(self, state: str = None) -> str:
        """Generate Google OAuth 2.0 authorization URL."""
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [self.redirect_uri]
                }
            },
            scopes=SCOPES
        )
        flow.redirect_uri = self.redirect_uri

        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent',
            state=state
        )

        return authorization_url

    def exchange_code_for_tokens(self, authorization_code: str) -> Dict[str, Any]:
        """Exchange authorization code for access and refresh tokens."""
        try:
            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "redirect_uris": [self.redirect_uri]
                    }
                },
                scopes=SCOPES
            )
            flow.redirect_uri = self.redirect_uri

            flow.fetch_token(code=authorization_code)

            credentials = flow.credentials

            return {
                'access_token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'expires_at': credentials.expiry
            }
        except Exception as e:
            logger.error(f"Error exchanging code for tokens: {str(e)}")
            raise e

    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh an expired access token using the refresh token."""
        try:
            credentials = Credentials(
                token=None,
                refresh_token=refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=self.client_id,
                client_secret=self.client_secret
            )

            request = Request()
            credentials.refresh(request)

            return {
                'access_token': credentials.token,
                'expires_at': credentials.expiry
            }
        except Exception as e:
            logger.error(f"Error refreshing access token: {str(e)}")
            raise e

    def get_credentials(self, user_id: int) -> Optional[Credentials]:
        """Get valid Google credentials for a user."""
        db = SessionLocal()
        try:
            token_record = db.query(GoogleOAuthToken).filter(
                GoogleOAuthToken.user_id == user_id
            ).first()

            if not token_record:
                return None

            # Check if token is expired or about to expire (5 minutes buffer)
            if token_record.expires_at <= datetime.utcnow() + timedelta(minutes=5):
                # Token is expired or expiring soon, refresh it
                try:
                    token_data = self.refresh_access_token(token_record.refresh_token)

                    # Update token in database
                    token_record.access_token = token_data['access_token']
                    token_record.expires_at = token_data['expires_at']
                    token_record.updated_at = datetime.utcnow()
                    db.commit()

                    logger.info(f"Refreshed access token for user {user_id}")
                except Exception as e:
                    logger.error(f"Failed to refresh token for user {user_id}: {str(e)}")
                    return None

            # Create credentials object
            credentials = Credentials(
                token=token_record.access_token,
                refresh_token=token_record.refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=self.client_id,
                client_secret=self.client_secret,
                scopes=SCOPES
            )

            return credentials

        finally:
            db.close()

    def _execute_with_retry(self, func, *args, **kwargs):
        """Execute a Google API call with exponential backoff retry logic."""
        max_retries = 3
        base_delay = 1  # seconds
        max_delay = 30  # seconds

        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except HttpError as error:
                if error.resp.status in [429, 500, 502, 503, 504]:
                    if attempt == max_retries - 1:  # Last attempt
                        raise

                    # Calculate delay with exponential backoff and jitter
                    delay = min(base_delay * (2 ** attempt) + random.uniform(0, 1), max_delay)
                    logger.warning(
                        f"Google API error {error.resp.status}, retrying in {delay:.2f}s "
                        f"(attempt {attempt + 1}/{max_retries}): {error}"
                    )
                    time.sleep(delay)
                else:
                    # Non-retryable error
                    raise
            except Exception as e:
                # Non-HTTP errors are not retried
                raise e

    def store_tokens(self, user_id: int, access_token: str, refresh_token: str, expires_at: datetime) -> bool:
        """Store or update OAuth tokens for a user."""
        db = SessionLocal()
        try:
            # Check if token record already exists
            token_record = db.query(GoogleOAuthToken).filter(
                GoogleOAuthToken.user_id == user_id
            ).first()

            if token_record:
                # Update existing record
                token_record.access_token = access_token
                token_record.refresh_token = refresh_token
                token_record.expires_at = expires_at
                token_record.updated_at = datetime.utcnow()
            else:
                # Create new record
                token_record = GoogleOAuthToken(
                    user_id=user_id,
                    access_token=access_token,
                    refresh_token=refresh_token,
                    expires_at=expires_at
                )
                db.add(token_record)

            db.commit()
            logger.info(f"Stored Google OAuth tokens for user {user_id}")
            return True

        except Exception as e:
            db.rollback()
            logger.error(f"Error storing tokens for user {user_id}: {str(e)}")
            return False
        finally:
            db.close()

    def get_tokens(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get stored OAuth tokens for a user."""
        db = SessionLocal()
        try:
            token_record = db.query(GoogleOAuthToken).filter(
                GoogleOAuthToken.user_id == user_id
            ).first()

            if not token_record:
                return None

            return {
                'access_token': token_record.access_token,
                'refresh_token': token_record.refresh_token,
                'expires_at': token_record.expires_at
            }

        finally:
            db.close()

    def delete_tokens(self, user_id: int) -> bool:
        """Delete OAuth tokens for a user (disconnect)."""
        db = SessionLocal()
        try:
            token_record = db.query(GoogleOAuthToken).filter(
                GoogleOAuthToken.user_id == user_id
            ).first()

            if token_record:
                db.delete(token_record)
                db.commit()
                logger.info(f"Deleted Google OAuth tokens for user {user_id}")
                return True
            else:
                logger.warning(f"No tokens found for user {user_id} to delete")
                return False

        except Exception as e:
            db.rollback()
            logger.error(f"Error deleting tokens for user {user_id}: {str(e)}")
            return False
        finally:
            db.close()

    def _get_drive_service(self, user_id: int):
        """Get an authorized Google Drive service instance."""
        credentials = self.get_credentials(user_id)
        if not credentials:
            raise Exception("No valid credentials found for user")

        return build('drive', 'v3', credentials=credentials, cache_discovery=False)

    def list_files(self, user_id: int, parent_id: str = None, page_size: int = 100) -> List[Dict[str, Any]]:
        """List files in Google Drive."""
        try:
            service = self._get_drive_service(user_id)

            # Build query
            query = "trashed = false"
            if parent_id:
                query += f" and '{parent_id}' in parents"
            else:
                query += " and 'me' in owners"  # Only files owned by the user

            # Execute with retry
            results = self._execute_with_retry(
                service.files().list,
                q=query,
                pageSize=page_size,
                fields="nextPageToken, files(id, name, mimeType, size, parents, modifiedTime, thumbnailLink)",
                orderBy="folder,name"
            )

            files = results.get('files', [])

            # Process and cache files
            self._cache_files(user_id, files)

            return files

        except Exception as e:
            logger.error(f"Error listing files for user {user_id}: {str(e)}")
            raise e

    def upload_file(self, user_id: int, file_data: BinaryIO, filename: str,
                   mime_type: str, parent_id: str = None) -> Dict[str, Any]:
        """Upload a file to Google Drive."""
        try:
            service = self._get_drive_service(user_id)

            # Prepare file metadata
            file_metadata = {'name': filename}
            if parent_id:
                file_metadata['parents'] = [parent_id]

            # Prepare media
            media = MediaIoBaseUpload(file_data, mimetype=mime_type, resumable=True)

            # Execute upload with retry
            file = self._execute_with_retry(
                service.files().create,
                body=file_metadata,
                media_body=media,
                fields='id, name, mimeType, size, parents, modifiedTime, thumbnailLink'
            )

            # Cache the uploaded file
            self._cache_file(user_id, file)

            return file

        except Exception as e:
            logger.error(f"Error uploading file for user {user_id}: {str(e)}")
            raise e

    def download_file(self, user_id: int, file_id: str) -> bytes:
        """Download a file from Google Drive."""
        try:
            service = self._get_drive_service(user_id)

            # Get file metadata first
            file_metadata = self._execute_with_retry(
                service.files().get,
                fileId=file_id,
                fields='name, mimeType, size'
            )

            # Download file content
            request = service.files().get_media(fileId=file_id)
            file_buffer = io.BytesIO()
            downloader = MediaIoBaseDownload(file_buffer, request)

            done = False
            while done is False:
                status, done = self._execute_with_retry(
                    downloader.next_chunk
                )

            file_buffer.seek(0)
            return file_buffer.read()

        except Exception as e:
            logger.error(f"Error downloading file {file_id} for user {user_id}: {str(e)}")
            raise e

    def create_folder(self, user_id: int, folder_name: str, parent_id: str = None) -> Dict[str, Any]:
        """Create a folder in Google Drive."""
        try:
            service = self._get_drive_service(user_id)

            # Prepare folder metadata
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            if parent_id:
                file_metadata['parents'] = [parent_id]

            # Execute with retry
            file = self._execute_with_retry(
                service.files().create,
                body=file_metadata,
                fields='id, name, mimeType, parents, modifiedTime'
            )

            # Cache the created folder
            self._cache_file(user_id, file)

            return file

        except Exception as e:
            logger.error(f"Error creating folder for user {user_id}: {str(e)}")
            raise e

    def delete_file(self, user_id: int, file_id: str) -> bool:
        """Delete a file from Google Drive."""
        try:
            service = self._get_drive_service(user_id)

            # Execute deletion with retry
            self._execute_with_retry(
                service.files().delete,
                fileId=file_id
            )

            # Remove from cache
            self._remove_from_cache(user_id, file_id)

            return True

        except Exception as e:
            logger.error(f"Error deleting file {file_id} for user {user_id}: {str(e)}")
            raise e

    def rename_file(self, user_id: int, file_id: str, new_name: str) -> Dict[str, Any]:
        """Rename a file in Google Drive."""
        try:
            service = self._get_drive_service(user_id)

            # Execute rename with retry
            file = self._execute_with_retry(
                service.files().update,
                fileId=file_id,
                body={'name': new_name},
                fields='id, name, mimeType, size, parents, modifiedTime'
            )

            # Update cache
            self._update_cache(user_id, file_id, file)

            return file

        except Exception as e:
            logger.error(f"Error renaming file {file_id} for user {user_id}: {str(e)}")
            raise e

    def _cache_files(self, user_id: int, files: List[Dict[str, Any]]) -> None:
        """Cache multiple files in the database."""
        db = SessionLocal()
        try:
            for file_data in files:
                self._upsert_file_cache(db, user_id, file_data)
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Error caching files for user {user_id}: {str(e)}")
        finally:
            db.close()

    def _cache_file(self, user_id: int, file_data: Dict[str, Any]) -> None:
        """Cache a single file in the database."""
        db = SessionLocal()
        try:
            self._upsert_file_cache(db, user_id, file_data)
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Error caching file for user {user_id}: {str(e)}")
        finally:
            db.close()

    def _upsert_file_cache(self, db, user_id: int, file_data: Dict[str, Any]) -> None:
        """Insert or update a file in the cache."""
        file_id = file_data.get('id')
        if not file_id:
            return

        # Check if file already exists in cache
        cached_file = db.query(GoogleFile).filter(
            GoogleFile.user_id == user_id,
            GoogleFile.file_id == file_id
        ).first()

        # Parse modified time
        modified_time_str = file_data.get('modifiedTime')
        modified_time = None
        if modified_time_str:
            try:
                # Remove timezone info for simplicity (store as UTC naive)
                modified_time = datetime.fromisoformat(
                    modified_time_str.replace('Z', '+00:00')
                ).replace(tzinfo=None)
            except Exception:
                modified_time = datetime.utcnow()

        if cached_file:
            # Update existing record
            cached_file.name = file_data.get('name', cached_file.name)
            cached_file.mime_type = file_data.get('mimeType', cached_file.mime_type)
            cached_file.size = file_data.get('size')
            cached_file.parent_id = file_data.get('parents', [None])[0] if file_data.get('parents') else None
            cached_file.modified_time = modified_time or cached_file.modified_time
            cached_file.updated_at = datetime.utcnow()
        else:
            # Create new record
            new_file = GoogleFile(
                user_id=user_id,
                file_id=file_id,
                name=file_data.get('name', ''),
                mime_type=file_data.get('mimeType', 'application/octet-stream'),
                size=file_data.get('size'),
                parent_id=file_data.get('parents', [None])[0] if file_data.get('parents') else None,
                modified_time=modified_time or datetime.utcnow()
            )
            db.add(new_file)

    def _remove_from_cache(self, user_id: int, file_id: str) -> None:
        """Remove a file from the cache."""
        db = SessionLocal()
        try:
            cached_file = db.query(GoogleFile).filter(
                GoogleFile.user_id == user_id,
                GoogleFile.file_id == file_id
            ).first()

            if cached_file:
                db.delete(cached_file)
                db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Error removing file {file_id} from cache for user {user_id}: {str(e)}")
        finally:
            db.close()

    def _update_cache(self, user_id: int, file_id: str, file_data: Dict[str, Any]) -> None:
        """Update a file in the cache."""
        db = SessionLocal()
        try:
            cached_file = db.query(GoogleFile).filter(
                GoogleFile.user_id == user_id,
                GoogleFile.file_id == file_id
            ).first()

            if cached_file:
                cached_file.name = file_data.get('name', cached_file.name)
                cached_file.mime_type = file_data.get('mimeType', cached_file.mime_type)
                cached_file.size = file_data.get('size')
                cached_file.parent_id = file_data.get('parents', [None])[0] if file_data.get('parents') else None

                # Parse modified time
                modified_time_str = file_data.get('modifiedTime')
                if modified_time_str:
                    try:
                        modified_time = datetime.fromisoformat(
                            modified_time_str.replace('Z', '+00:00')
                        ).replace(tzinfo=None)
                        cached_file.modified_time = modified_time
                    except Exception:
                        pass  # Keep existing modified time if parsing fails

                cached_file.updated_at = datetime.utcnow()
                db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating file {file_id} in cache for user {user_id}: {str(e)}")
        finally:
            db.close()

    def get_cached_files(self, user_id: int, parent_id: str = None) -> List[Dict[str, Any]]:
        """Get cached files for a user."""
        db = SessionLocal()
        try:
            query = db.query(GoogleFile).filter(GoogleFile.user_id == user_id)

            if parent_id is not None:
                query = query.filter(GoogleFile.parent_id == parent_id)
            else:
                # Get root-level files (no parent)
                query = query.filter(GoogleFile.parent_id.is_(None))

            cached_files = query.all()

            # Convert to dictionary format similar to Google API response
            files = []
            for cf in cached_files:
                files.append({
                    'id': cf.file_id,
                    'name': cf.name,
                    'mimeType': cf.mime_type,
                    'size': cf.size,
                    'parents': [cf.parent_id] if cf.parent_id else [],
                    'modifiedTime': cf.modified_time.isoformat() + 'Z' if cf.modified_time else None
                })

            return files

        finally:
            db.close()