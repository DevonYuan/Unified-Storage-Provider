# OmniDrive: Unified Cloud Storage Pool

This is a personal tool that I made for myself, to manage my two cloud storage accounts (specifically Google Drive and Microsoft OneDrive) into a single seamless, and unified virtual storage pool.

Instead of jumping between different interfaces and managing fragmented storage limits, OmniDrive acts as a router and abstraction layer. It presents a single interface where your total available storage is the sum of your connected providers, automatically handling distribution and retrieval across APIs without costing a dime in infrastructure fees.

OmniDrive is a fully local, single-user desktop app. There is no login, no account system, and no remote database — everything runs and lives on the user's own machine.

## Tech Stack

**Backend**:
- Backend framework: FastAPI
- Managing Google Drive: Google Drive API
- Managing Microsoft: Microsoft Graph Files API
- Local metadata storage: SQLite (via SQLAlchemy), with Alembic for schema migrations
- Secret storage: `keyring` (delegates to the OS credential store — Keychain on macOS, Credential Manager on Windows, Secret Service/libsecret on Linux)
- App data directory resolution: `platformdirs`

**Frontend**: React with Vite

**Packaging**: Once the backend and frontend run locally, we will package the app as a desktop app using Electron. FastAPI will run as a bundled subprocess managed by Electron's main process, which will also resolve the OS-appropriate app data directory and hand it off to the backend on launch.

## Local Data Storage

Since OmniDrive doesn't authenticate users or talk to a remote database, "local storage" covers two distinct concerns, handled differently:

- **OAuth tokens (Google Drive / Microsoft Graph)** are stored via `keyring`, not in a plain file or database column. This delegates to the OS's real credential store rather than inventing our own encryption.
- **Everything else** — connected account info, the virtual filesystem, and (starting in Phase 4) the chunk-to-provider mapping — lives in a local SQLite database. SQLite gives us transactional guarantees, which matter once files start getting split and distributed across two providers: we need to know exactly what state a chunked upload was in if the app crashes or loses connectivity mid-operation.

The SQLite file lives in the OS-standard app data directory (resolved via `platformdirs`), not a path relative to the source code, so it survives updates and behaves correctly across macOS/Windows/Linux.

Expected core tables (growing across phases):
- `connected_accounts` — provider, linked account display name, keyring reference key, token expiry
- `virtual_files` — virtual path, size, timestamps, status
- `file_chunks` — links a virtual file to its physical chunks across providers, with per-chunk upload status (Phase 4)
- `settings` — app-level key/value config (default provider, chunk size threshold, etc.)

## Phases

We will elaborate more on this in separate documents.

### Phase 1 - Skeleton
Build a working skeleton of a web app. Users store their required data locally — no authentication, no accounts, no data collection. This phase includes standing up the local SQLite schema and the keyring-based secret storage that later phases will build on.

### Phase 2 - Google Drive Integration
Add support for Google Drive. The end goal is that you can effectively navigate the app, as if you were using Google Drive directly. Under the hood, we will be working with the Google Drive API.

### Phase 3 - Microsoft OneDrive Integration
Add support for Microsoft OneDrive. The end goal is that you can effectively navigate the app, as if you were using OneDrive directly. Under the hood, we will be working with the Microsoft Graph Files API. Note that at the end of the phase the user should be able to choose which provider they are using.

### Phase 4 - Unified Storage Pool
Implement the core functionality that merges the storage from both providers into a single virtual filesystem. This includes handling file chunking, automatic distribution across providers based on available space, and seamless retrieval regardless of where the file is physically stored. The user should experience this as a single, unified drive with combined storage capacity.

### Phase 5 - Polishing (Optional)
Explore different UI styles and experiment with different AI tools to only enhance the UI, but do NOT break the functionality of the app?

## Footnote
I originally intended for this app to support several users, but it must undergo Google's verification process to allow users without having to explicitly add them to a list in the GCP console. I fully intend on preparing demo videos and submitting them for review in the future, but until then, you will have to contact me, so that I can add you to a list of test users.
