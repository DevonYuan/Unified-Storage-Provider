# Phase 3 Implementation Plan: Microsoft OneDrive Integration

## Goal
Add Microsoft OneDrive support so users can connect their Microsoft account and navigate OneDrive files through the OmniDrive interface. At the end of this phase, the user can choose which provider to browse.

---

## Prerequisites: Azure AD App Registration

Before any code, register an app in the Azure Portal:

1. Go to **Azure Portal** → **Microsoft Entra ID** (formerly Azure AD) → **App registrations** → **New registration**
2. **Name**: `OmniDrive` (or similar)
3. **Supported account types**: "Accounts in any organizational directory and personal Microsoft accounts"
4. **Redirect URI**: Web → `http://localhost:8000/auth/microsoft/callback`
5. After creation, go to **Certificates & secrets** → **New client secret** — save the value immediately
6. Note the **Application (client) ID** from the Overview page

---

## Environment Variables

Add these to your `.env` file:

```env
# Microsoft Graph / Azure AD OAuth
MICROSOFT_CLIENT_ID=your-client-id-here
MICROSOFT_CLIENT_SECRET=your-client-secret-here
MICROSOFT_REDIRECT_URI=http://localhost:8000/auth/microsoft/callback
# Optional overrides (defaults below are standard):
# MICROSOFT_AUTH_URI=https://login.microsoftonline.com/common/oauth2/v2.0/authorize
# MICROSOFT_TOKEN_URI=https://login.microsoftonline.com/common/oauth2/v2.0/token
```

### Env Var Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `MICROSOFT_CLIENT_ID` | ✅ Yes | — | Azure AD App client ID |
| `MICROSOFT_CLIENT_SECRET` | ✅ Yes | — | Azure AD App client secret |
| `MICROSOFT_REDIRECT_URI` | ✅ Yes | — | Must match Azure Portal exactly |
| `MICROSOFT_AUTH_URI` | No | `https://login.microsoftonline.com/common/oauth2/v2.0/authorize` | OAuth authorization endpoint |
| `MICROSOFT_TOKEN_URI` | No | `https://oauth2.googleapis.com/token` | OAuth token endpoint |

### Required OAuth Scopes (hardcoded, not env vars)

```
offline_access          → ensures a refresh token is returned
Files.Read              → read all OneDrive files
Files.ReadWrite         → read/write all OneDrive files (needed for Phase 4 uploads)
User.Read               → get user's display name and email
```

---

## Backend Changes

### 1. `config.py` — Add `MicrosoftOAuthConfig`

Mirror the `GoogleOAuthConfig` pattern:

```python
class MicrosoftOAuthConfig(BaseModel):
    client_id: str
    client_secret: str
    redirect_uri: str
    auth_uri: str = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
    token_uri: str = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    scopes: List[str] = ["offline_access", "Files.Read", "Files.ReadWrite", "User.Read"]

    @classmethod
    def from_env(cls) -> "MicrosoftOAuthConfig": ...
    def validate(self) -> List[str]: ...
```

Add `microsoft_oauth: MicrosoftOAuthConfig` to `AppConfig` and update `get_config()`.

### 2. `services/microsoft_oauth.py` — New file

Mirror `services/google_oauth.py`. Functions needed:

| Function | Purpose |
|---|---|
| `build_authorization_url(redirect_uri)` | Build Azure AD OAuth URL with state |
| `validate_state(state)` | Validate and return stored redirect URI |
| `exchange_code_for_tokens(code, redirect_uri)` | POST to token endpoint for access + refresh tokens |
| `get_user_info(access_token)` | GET `https://graph.microsoft.com/v1.0/me` for display name & email |
| `refresh_access_token(refresh_token)` | Refresh an expired access token |
| `store_refresh_token(keyring_key, token)` | Store in OS keyring |
| `get_refresh_token(keyring_key)` | Retrieve from OS keyring |
| `get_keyring_key(user_id)` | Generate keyring key: `"onedrive:{user_id}"` |

