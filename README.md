# OmniDrive: Unified Cloud Storage Pool

This desktop app is a personal tool, to manage my two cloud storage accounts (specifically Google Drive and Microsoft OneDrive) into a single seamless, unified storage pool.

Instead of jumping between different interfaces and managing fragmented storage limits, OmniDrive acts as a router and abstraction layer. It presents a single interface where your total available storage is the sum of your connected providers, automatically handling distribution and retrieval across the two platforms.

Since OmniDrive is a fully local, single-user desktop app, there is no login, no account system, and no remote database — everything runs and lives on the user's own machine.

## Using the App
If you would like to use the app, you will need to contact me. I need to add you to a list of test users in GCP before you can use OmniDrive. If you attempt to user the app beforehand, you will be unable to access the Google Drive component, hence unable to experience the convenience layer that the app offers. 

## Tech Stack

**Backend**:
- Backend framework: FastAPI
- Managing Google Drive: Google Drive API
- Managing Microsoft: Microsoft Graph Files API
- Local metadata storage: SQLite (via SQLAlchemy), with Alembic for schema migrations
- App data directory resolution: `platformdirs`
- Secret storage: `keyring` (delegates to the OS credential store — Keychain on macOS, Credential Manager on Windows, Secret Service/libsecret on Linux)

**Frontend**: React with Vite

**Packaging**: Once the backend and frontend run locally, we will package the app as a desktop app using Electron. FastAPI will run as a bundled subprocess managed by Electron's main process, which will also resolve the OS-appropriate app data directory and hand it off to the backend on launch.

## Local Data Storage

Since OmniDrive doesn't authenticate users or talk to a remote database, "local storage" covers two distinct concerns, handled differently:

- **OAuth tokens (Google Drive / Microsoft Graph)** are stored via `keyring`, not in a plain file or database column. This delegates to the OS's real credential store rather than inventing our own encryption.
- **Everything else** — connected account info, and (in phase 4) information regarding routing logic, lives in a SQLite database. SQLite gives us transactional guarantees, which matter once folders are split across providers. We will split folders, but we definitely not chunk files. 

The SQLite file lives in the OS-standard app data directory (resolved via `platformdirs`), not a path relative to the source code, so it survives updates and behaves correctly across macOS/Windows/Linux.

## Phases
We will elaborate more on this in separate documents.

### Phase 1 - Skeleton
Build a working skeleton of a web app. Logging in and out are the only features. 

### Phase 2 - Google Drive Integration
Users store their required data locally — no authentication, no accounts, no data collection. This phase includes standing up the local SQLite schema and the keyring-based secret storage that later phases will build on. We will also add support for Google Drive. The end goal is that you can effectively navigate the app, as if you were using Google Drive directly. Under the hood, we will be working with the Google Drive API. 

### Phase 3 - Microsoft OneDrive Integration
Add support for Microsoft OneDrive. The end goal is that you can effectively navigate the app, as if you were using OneDrive directly. Under the hood, we will be working with the Microsoft Graph Files API. Note that at the end of the phase the user should be able to choose which provider they are using.

### Phase 4 - Unified Storage Pool
Implement the core functionality that merges the storage from both providers into a single virtual file system. This includes handling automatic distribution across providers based on available space, and seamless retrieval regardless of where the file is physically stored. The user should experience this as a single, unified drive with combined storage capacity. The logic behind the internal file system is explained more in-depth in Phase 4's dedicated document, `docs/phase4.md`

### Phase 5 - Polishing the User Experience 
Experimenting with different aesthetics, debugging, and updating the documents to reflect changes to the plans throughout the implementation. 

## Phase 6 - Packaging as a Desktop App
Bundle the backend into a standalone executable with PyInstaller (so users don't need Python installed) and wrap the frontend in Electron. Electron spawns the backend as a subprocess on startup, and the React frontend communicates with it over localhost — no remote servers, no cloud dependencies. The OAuth flow required special handling since Chromium blocks redirects between `http://` and `file://` origins, solved by using Electron's IPC bridge to let the main process handle navigation directly. The app ships as an NSIS installer for Windows, with the Electron configuration structured so that adding macOS and Linux targets is straightforward later.

### Contact Info 
Email: devon.yuan@outlook.com <br>
Phone: 236-458-2221 <br>
LinkedIn: [Click Here](https://www.linkedin.com/in/devon-yuan-361575340/) <br>
Discord: devon7021o_o