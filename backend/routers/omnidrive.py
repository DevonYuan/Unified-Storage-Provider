"""OmniDrive unified view router — single virtual filesystem across providers."""

from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from database_driver import get_db
from services.omnidrive_tree import (
    get_merged_files,
    upload_file_to_pool,
    create_folder_in_pool,
    rename_item,
    delete_item,
    invalidate_cache,
    get_provider_accounts,
    parse_virtual_id,
)

router = APIRouter(prefix="/omnidrive", tags=["OmniDrive"])


class OmniDriveFileListResponse(BaseModel):
    path: str
    items: list[dict]
    total_items: int
    next_page_token: Optional[str] = None


class CreateFolderRequest(BaseModel):
    name: str
    parent_path: str = "/"


class RenameRequest(BaseModel):
    name: str


# ── Read ─────────────────────────────────────────────────────────────────────

@router.get("/files")
async def list_files(
    path: str = Query("/", description="Virtual path to list"),
    page_size: int = Query(100, ge=1, le=500),
    page_token: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """List files and folders in the unified OmniDrive view."""
    google_account, ms_account = get_provider_accounts(db)

    if not google_account and not ms_account:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No storage providers connected. Connect Google Drive or OneDrive first.",
        )

    try:
        result = await get_merged_files(
            google_account=google_account,
            ms_account=ms_account,
            db=db,
            path=path,
            page_size=page_size,
            page_token=page_token,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ── Write ────────────────────────────────────────────────────────────────────

@router.post("/files/upload")
async def upload_file(
    file: UploadFile = File(...),
    parent_path: str = "/",
    db: Session = Depends(get_db),
):
    """Upload a file to the unified storage pool."""
    google_account, ms_account = get_provider_accounts(db)

    if not google_account and not ms_account:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No storage providers connected.",
        )

    try:
        result = await upload_file_to_pool(
            file=file,
            parent_path=parent_path,
            google_account=google_account,
            ms_account=ms_account,
            db=db,
        )
        return result
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/folders")
async def create_folder(
    request: CreateFolderRequest,
    db: Session = Depends(get_db),
):
    """Create a new folder in the unified storage pool."""
    google_account, ms_account = get_provider_accounts(db)

    if not google_account and not ms_account:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No storage providers connected.",
        )

    if not request.name.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Folder name is required.")

    try:
        result = await create_folder_in_pool(
            folder_name=request.name.strip(),
            parent_path=request.parent_path,
            google_account=google_account,
            ms_account=ms_account,
            db=db,
        )
        return result
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.patch("/files/{virtual_id}")
async def rename_file(
    virtual_id: str,
    request: RenameRequest,
    db: Session = Depends(get_db),
):
    """Rename a file or folder in the unified view."""
    google_account, ms_account = get_provider_accounts(db)

    if not request.name.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New name is required.")

    try:
        result = await rename_item(
            virtual_id=virtual_id,
            new_name=request.name.strip(),
            google_account=google_account,
            ms_account=ms_account,
            db=db,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/files/{virtual_id}")
async def delete_file(
    virtual_id: str,
    db: Session = Depends(get_db),
):
    """Delete a file or folder from the unified view."""
    google_account, ms_account = get_provider_accounts(db)

    try:
        await delete_item(
            virtual_id=virtual_id,
            google_account=google_account,
            ms_account=ms_account,
            db=db,
        )
        return {"status": "deleted", "virtual_id": virtual_id}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/files/{virtual_id}/download")
async def download_file(
    virtual_id: str,
    db: Session = Depends(get_db),
):
    """Download a file from the unified view."""
    from fastapi.responses import StreamingResponse
    from io import BytesIO

    provider, real_id = parse_virtual_id(virtual_id)
    google_account, ms_account = get_provider_accounts(db)

    if provider == "merged":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot download a merged folder directly")

    account = google_account if provider == "google" else ms_account
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No {provider} account connected")

    try:
        if account.provider.value == "google_drive":
            from services.google_drive import download_drive_file
            content, filename, mime_type = await download_drive_file(account, db, real_id)
        else:
            from services.microsoft_graph import download_drive_file as download_ms_file
            content, filename, mime_type = await download_ms_file(account, db, real_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return StreamingResponse(
        BytesIO(content),
        media_type=mime_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Maintenance ──────────────────────────────────────────────────────────────

@router.post("/refresh")
async def refresh_tree():
    """Force a full rebuild of the in-memory unified tree."""
    invalidate_cache()
    return {"status": "refreshed", "message": "Unified tree cache cleared. Next request will rebuild from providers."}