Key differences from Google:
- Token exchange uses same field names (`code`, `client_id`, `client_secret`, `grant_type`, `redirect_uri`)
- `scope` in auth URL is space-separated like Google
- Microsoft returns `id_token` (JWT) in token response — we don't need it
- Refresh token response may NOT include a new refresh token (Microsoft refresh tokens are long-lived unless revoked)

Use a **separate** in-memory state cache from Google's (or prefix the state keys with `"ms:"`) to avoid collisions.

### 3. `services/microsoft_graph.py` — New file

Mirror `services/google_drive.py` but for Microsoft Graph API.

| Function | Purpose |
|---|---|
| `get_valid_access_token(account, db)` | Return current token (or refresh if needed) |
| `list_drive_files(account, db, parent_id, page_size)` | List files in a OneDrive folder |
| `get_file_metadata(account, db, file_id)` | Get single file/folder metadata |
| `upload_drive_file(account, db, file, parent_id)` | Upload a file to OneDrive |

**Key API differences from Google Drive:**

| Concern | Google Drive | Microsoft Graph |
|---|---|---|
| Base URL | `https://www.googleapis.com/drive/v3/` | `https://graph.microsoft.com/v1.0/` |
| List files | `GET /files?q='{parent}' in parents` | `GET /me/drive/items/{parent}/children` |
| Root folder | `'root'` literal | `'root'` literal |
| Auth header | `Authorization: Bearer {token}` | `Authorization: Bearer {token}` |
| Pagination | `pageToken` query param | `@odata.nextLink` in response, or `$top` / `$skip` |
| Order by | `orderBy=modifiedTime desc` | `$orderby=lastModifiedDateTime desc` |
| Thumbnail | `thumbnailLink` field | `thumbnails[0].medium.url` (or `/thumbnails` endpoint) |
| Web link | `webViewLink` field | `webUrl` field |
| MIME type | `mimeType` field | `file.mimeType` for files; folders have `folder` object |
| Is folder | `mimeType == 'application/vnd.google-apps.folder'` | Check if `folder` property exists on the item |
| Size | `size` (string of bytes) | `size` (integer, bytes) |
| Modified | `modifiedTime` (RFC 3339) | `lastModifiedDateTime` (ISO 8601) |
| File ID | `id` | `id` |
| Name | `name` | `name` |

**Important**: The `FileItem` Pydantic model in `storage.py` is provider-agnostic. We need a **translation layer** that maps Microsoft's response shape into the same `FileItem` fields. This can be a helper like `_ms_item_to_fileitem(ms_item)` in the router or service.

### 4. `routers/auth.py` — Add Microsoft OAuth flow

Modify `start_oauth` (POST `/auth/oauth/start`):
- Currently rejects anything except `GOOGLE_DRIVE` with 501
- Add branch for `ProviderType.ONEDRIVE` → calls `microsoft_oauth.build_authorization_url()`

Add new endpoint `GET /auth/microsoft/callback`:
- Same pattern as `GET /auth/google/callback`
- Exchanges code for tokens via `microsoft_oauth.exchange_code_for_tokens()`
- Gets user info via `microsoft_oauth.get_user_info()`
- Stores account with `provider=ProviderType.ONEDRIVE`, `keyring_key="onedrive:{user_id}"`
- Redirects to `http://localhost:5173/signup`

**No changes needed** to `list_accounts`, `get_account`, or `delete_account` — they already work with any `ProviderType`.

### 5. `routers/storage.py` — Add OneDrive file operations

Modify `list_files` (GET `/storage/{account_id}/files`):
- Currently rejects non-Google accounts with 400
- Add branch for `ProviderType.ONEDRIVE` → calls `microsoft_graph.list_drive_files()`

Modify `upload_file` (POST `/storage/{account_id}/files/upload`):
- Same pattern — add OneDrive branch

The existing `FileItem` / `FileListResponse` models and helper functions (`get_mime_type_category`, `format_file_size`, `format_modified_time`) are already provider-agnostic and should work unchanged.

### 6. `database_driver.py` — No changes needed
The `ConnectedAccount` model and SQLite schema already support `ProviderType.ONEDRIVE`.

---

## Frontend Changes

### 1. `SignUpPage.jsx` — Replace simulated OneDrive connection

