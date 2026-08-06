"""OmniDrive unified tree service — merges Google Drive and OneDrive into a single virtual filesystem.

This module maintains an in-memory cache of merged directory listings and a
path→provider mapping so the omnidrive router can navigate, upload, rename,
and delete across both providers as if they were one.
"""

from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from fastapi import UploadFile
from sqlalchemy.orm import Session

from models import ConnectedAccount, ProviderType, UploadRouting, RepairLog
from services.google_drive import (
    GoogleDriveError,
    list_drive_files,
    upload_drive_file,
    create_drive_folder,
)
from services.microsoft_graph import (
    MicrosoftGraphError,
    list_drive_files as list_ms_files,
    upload_drive_file as upload_ms_file,
    create_drive_folder as create_ms_folder,
)

# ── In-memory state ──────────────────────────────────────────────────────────

# Cache: virtual path → merged file list (list of dicts in FileItem shape)
_listing_cache: Dict[str, List[Dict[str, Any]]] = {}

# Provider mapping: virtual path → [(provider_str, real_folder_id), …]
# Only populated for merged folders (exists on both providers).
# provider_str is "google" or "onedrive".
_path_mapping: Dict[str, List[Tuple[str, str]]] = {}

# ── Helpers ──────────────────────────────────────────────────────────────────

FOLDER_MIME = "application/vnd.google-apps.folder"


def encode_virtual_id(provider: str, real_id: str) -> str:
    """Encode a provider + real ID into a virtual ID."""
    return f"{provider}:{real_id}"


def parse_virtual_id(virtual_id: str) -> Tuple[str, str]:
    """Parse a virtual ID into (provider, real_id)."""
    parts = virtual_id.split(":", 1)
    if len(parts) != 2:
        raise ValueError(f"Invalid virtual ID: {virtual_id}")
    return parts[0], parts[1]


def _is_folder(item: Dict[str, Any]) -> bool:
    """Determine if a provider item is a folder."""
    if item.get("is_folder"):
        return True
    mime = item.get("mimeType", "")
    return mime == FOLDER_MIME


def _normalise_item(item: Dict[str, Any], provider: str) -> Dict[str, Any]:
    """Convert a raw provider item into the common internal format used for merging."""
    is_folder = _is_folder(item)
    size_raw = item.get("size")
    try:
        size_int = int(size_raw) if size_raw is not None else None
    except (ValueError, TypeError):
        size_int = None

    return {
        "id": item.get("id", ""),
        "name": item.get("name", ""),
        "mimeType": item.get("mimeType", FOLDER_MIME if is_folder else "application/octet-stream"),
        "size": size_int,
        "modifiedTime": item.get("modifiedTime"),
        "thumbnailLink": item.get("thumbnailLink"),
        "webViewLink": item.get("webViewLink"),
        "is_folder": is_folder,
        "item_count": item.get("item_count"),
        "_provider": provider,
    }


def _build_fileitem(norm: Dict[str, Any], providers: List[str]) -> Dict[str, Any]:
    """Build a FileItem-shaped dict from a normalised item + providers list."""
    from routers.storage import get_mime_type_category, format_file_size, format_modified_time

    mime = norm["mimeType"]
    category = get_mime_type_category(mime)
    size = norm["size"]
    mod_time = norm["modifiedTime"]

    vid: str
    if len(providers) == 1:
        vid = encode_virtual_id(providers[0], norm["id"])
    else:
        vid = encode_virtual_id("merged", norm["name"])

    return {
        "virtual_id": vid,
        "name": norm["name"],
        "providers": providers,
        "mime_type": mime,
        "category": category,
        "size": size,
        "size_formatted": format_file_size(size) if size else None,
        "modified_time": mod_time,
        "modified_time_formatted": format_modified_time(mod_time) if mod_time else None,
        "thumbnail_link": norm.get("thumbnailLink"),
        "web_view_link": norm.get("webViewLink"),
        "is_folder": norm["is_folder"],
        "item_count": norm.get("item_count"),
    }


# ── Provider fetching ────────────────────────────────────────────────────────

