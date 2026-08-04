# Notes for Phase 4 
## Each Time We Run OmniDrive
Before we even talk about the architecture / what we are doing with the API's, let's figure out the logic behind the internal file system. We can imagine that both Google Drive and OneDrive's file systems are 2 different trees. We have 2 main goals:

1. To leave the smallest impact on the separate file systems while OmniDrive works.

2. For OmniDrive to still be functional even if the users go ahead and do their own things in their separate drives (Such as creating, deleting, renaming, and moving files). <br>

To achieve Goal #2, my plan is to create a new tree to represent OmniDrive's internal file system each time we actually open OmniDrive. We can create this new tree by merging the existing Google Drive and OneDrive trees. For the most part, this will be a smooth process, except for when there are multiple files / folders with the same name. 
- For **files** with the same name in the same directory of the respective providers (E. g. Copies of the same document in the root directory of Google Drive and OneDrive), we will have to force renaming to happen. 
- For **folders** with the same name, we can merge them into 1 folder, then recursively repeat the process of merging the contents within the 2 folders. <br>

This will also help us achieve goal 1 in the process, but there is a trade-off involved: 
- Pro: Local data storage is not as important, because we can create the internal file systems ourselves every time. We should not store the internal file system locally, especially when it is prone to changing without us knowing (Reference Goal #2). Note that assuming the user only uses OmniDrive (i. e. does not use Google Drive or OneDrive separately), the results will be the same every time. 
- Con: It is a bit inefficient to recreate the tree every single time. However, this is mitigated by the fact that if the user only uses OmniDrive, then it should be a relatively very fast process. 

For the situations where we are forcing the renaming of files, I propose adding "-google" and "-onedrive" at the end of the files.

## Edge Case: File-Folder Name Collision

The merge rules above handle same-name files and same-name folders separately, but then: **what if Google Drive has a file named "Budget" in root and OneDrive has a folder named "Budget" in root?**

Since a file and folder cannot coexist with the same name in a single directory, we need an explicit rule: We will treat file-folder name collisions as file collisions. Force-rename the file (not the folder) by appending the provider suffix. The folder retains its original name.

**Rationale**:
- Folders are more likely to be merge targets (they may contain shared content)
- Renaming a folder breaks the merge key for all its descendants
- Renaming a single file is a localized change
- This preserves the folder structure for potential merges at deeper levels

**Example**:
- Google Drive: `/Budget.xlsx` (file)
- OneDrive: `/Budget/` (folder containing reports)
- OmniDrive view: `/Budget-google.xlsx` and `/Budget/` (folder)

## Edge Case: Double-Collision on Forced Rename

When we force-rename a colliding file (e.g., `Budget.xlsx` → `Budget-google.xlsx`), there arises another risk: **what if a file already named `Budget-google.xlsx` exists in that same directory on Google Drive?**

Since this is deterministic logic running without user prompts, we need a defined fallback:

**Fallback Strategy**: Append a counter suffix until a unique name is found.

**Algorithm**:
1. Try `{original_name}-{provider}.{ext}` (e.g., `Budget-google.xlsx`)
2. If exists, try `{original_name}-{provider}-2.{ext}` (e.g., `Budget-google-2.xlsx`)
3. If exists, try `{original_name}-{provider}-3.{ext}`, incrementing until unique
4. Cap at reasonable limit (e.g., 100 attempts) to prevent infinite loops

**Example**:
- Google Drive: `/Budget.xlsx`, `/Budget-google.xlsx`, `/Budget-google-2.xlsx`
- OneDrive: `/Budget.xlsx`
- OmniDrive view: `/Budget-google-3.xlsx` (from Google), `/Budget-onedrive.xlsx` (from OneDrive) 

**Note**: All collision resolution rules described above (file-file, folder-folder, file-folder, and double-collision counter) apply **recursively at every directory depth**, not just at the root level. The merge process walks both provider trees in parallel, resolving collisions at each level independently.

## API Endpoint Design for Unified View

The OmniDrive unified view requires new backend endpoints separate from the per-provider storage routes. A new router (`routers/omnidrive.py`) will handle these.

### Virtual File IDs

To uniquely identify files across providers in the unified view, each item gets a **virtual ID** that encodes the provider and the real file ID:

```
Format: "{provider}:{real_file_id}"
Example: "google:1aBc234XyZ" or "onedrive:01ABCDEFGHIJKLM"
```

The frontend never needs to decode these — it treats them as opaque strings. The backend parses them to route operations to the correct provider.

### Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/omnidrive/files` | List files in the unified view at a given path |
| `POST` | `/omnidrive/files/upload` | Upload a file to the unified pool |
| `POST` | `/omnidrive/folders` | Create a new folder in the unified pool |
| `PATCH` | `/omnidrive/files/{virtual_id}` | Rename a file or folder |
| `DELETE` | `/omnidrive/files/{virtual_id}` | Delete a file or folder |

### `GET /omnidrive/files`

**Query params**:
- `path` (string, default `"/"`): The virtual path to list (e.g., `"/Documents/Projects"`)
- `page_size` (int, default 100): Number of items per page
- `page_token` (string, optional): Pagination token for the next page

**Response**:
```json
{
  "path": "/",
  "items": [
    {
      "virtual_id": "google:1aBc234XyZ",
      "name": "Report.docx",
      "providers": ["google"],
      "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      "category": "document",
      "size": 245760,
      "size_formatted": "240.0 KB",
      "modified_time": "2026-08-01T12:00:00Z",
      "modified_time_formatted": "3d ago",
      "is_folder": false
    },
    {
      "virtual_id": "merged:Documents",
      "name": "Documents",
      "providers": ["google", "onedrive"],
      "mime_type": "application/vnd.google-apps.folder",
      "category": "folder",
      "is_folder": true,
      "item_count": 15
    }
  ],
  "total_items": 42,
  "next_page_token": "eyJwYWdlIjogMn0="
}
```

**Key fields**:
- `virtual_id`: Opaque identifier encoding provider + real ID. For merged folders, the prefix is `"merged:"` and the name is used as the key.
- `providers`: Array indicating which provider(s) the item lives on. `["google"]` = Google Drive only, `["onedrive"]` = OneDrive only, `["google", "onedrive"]` = merged/exists on both.
- All other fields (`name`, `mime_type`, `category`, `size`, etc.) match the existing `FileItem` schema.

### `POST /omnidrive/files/upload`

Uploads a file to the unified pool. The backend decides which provider to use based on the upload routing rules (see Storage Pooling section).

**Request**: `multipart/form-data` with:
- `file`: The file to upload
- `parent_path` (string, default `"/"`): The virtual path to upload into

**Response**: The created `FileItem` with its `virtual_id`.

### `POST /omnidrive/folders`

Creates a new folder in the unified pool.

**Request body**:
```json
{
  "name": "New Folder",
  "parent_path": "/Documents"
}
```

**Response**: The created folder as a `FileItem`.

### `PATCH /omnidrive/files/{virtual_id}`

Renames a file or folder. For merged folders, propagates to all providers.

**Request body**:
```json
{
  "name": "New Name.xlsx"
}
```

### `DELETE /omnidrive/files/{virtual_id}`

Deletes a file or folder. For merged folders, propagates to all providers.

### In-Memory Tree on the Backend

The merged tree lives as a module-level data structure in the new `routers/omnidrive.py` (or a dedicated `services/omnidrive_tree.py`). It is:

- **Built on backend startup**: When FastAPI starts, the tree is constructed by fetching the full file listing from both providers and merging them.
- **Rebuilt on demand**: A `POST /omnidrive/refresh` endpoint forces a full tree rebuild (needed if the user made external provider changes).
- **Mutated incrementally**: Uploads, renames, and deletes performed through OmniDrive endpoints update the in-memory tree immediately without re-fetching from providers.
- **Not persisted to SQLite**: Since the tree is rebuilt from provider data each time, there is no local cache of the virtual file system. The only persistent state is the upload-alternation counter (see Storage Pooling).

The frontend does NOT need to know about the in-memory tree. It simply calls the REST endpoints and receives JSON. The frontend's React state reflects whatever the API returns — the merge logic is entirely opaque to the client.

## Storage Pooling 

Firstly, we will not be chunking files. Here is the plan for handling new uploads across all scenarios.

### Upload Routing Rules

| Scenario | Rule |
|---|---|
| **Root-level** upload (file or folder created in `"/"`) | Alternate between Google Drive and OneDrive using a persistent counter |
| **Non-merged folder** (folder exists on only one provider) | Upload to the same provider that owns the folder |
| **Merged folder** (folder exists on both providers) | Alternate between Google Drive and OneDrive using the **same** persistent counter as root-level uploads |

The alternation counter is stored as a single-row table in SQLite (`upload_routing` table with a `next_provider` column). On each successful upload to root or a merged folder, the counter flips to the other provider.

**Rationale for using one shared counter**: Whether the user is uploading to root or into a merged folder, the goal is the same — evenly distribute new content across both providers. A single global counter keeps the distribution balanced overall, is simpler to implement, and avoids per-folder counter management overhead.

### Provider Unavailability Fallback

If the provider chosen by the alternation counter is unavailable (disconnected account, out of storage space, API error), the upload **falls back to the other provider**. The counter still flips as if the first provider was used — this prevents repeatedly trying the failed provider on every subsequent upload. On the next upload attempt (after the counter has flipped), the previously-failed provider will be tried again naturally.

**Example**:
1. Counter says → Google. Google is full. Fallback → OneDrive (succeeds). Counter flips to OneDrive.
2. Counter says → OneDrive. OneDrive succeeds. Counter flips to Google.
3. Counter says → Google. Google still full. Fallback → OneDrive (succeeds). Counter flips to OneDrive.

This means the working provider gets more uploads while the other is down, which is the desired behavior.

If **both** providers are unavailable, the upload fails with a clear error.

### Subfolder Uploads in Non-Merged Folders

For new uploads inside a folder that exists on only one provider, we keep them in that provider's folder. For example, if I have a folder only in Google Drive and I create a subfolder via OmniDrive, that subfolder will NOT be provisioned in OneDrive.

While this creates some storage imbalance, consider Goal #2: this ensures you can always download a complete folder from a single provider without OmniDrive. If OmniDrive split a folder's contents across providers, downloading from Google Drive directly would give you an incomplete folder.

### Note on the Alternation Approach

The round-robin alternation is intentionally simple. It prioritizes ease of testing and predictable behavior over optimal space utilization. For a personal tool managing two free-tier cloud accounts, the simplicity is worth the trade-off. If more providers are added in the future, this can be upgraded to a weighted selection based on available space.

## Pagination and Sorting in the Unified View

In the per-provider views (Phase 2 & 3), sorting and pagination are delegated to the provider APIs (e.g., `orderBy=modifiedTime desc`, `pageToken`). In the unified OmniDrive view, this is no longer possible because files from two providers must be interleaved.

### Approach

1. **Fetch all files** from both providers for the requested directory (no provider-side pagination).
2. **Merge and sort** the combined list in-memory on the backend using Python's `sorted()`.
3. **Paginate** the merged result before returning it to the frontend.

### Sorting

Sorting is done server-side on the merged list. The supported sort orders mirror the existing options:

| Sort Key | Behavior |
|---|---|
| `modified_time` (default) | Most recently modified first |
| `name` | Alphabetical by name (case-insensitive) |
| `size` | Largest first (folders sorted by name within the folder group) |

Folders are always listed before files regardless of sort order, matching typical file manager behavior.

### Pagination

The merged result uses **offset-based pagination** via `page_size` and `page_token`:

- `page_token` is an opaque base64-encoded cursor representing the offset into the merged list.
- The `next_page_token` in the response indicates there are more results.
- Absence of `next_page_token` means the end of the list has been reached.

**Performance note**: For very large directories (hundreds of files), fetching everything from both providers on every navigation could be slow. As a mitigation, the backend can cache provider responses for a short TTL (e.g., 30 seconds) keyed by `(account_id, parent_id)`. Since this is a single-user desktop app, the cache hit rate will be high during active browsing.

**Frontend impact**: The `ConnectedHomePage` component's existing `sortOptions` and pagination UI work the same way — only the API endpoint changes from `/storage/{id}/files` to `/omnidrive/files`. Filtering by category (images, documents, etc.) is done client-side on the already-fetched and merged page, since the backend returns all categories together.

## Edge Case: Delete/Rename Propagation on Merged Folders

The merge logic described above handles the **read side** (how we construct the unified view), but not the **write side** (how user actions propagate back to providers). This is critical for merged folders.

**Scenario**: Google Drive has `/Documents/` and OneDrive has `/Documents/`. These merge into a single logical folder in OmniDrive. What happens when the user:

1. **Renames** the logical `/Documents/` folder to `/Docs/` in OmniDrive?
2. **Deletes** the logical `/Documents/` folder in OmniDrive?

**Decision**: Write operations on merged folders should **propagate to all underlying provider folders**.

**Rationale**:
- A merged folder represents a single logical entity spanning multiple providers
- If we only rename/delete on one provider, the merge breaks on next launch (name-matching key fails)
- User expects unified behavior — they see one folder, they act on one folder
- This is a one-to-many write, but it's the only way to maintain consistency without breaking everything

**Implementation**:
- **Rename**: When user renames a merged folder, issue rename API calls to all providers that have that folder. Use a best-effort approach (see atomicity discussion below).
- **Delete**: When user deletes a merged folder, issue delete API calls to all providers that have that folder.
- **Metadata updates**: Same propagation logic applies to any folder metadata changes.

### Pragmatic Approach to Atomicity

True atomicity across two independent cloud APIs is impossible without a distributed transaction coordinator. For a single-user desktop tool, we accept **eventual consistency** with a best-effort rollback:

1. **Attempt propagation**: Execute the operation (rename/delete) on all providers sequentially.
2. **Partial success**: If some succeed and some fail:
   - **Rename**: Attempt to undo the successful renames (rename back to original name). If the undo also fails, log the inconsistency to a **repair log** in SQLite and notify the user which provider(s) are out of sync.
   - **Delete**: Deletes that succeeded stay deleted. Log which providers still have the folder, and notify the user. This is safer than trying to "undelete," which is often impossible.
3. **Full failure**: If all providers fail, return an error — the in-memory tree is not mutated.
4. **On next tree rebuild**: The merge process will naturally reconcile inconsistencies. A renamed folder on one provider will appear as a separate, unmerged folder. The repair log helps the user know what happened.

**Error Handling**:
- Show a clear error message indicating which provider(s) failed and what state each provider is in
- The repair log table (`repair_log`) stores: timestamp, operation type, virtual_id, provider, success/failure, error message
- A future Phase 5 UI could surface the repair log to the user

**Trade-off acknowledged**: This means users cannot have different folder names across providers for the same logical folder. This is intentional — the unified view requires unified naming.

## Edge Case: Mid-Session Drift

The tree is rebuilt at launch by fetching fresh data from both providers. However, users may upload/create/delete/rename files during an active OmniDrive session through the OmniDrive interface itself. Additionally, users might make changes in a browser tab to Google Drive or OneDrive while OmniDrive is open.

**Decision**: Accept that **only a full app restart reflects provider-side changes made outside OmniDrive**. For changes made through OmniDrive itself, we will **mutate the in-memory tree incrementally**.

**Rationale**:
- Incremental in-memory updates for OmniDrive-initiated actions are cheap and provide immediate feedback
- Polling providers for external changes would be complex (rate limits, conflict resolution, performance)
- Rebuilding the tree on app restart is simple and guarantees consistency
- This is a reasonable trade-off for a single-user desktop app

**Implementation**:
- **OmniDrive-initiated changes**: When user uploads/creates/deletes/renames through OmniDrive, immediately update the in-memory tree to reflect the change. Do NOT re-fetch from providers.
- **External provider changes**: If user makes changes in browser tab to Google Drive/OneDrive, those changes will NOT appear in OmniDrive until app restart. Show a subtle indicator (optional Phase 5) that a refresh is available.
- **Conflict detection**: If OmniDrive tries to perform an operation that fails because the provider state changed externally (e.g., delete a file that was already deleted in browser), handle the API error gracefully and refresh the tree.

**Alternative considered**: Implement periodic polling or webhooks. Rejected because:
- Adds significant complexity (webhook registration, endpoint exposure, rate limit management)
- Overkill for single-user desktop app
- User can simply restart app to sync  
- OmniDrive is not meant to be used this way anyways! Users should not be doing this, but we are just trying to prevent the app from crashing if it *does* happen. 

## Edge Case: Off-Session Provider Changes (Broken Merge Keys)

The mid-session drift section covers changes made while OmniDrive is running. A separate concern is changes made **between sessions** — the user closes OmniDrive, renames or moves folders directly on Google Drive or OneDrive, then reopens OmniDrive.

**Problem**: The merge logic relies on matching folder names across providers. If a folder that was previously merged gets renamed on one provider externally, the name-match fails on the next tree rebuild and the previously-merged folder silently splits into two separate folders with no warning.

**Example**:
- Session 1: Google Drive has `/Documents/` and OneDrive has `/Documents/` → merged as one logical folder.
- User closes OmniDrive, renames `/Documents/` to `/Docs/` on Google Drive directly.
- Session 2: Google Drive has `/Docs/` and OneDrive has `/Documents/` → no name match, two separate folders appear.

**Decision**: Accept this as expected behavior. The tree rebuild is a fresh snapshot of provider state. If the user changes provider data externally, the merge output changes accordingly. We will **not** persist merge history across sessions.

**Rationale**:
- Persisting merge relationships would require storing a mapping of which folders were previously merged — exactly the kind of local state we deliberately avoid (see trade-offs in the tree rebuild section).
- The user explicitly chose to bypass OmniDrive, so they should expect the unified view to reflect their changes.
- The worst case is two separate folders instead of one merged folder — no data loss, no corruption.

**Mitigation**: The origin indicator dots (green/blue) make it visually obvious which folders came from which provider, so a previously-merged folder splitting apart is immediately noticeable.

## Defining the User Experience 
Before the implementation plan, let's figure out what the final state of OmniDrive *should* be so we have a clear idea of the functionalities that we want. 

Right now, when the user opens OmniDrive, they can click a button that opens up a drop-down with 2 options, where you can navigate Google Drive and OneDrive effectively by choosing which provider. I intend to keep this, BUT:
- We are going to add a new option, where we call it OmniDrive. 
- The user can click on this option to experience the purpose of the app: A unified storage pool that "merges" the 2 other providers together. 
- This will become the new default option. 
- When we use this option, just for clarity, we can include a small green or blue dot next to each file name to indicate whether the file is stored in Google Drive or OneDrive. For merged folders, we can have a "split" indicator with green on 1 side and blue on the other. 

### Origin Indicator Propagation

The `providers` field returned by the API determines the indicator for every item at every depth:

| `providers` value | Indicator |
|---|---|
| `["google"]` | Green dot |
| `["onedrive"]` | Blue dot |
| `["google", "onedrive"]` | Split indicator (half green, half blue) |

This propagates naturally through recursive merging. If `/Projects/` is a merged folder, then any child within it that also exists on both providers will show the split indicator. Children that exist on only one provider will show that provider's single dot. No special-casing is needed — the merge algorithm sets `providers` correctly for every item in the tree.

### Sorting and Filtering in OmniDrive Mode

Sorting (by name, date, size) and category filtering work the same as the existing per-provider views, with one difference: they are performed on the **already-merged result** rather than delegated to a provider API. From the user's perspective, the dropdowns and buttons behave identically to the Google Drive and OneDrive views.

### Provider Selector Dropdown

The existing dropdown that lets users switch between Google Drive and OneDrive will gain a third option: **"OmniDrive"**. This is a synthetic option — it does not correspond to a `ConnectedAccount` row in the database. The frontend detects this special value and calls the `/omnidrive/*` endpoints instead of `/storage/{account_id}/*`.

The OmniDrive option will be the **default** selection when the user arrives at the home page and has at least one provider connected.