`handleOneDriveConnect` currently uses `setTimeout` to simulate. Replace with real OAuth flow:

```javascript
const handleOneDriveConnect = async () => {
    setConnecting('microsoft')
    try {
        const redirectUri = 'http://localhost:8000/auth/microsoft/callback'
        const { auth_url, state } = await authApi.startMicrosoftOAuth(redirectUri)
        sessionStorage.setItem('oauth_state_ms', state)
        window.location.href = auth_url
    } catch (err) {
        setConnecting(null)
        alert(`Failed to start OneDrive connection: ${err.message}`)
    }
}
```

### 2. `client.js` — Add Microsoft endpoints

```javascript
export const authApi = {
    // ... existing ...
    async startMicrosoftOAuth(redirectUri) {
        return request('/auth/oauth/start', {
            method: 'POST',
            body: { provider: 'onedrive', redirect_uri: redirectUri },
        });
    },
}
```

The existing `listAccounts()`, `storageApi.listFiles()`, `storageApi.uploadFile()` all work as-is because the backend handles provider routing.

### 3. `ConnectedHomePage.jsx` — Handle multiple providers

Currently `fetchFiles` hardcodes finding the first Google Drive account. Update to:
- Allow selecting which provider/account to view (dropdown in toolbar)
- Or auto-select the only connected provider

Simplest approach for Phase 3: let the user pick a provider. Add a provider selector in the toolbar. The selected account ID drives which files are fetched.

### 4. `FileCard.jsx` — Origin dot color per provider

Update the origin dot to show:
- **Green** (`#4caf50`) for Google Drive
- **Blue** (`#0078d4`) for OneDrive

Pass `provider` as a prop and conditionally apply the class:
```css
.file-card__origin--google { background-color: #4caf50; }
.file-card__origin--onedrive { background-color: #0078d4; }
```

---

## File-by-File Summary

| File | Action | Effort |
|---|---|---|
| `.env` | Add 3 new env vars | Trivial |
| `backend/config.py` | Add `MicrosoftOAuthConfig`, wire into `AppConfig` | Small |
| `backend/services/microsoft_oauth.py` | **New file** — OAuth flow for Azure AD | Medium |
| `backend/services/microsoft_graph.py` | **New file** — Graph API for OneDrive | Large |
| `backend/routers/auth.py` | Add Microsoft branch to `/oauth/start`, add `/microsoft/callback` | Medium |
| `backend/routers/storage.py` | Add OneDrive branches to `list_files` + `upload_file` | Small |
| `frontend/src/api/client.js` | Add `startMicrosoftOAuth()` | Trivial |
| `frontend/src/components/SignUpPage.jsx` | Replace simulated OneDrive with real OAuth | Small |
| `frontend/src/components/ConnectedHomePage.jsx` | Provider selector dropdown | Medium |
| `frontend/src/components/FileCard.jsx` | Pass `provider`, color origin dot accordingly | Small |
| `frontend/src/styles/FileCard.css` | Add `.file-card__origin--onedrive` | Trivial |

---

## Verification Steps

1. Register Azure AD app, set env vars, start backend
2. Go to `/signup` → click "Connect" on OneDrive → should redirect to Microsoft login
3. After consent, should redirect back and show "Connected"
4. Go to `/home` → select OneDrive from provider dropdown
5. Should see OneDrive files/folders with blue origin dots
6. Click into folders — navigation should work
7. Upload a file — should appear in OneDrive
8. Switch between Google Drive and OneDrive — files should reload correctly

---

## Risks & Notes

- **Microsoft refresh tokens** are long-lived (90 days default for personal accounts) but can be revoked by password changes, MFA changes, or explicit revocation. Same reconnect pattern as Google applies.
- **Microsoft consent prompt**: Unlike Google's `prompt=consent`, Microsoft uses `prompt=select_account` or omitting the parameter. The `offline_access` scope ensures a refresh token is returned on first consent.
- **OneDrive personal vs business**: Using `/common` in the auth endpoint allows both. File listing uses `/me/drive/...` which works for both.
- **Thumbnail handling**: Microsoft Graph returns thumbnails as an array; need to pick the first available size. This can be deferred to Phase 5.