async def _fetch_all_google(
    account: ConnectedAccount, db: Session, parent_id: str
) -> List[Dict[str, Any]]:
    """Fetch every file from a Google Drive folder (follows all pages)."""
    raw = await list_drive_files(account, db, parent_id=parent_id, page_size=1000)
    return [_normalise_item(item, "google") for item in raw]


async def _fetch_all_onedrive(
    account: ConnectedAccount, db: Session, parent_id: str
) -> List[Dict[str, Any]]:
    """Fetch every file from a OneDrive folder (follows all pages).

    Wraps the existing list_ms_files which already normalises through
    _ms_item_to_fileitem, so we just normalise again for the _provider tag.
    """
    raw = await list_ms_files(account, db, parent_id=parent_id, page_size=1000)
    return [_normalise_item(item, "onedrive") for item in raw]


# ── Merge algorithm ──────────────────────────────────────────────────────────

def _merge_two_lists(
    google_items: List[Dict[str, Any]],
    ms_items: List[Dict[str, Any]],
    virtual_parent_path: str,
) -> List[Dict[str, Any]]:
    """Merge two provider file lists into a single unified list.

    Collision rules (see phase4.md):
    - Same-name folders → merge into one (providers=["google","onedrive"])
    - Same-name files → force-rename both with "-google" / "-onedrive" suffix
    - File-folder collision → force-rename the file, keep folder name
    - Double-collision on forced rename → append counter until unique
    """
    # Build lookup by lowercased name
    by_name: Dict[str, List[Dict[str, Any]]] = {}
    for item in google_items + ms_items:
        key = item["name"].lower()
        by_name.setdefault(key, []).append(item)

    merged: List[Dict[str, Any]] = []

    for key, group in by_name.items():
        if len(group) == 1:
            item = group[0]
            merged.append(_build_fileitem(item, [item["_provider"]]))
            continue

        # Multiple items with same name — classify
        folders = [i for i in group if i["is_folder"]]
        files = [i for i in group if not i["is_folder"]]

        if folders and not files:
            # All folders — merge into one
            representative = folders[0]
            providers_list = sorted({f["_provider"] for f in folders})
            merged_item = _build_fileitem(representative, providers_list)
            # Sum child counts
            total_children = sum(f.get("item_count") or 0 for f in folders)
            merged_item["item_count"] = total_children

            # Register in path mapping for later navigation
            child_path = _join_path(virtual_parent_path, representative["name"])
            _path_mapping[child_path] = [
                (f["_provider"], f["id"]) for f in folders
            ]

            merged.append(merged_item)

        elif files and not folders:
            # All files — force-rename each with provider suffix
            for item in files:
                renamed = _force_rename_file(item, group)
                merged.append(_build_fileitem(renamed, [item["_provider"]]))

        else:
            # File-folder collision — rename the file(s), keep folder(s)
            for folder_item in folders:
                providers_list = sorted({f["_provider"] for f in folders})
                merged_item = _build_fileitem(folder_item, providers_list)
                total_children = sum(f.get("item_count") or 0 for f in folders)
                merged_item["item_count"] = total_children
                child_path = _join_path(virtual_parent_path, folder_item["name"])
                _path_mapping[child_path] = [
                    (f["_provider"], f["id"]) for f in folders
                ]
                merged.append(merged_item)

            for file_item in files:
                renamed = _force_rename_file(file_item, group)
                merged.append(_build_fileitem(renamed, [file_item["_provider"]]))

    # Sort: folders first, then by name
    merged.sort(key=lambda x: (not x["is_folder"], x["name"].lower()))
    return merged


