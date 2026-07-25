# Phase 2 - Google Drive Integration
In this phase, we will add support for Google Drive. We will implement the OAuth flow and file operations using the Google Drive API so that users can effectively navigate the app as if they were using Google Drive directly. 

## To-Do List 
### 1. Decide upon table definitions.
- Choose definitions for tables related to Google Drive OAuth tokens and file metadata. 
- We are not concerned with Microsoft OneDrive integration at this time
- We will be using Google OAuth 2.0 and the Google Drive API. I will manually add the environment variables.

### 2. Write tests for the backend and frontend
- The tests apply strictly to the functionality of the Google Drive integration. 

**Acceptance Criteria:** 
- Write unit tests for Google OAuth token storage and retrieval
- Write unit tests for Google Drive file listing endpoint
- Write unit tests for file upload and download endpoints
- Write unit tests for folder navigation endpoints
- Write unit tests for file deletion endpoints
- Write unit tests for file renaming endpoints 
- Write frontend tests for Google Drive file browser components
- Write tests for OAuth callback handling
- Ensure all tests clean up test data from database
- Mock Google Drive API responses in tests

### 3. Implement the backend and frontend
- This one is self-explanatory. Tests MUST be written BEFORE this happens. 
- The tests added in phase 2 must NOT be edited without good reason 

**Acceptance Criteria:** 
- Implement Google OAuth 2.0 flow with automatic token refresh
- Implement file listing endpoint that maps Google Drive files to internal schema
- Implement file upload endpoint to Google Drive
- Implement file download endpoint from Google Drive
- Implement folder creation and navigation, deletion, and renaming 
- Create frontend Google Drive file browser UI
- Implement "Connect Google Drive" button and OAuth flow (Given the scope, this should be a one-time thing)
- The REDIRECT_URI used for calling OAuth is included in the environment variables 

### 4. Manual testing 
- This one is also self-explanatory. 

**Acceptance Criteria:** 
- Test OAuth connection flow end-to-end
- Test file listing and navigation
- Test file upload and download
- Test folder creation
- Test token refresh behavior

The end goal of this, is that there is functionally no difference between using our app, and using Google Drive. <br>
The work that a user does within this app should reflect in their actual Google Drive account.