def _force_rename_file(
    item: Dict[str, Any], all_group: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Force-rename a file by appending provider suffix, with counter fallback."""
    original_name: str = item["name"]
    provider = item["_provider"]
    dot_idx = original_name.rfind(".")
    if dot_idx > 0:
        base, ext = original_name[:dot_idx], original_name[dot_idx:]
    else:
        base, ext = original_name, ""

    # Collect all names in this group for collision checking
    existing_names = {i["name"].lower() for i in all_group}

    for counter in range(1, 101):
        if counter == 1:
            candidate = f"{base}-{provider}{ext}"
        else:
            candidate = f"{base}-{provider}-{counter}{ext}"
        if candidate.lower() not in existing_names:
            renamed = dict(item)
            renamed["name"] = candidate
            return renamed

    # Fallback: use a unique suffix (should never happen in practice)
    renamed = dict(item)
    renamed["name"] = f"{base}-{provider}-{datetime.now(timezone.utc).timestamp():.0f}{ext}"
    return renamed


def _join_path(parent: str, name: str) -> str:
    """Join a parent path and child name into a virtual path."""
    if parent == "/":
        return f"/{name}"
    return f"{parent}/{name}"


# ── Public API ───────────────────────────────────────────────────────────────

def invalidate_cache(path: Optional[str] = None):
    """Clear cached listings.  Pass a path to clear only that entry."""
    global _listing_cache, _path_mapping
    if path is None:
        _listing_cache.clear()
        _path_mapping.clear()
    else:
        _listing_cache.pop(path, None)
        # Also clear any child paths
        prefix = path.rstrip("/") + "/"
        for p in list(_listing_cache):
            if p == path or p.startswith(prefix):
                del _listing_cache[p]
        for p in list(_path_mapping):
            if p == path or p.startswith(prefix):
                del _path_mapping[p]


async def get_merged_files(
    google_account: Optional[ConnectedAccount],
    ms_account: Optional[ConnectedAccount],
    db: Session,
    path: str = "/",
    page_size: int = 100,
    page_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Return a paginated, merged file listing for *path*."""

    # Use cache if available (and no forced refresh)
    if path in _listing_cache:
        items = _listing_cache[path]
        return _paginate(items, path, page_size, page_token)

    # Determine which provider folders to fetch
    google_items: List[Dict[str, Any]] = []
    ms_items: List[Dict[str, Any]] = []
    errors: List[str] = []

    if path == "/":
        # Root: fetch from both providers' roots
        if google_account:
            try:
                google_items = await _fetch_all_google(google_account, db, "root")
            except GoogleDriveError as e:
                errors.append(f"Google Drive: {e}")
        if ms_account:
            try:
                ms_items = await _fetch_all_onedrive(ms_account, db, "root")
            except MicrosoftGraphError as e:
                errors.append(f"OneDrive: {e}")
    elif path in _path_mapping:
        # Merged folder or known path — fetch from each mapped provider folder
        for provider_str, real_id in _path_mapping[path]:
            try:
                if provider_str == "google" and google_account:
                    google_items = await _fetch_all_google(google_account, db, real_id)
                elif provider_str == "onedrive" and ms_account:
                    ms_items = await _fetch_all_onedrive(ms_account, db, real_id)
            except GoogleDriveError as e:
                errors.append(f"Google Drive: {e}")
            except MicrosoftGraphError as e:
                errors.append(f"OneDrive: {e}")
    else:
        # Non-merged folder — try to resolve via virtual ID in the parent's listing
        parent_path = "/" if "/" not in path.rstrip("/") else path.rsplit("/", 1)[0]
        if not parent_path:
            parent_path = "/"
        folder_name = path.rstrip("/").rsplit("/", 1)[-1]

        # Look through parent listing for this folder
        parent_items = _listing_cache.get(parent_path, [])
        matched = [i for i in parent_items if i["name"] == folder_name and i["is_folder"]]
        if matched:
            providers_list = matched[0].get("providers", [])
            for prov in providers_list:
                try:
                    if prov == "google" and google_account:
                        vid = matched[0]["virtual_id"]
                        if vid.startswith("google:"):
                            real_id = vid.split(":", 1)[1]
                            google_items = await _fetch_all_google(google_account, db, real_id)
                    elif prov == "onedrive" and ms_account:
                        vid = matched[0]["virtual_id"]
                        if vid.startswith("onedrive:"):
                            real_id = vid.split(":", 1)[1]
                            ms_items = await _fetch_all_onedrive(ms_account, db, real_id)
                except GoogleDriveError as e:
                    errors.append(f"Google Drive: {e}")
                except MicrosoftGraphError as e:
                    errors.append(f"OneDrive: {e}")

    # If both providers failed with errors, raise
    if errors and not google_items and not ms_items:
        raise RuntimeError("; ".join(errors))

    # Merge
    merged = _merge_two_lists(google_items, ms_items, path)
    _listing_cache[path] = merged
    result = _paginate(merged, path, page_size, page_token)

    # Attach any per-provider errors so the frontend can surface them
    if errors:
        result["errors"] = errors

    return result


def _paginate(
    items: List[Dict[str, Any]], path: str, page_size: int, page_token: Optional[str]
) -> Dict[str, Any]:
    """Slice *items* according to page_size / page_token and return a response dict."""
    offset = 0
    if page_token:
        try:
            decoded = base64.urlsafe_b64decode(page_token.encode()).decode()
            offset = int(decoded)
        except Exception:
            offset = 0

    total_items = len(items)
    page = items[offset : offset + page_size]
    next_token: Optional[str] = None
    if offset + page_size < total_items:
        next_token = base64.urlsafe_b64encode(
            str(offset + page_size).encode()
        ).decode()

    return {
        "path": path,
        "items": page,
        "total_items": total_items,
        "next_page_token": next_token,
    }


# ── Upload routing ───────────────────────────────────────────────────────────

def _get_next_provider(db: Session) -> ProviderType:
    """Read the current next_provider from the upload_routing table."""
    row = db.query(UploadRouting).first()
    if not row:
        row = UploadRouting(id=1, next_provider=ProviderType.GOOGLE_DRIVE)
        db.add(row)
        db.commit()
    return row.next_provider


def _flip_provider(db: Session):
    """Flip the next_provider after a successful upload."""
    row = db.query(UploadRouting).first()
    if row:
        row.next_provider = (
            ProviderType.ONEDRIVE
            if row.next_provider == ProviderType.GOOGLE_DRIVE
            else ProviderType.GOOGLE_DRIVE
        )
        db.commit()


def _resolve_upload_target(
    parent_path: str,
    google_account: Optional[ConnectedAccount],
    ms_account: Optional[ConnectedAccount],
    db: Session,
) -> Tuple[Optional[ConnectedAccount], str]:
    """Determine which provider account and parent_id to use for an upload.

    Returns (account, parent_id).  May return (None, "") if no provider available.
    """
    # Case 1: root or merged folder → use alternation counter
    if parent_path == "/" or parent_path in _path_mapping:
        next_prov = _get_next_provider(db)
        primary = google_account if next_prov == ProviderType.GOOGLE_DRIVE else ms_account
        fallback = ms_account if next_prov == ProviderType.GOOGLE_DRIVE else google_account

        # Resolve parent_id for the chosen provider
        parent_id = "root"
        if parent_path in _path_mapping:
            for pstr, rid in _path_mapping[parent_path]:
                if pstr == "google" and next_prov == ProviderType.GOOGLE_DRIVE:
                    parent_id = rid
                elif pstr == "onedrive" and next_prov == ProviderType.ONEDRIVE:
                    parent_id = rid

        if primary:
            _flip_provider(db)
            return primary, parent_id
        elif fallback:
            _flip_provider(db)  # still flip so we don't retry failed provider
            fallback_parent = "root"
            if parent_path in _path_mapping:
                for pstr, rid in _path_mapping[parent_path]:
                    if (pstr == "google" and fallback.provider == ProviderType.GOOGLE_DRIVE) or \
                       (pstr == "onedrive" and fallback.provider == ProviderType.ONEDRIVE):
                        fallback_parent = rid
            return fallback, fallback_parent
        return None, ""

    # Case 2: non-merged folder — find which provider owns it
    parent_items = _listing_cache.get(parent_path, [])
    # If cache is empty, try to find the provider from path_mapping of parent
    parent_dir = "/" if "/" not in parent_path.rstrip("/") else parent_path.rsplit("/", 1)[0]
    if not parent_dir:
        parent_dir = "/"
    folder_name = parent_path.rstrip("/").rsplit("/", 1)[-1]

    if parent_dir in _listing_cache:
        parent_items = _listing_cache[parent_dir]
    else:
        parent_items = _listing_cache.get(parent_path, [])

    matched = [i for i in parent_items if i["name"] == folder_name and i["is_folder"]]
    if matched:
        providers_list = matched[0].get("providers", [])
        if "google" in providers_list and google_account:
            vid = matched[0]["virtual_id"]
            real_id = vid.split(":", 1)[1] if vid.startswith("google:") else "root"
            return google_account, real_id
        if "onedrive" in providers_list and ms_account:
            vid = matched[0]["virtual_id"]
            real_id = vid.split(":", 1)[1] if vid.startswith("onedrive:") else "root"
            return ms_account, real_id

    return None, ""


# ── Write operations ─────────────────────────────────────────────────────────

async def upload_file_to_pool(
    file: UploadFile,
    parent_path: str,
    google_account: Optional[ConnectedAccount],
    ms_account: Optional[ConnectedAccount],
    db: Session,
) -> Dict[str, Any]:
    """Upload a file to the unified pool."""
    account, parent_id = _resolve_upload_target(parent_path, google_account, ms_account, db)
    if not account:
        raise RuntimeError("No storage provider available for upload")

    if account.provider == ProviderType.GOOGLE_DRIVE:
        result = await upload_drive_file(account, db, file, parent_id)
    else:
        result = await upload_ms_file(account, db, file, parent_id)

    # Invalidate cache for parent path
    invalidate_cache(parent_path)

    norm = _normalise_item(result, "google" if account.provider == ProviderType.GOOGLE_DRIVE else "onedrive")
    return _build_fileitem(norm, [norm["_provider"]])


async def create_folder_in_pool(
    folder_name: str,
    parent_path: str,
    google_account: Optional[ConnectedAccount],
    ms_account: Optional[ConnectedAccount],
    db: Session,
) -> Dict[str, Any]:
    """Create a folder in the unified pool."""
    account, parent_id = _resolve_upload_target(parent_path, google_account, ms_account, db)
    if not account:
        raise RuntimeError("No storage provider available for folder creation")

    if account.provider == ProviderType.GOOGLE_DRIVE:
        result = await create_drive_folder(account, db, folder_name, parent_id)
    else:
        result = await create_ms_folder(account, db, folder_name, parent_id)

    invalidate_cache(parent_path)

    norm = _normalise_item(result, "google" if account.provider == ProviderType.GOOGLE_DRIVE else "onedrive")
    return _build_fileitem(norm, [norm["_provider"]])


async def rename_item(
    virtual_id: str,
    new_name: str,
    google_account: Optional[ConnectedAccount],
    ms_account: Optional[ConnectedAccount],
    db: Session,
) -> Dict[str, Any]:
    """Rename a file or folder.  For merged folders, propagates to all providers."""
    provider, real_id = parse_virtual_id(virtual_id)

    accounts_to_rename: List[Tuple[ConnectedAccount, str]] = []

    if provider == "merged":
        # Search path_mapping for entries where this folder name appears
        merged_path: Optional[str] = None
        for path, mappings in _path_mapping.items():
            folder_name = path.rstrip("/").rsplit("/", 1)[-1] if "/" in path else path.lstrip("/")
            if folder_name == real_id:  # real_id holds the folder name for merged items
                merged_path = path
                for pstr, rid in mappings:
                    if pstr == "google" and google_account:
                        accounts_to_rename.append((google_account, rid))
                    elif pstr == "onedrive" and ms_account:
                        accounts_to_rename.append((ms_account, rid))
                break
    elif provider == "google" and google_account:
        accounts_to_rename.append((google_account, real_id))
    elif provider == "onedrive" and ms_account:
        accounts_to_rename.append((ms_account, real_id))

    if not accounts_to_rename:
        raise ValueError(f"Cannot resolve virtual ID: {virtual_id}")

    # Best-effort rename across all providers
    renamed_results: List[Tuple[ConnectedAccount, Dict[str, Any]]] = []
    failed: List[Tuple[ConnectedAccount, str]] = []
    for acct, rid in accounts_to_rename:
        try:
            result = await _rename_on_provider(acct, rid, new_name, db)
            renamed_results.append((acct, result))
        except Exception as e:
            failed.append((acct, str(e)))

    # If any failed, attempt rollback of successful ones
    if failed and renamed_results:
        for acct, result in renamed_results:
            try:
                original_name = result.get("name")
                if original_name and original_name != new_name:
                    rid2 = result.get("id", "")
                    await _rename_on_provider(acct, rid2, original_name, db)
            except Exception:
                _log_repair(db, "rename", virtual_id, acct.provider, False,
                            "Rollback failed after partial rename — manual reconciliation needed")

    for acct, err_msg in failed:
        _log_repair(db, "rename", virtual_id, acct.provider, False, err_msg)

    # Update path_mapping if a merged folder was renamed
    if provider == "merged" and renamed_results and not failed:
        old_path = None
        for path in _path_mapping:
            folder_name = path.rstrip("/").rsplit("/", 1)[-1] if "/" in path else path.lstrip("/")
            if folder_name == real_id:
                old_path = path
                break
        if old_path:
            parent = old_path.rsplit("/", 1)[0] if "/" in old_path else ""
            new_path = f"{parent}/{new_name}" if parent else f"/{new_name}"
            _path_mapping[new_path] = _path_mapping.pop(old_path)

    # Invalidate all cache (rename affects paths)
    invalidate_cache()

    if renamed_results:
        best = renamed_results[0]
        norm = _normalise_item(best[1], "google" if best[0].provider == ProviderType.GOOGLE_DRIVE else "onedrive")
        providers_list = ["google"] if best[0].provider == ProviderType.GOOGLE_DRIVE else ["onedrive"]
        if len(renamed_results) > 1:
            providers_list = sorted(["google", "onedrive"])
        return _build_fileitem(norm, providers_list)

    raise RuntimeError(f"Rename failed on all providers: {failed}")


async def _rename_on_provider(
    account: ConnectedAccount, file_id: str, new_name: str, db: Session
) -> Dict[str, Any]:
    """Rename a file/folder on a specific provider. Returns the updated item."""
    import httpx
    from services.google_drive import get_valid_access_token as google_token
    from services.microsoft_graph import get_valid_access_token as ms_token

    if account.provider == ProviderType.GOOGLE_DRIVE:
        token = await google_token(account, db)
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.patch(
                f"https://www.googleapis.com/drive/v3/files/{file_id}",
                headers={"Authorization": f"Bearer {token}"},
                json={"name": new_name},
            )
            if resp.status_code != 200:
                try:
                    error_data = resp.json()
                    error_msg = error_data.get("error", {}).get("message", "Unknown error")
                except Exception:
                    error_msg = f"HTTP {resp.status_code}: {resp.text[:200]}"
                raise GoogleDriveError(error_msg)
            try:
                return resp.json()
            except Exception:
                raise GoogleDriveError("Provider returned invalid JSON")
    else:
        token = await ms_token(account, db)
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.patch(
                f"https://graph.microsoft.com/v1.0/me/drive/items/{file_id}",
                headers={"Authorization": f"Bearer {token}"},
                json={"name": new_name},
            )
            if resp.status_code != 200:
                try:
                    error_data = resp.json()
                    error_msg = error_data.get("error", {}).get("message", "Unknown error")
                except Exception:
                    error_msg = f"HTTP {resp.status_code}: {resp.text[:200]}"
                raise MicrosoftGraphError(error_msg)
            from services.microsoft_graph import _ms_item_to_fileitem
            try:
                return _ms_item_to_fileitem(resp.json())
            except Exception:
                raise MicrosoftGraphError("Provider returned invalid JSON")


def _get_original_name_from_result(result: Dict[str, Any]) -> Optional[str]:
    """Extract the name from a rename result for rollback purposes."""
    return result.get("name")


async def delete_item(
    virtual_id: str,
    google_account: Optional[ConnectedAccount],
    ms_account: Optional[ConnectedAccount],
    db: Session,
) -> None:
    """Delete a file or folder.  For merged folders, propagates to all providers."""
    provider, real_id = parse_virtual_id(virtual_id)

    accounts_to_delete: List[Tuple[ConnectedAccount, str]] = []

    if provider == "merged":
        for path, mappings in list(_path_mapping.items()):
            for pstr, rid in mappings:
                if pstr == "google" and google_account:
                    accounts_to_delete.append((google_account, rid))
                elif pstr == "onedrive" and ms_account:
                    accounts_to_delete.append((ms_account, rid))
            if accounts_to_delete:
                # Remove from path mapping
                del _path_mapping[path]
                break
    elif provider == "google" and google_account:
        accounts_to_delete.append((google_account, real_id))
    elif provider == "onedrive" and ms_account:
        accounts_to_delete.append((ms_account, real_id))

    if not accounts_to_delete:
        raise ValueError(f"Cannot resolve virtual ID: {virtual_id}")

    succeeded = []
    failed = []
    for acct, rid in accounts_to_delete:
        try:
            await _delete_on_provider(acct, rid, db)
            succeeded.append(acct)
        except Exception as e:
            failed.append((acct, str(e)))

    for acct, err_msg in failed:
        _log_repair(db, "delete", virtual_id, acct.provider, False, err_msg)

    # Clean up path mapping for deleted paths
    for path in list(_path_mapping):
        for pstr, rid in _path_mapping[path]:
            if any(rid == r for _, r in accounts_to_delete if r == rid):
                del _path_mapping[path]
                break

    invalidate_cache()

    if not succeeded:
        raise RuntimeError(f"Delete failed on all providers: {failed}")


async def _delete_on_provider(
    account: ConnectedAccount, file_id: str, db: Session
) -> None:
    """Delete a file/folder on a specific provider."""
    import httpx
    from services.google_drive import get_valid_access_token as google_token
    from services.microsoft_graph import get_valid_access_token as ms_token

    if account.provider == ProviderType.GOOGLE_DRIVE:
        token = await google_token(account, db)
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.delete(
                f"https://www.googleapis.com/drive/v3/files/{file_id}",
                headers={"Authorization": f"Bearer {token}"},
            )
            if resp.status_code not in (200, 204):
                raise GoogleDriveError(resp.json().get("error", {}).get("message", "Unknown error"))
    else:
        token = await ms_token(account, db)
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.delete(
                f"https://graph.microsoft.com/v1.0/me/drive/items/{file_id}",
                headers={"Authorization": f"Bearer {token}"},
            )
            if resp.status_code not in (200, 204):
                raise MicrosoftGraphError(resp.json().get("error", {}).get("message", "Unknown error"))


def _log_repair(
    db: Session,
    operation_type: str,
    virtual_id: str,
    provider: ProviderType,
    success: bool,
    error_message: Optional[str] = None,
) -> None:
    """Log a failed propagation attempt for later reconciliation."""
    try:
        entry = RepairLog(
            operation_type=operation_type,
            virtual_id=virtual_id,
            provider=provider,
            success=success,
            error_message=error_message,
        )
        db.add(entry)
        db.commit()
    except Exception:
        pass  # Don't let repair-log failures break the main operation


def get_provider_accounts(db: Session) -> Tuple[Optional[ConnectedAccount], Optional[ConnectedAccount]]:
    """Return (google_account, ms_account) if connected.

    Picks the most recently updated account per provider so that
    a reconnected account takes precedence over a stale duplicate.
    """
    google = db.query(ConnectedAccount).filter(
        ConnectedAccount.provider == ProviderType.GOOGLE_DRIVE
    ).order_by(ConnectedAccount.updated_at.desc()).first()
    ms = db.query(ConnectedAccount).filter(
        ConnectedAccount.provider == ProviderType.ONEDRIVE
    ).order_by(ConnectedAccount.updated_at.desc()).first()
    return google, ms
