# OAuth 2.0 Integration Issue Analysis

## How OAuth Works in This Codebase

### OAuth Flow Overview
1. **Authorization Request**: User clicks "Connect Google Drive" button
2. **Frontend Request**: Frontend calls `/api/v1/google/oauth/url` to get Google's authorization URL
3. **Google Redirect**: User is redirected to Google's OAuth consent screen
4. **User Consent**: User grants permission to the application
5. **Callback**: Google redirects back to `/api/v1/google/oauth/callback?code=AUTH_CODE&state=STATE`
6. **Token Exchange**: Backend exchanges the authorization code for access/refresh tokens
7. **Token Storage**: Tokens are securely stored in the database
8. **API Access**: Backend uses tokens to make Google Drive API calls on behalf of the user

### Code Implementation Points

**Backend (`google_drive.py`)**:
- `/google/oauth/url`: Generates authorization URL using Google's OAuth flow
- `/google/oauth/callback`: Handles the callback, exchanges code for tokens, stores them

**Service (`google_drive_service.py`)**:
- `get_oauth_url()`: Creates OAuth flow and generates authorization URL
- `exchange_code_for_tokens()`: Exchanges authorization code for tokens
- `get_credentials()`: Retrieves and refreshes tokens as needed
- `_get_drive_service()`: Creates authenticated Google Drive service instance

**Frontend (`googleDrive.service.ts`)**:
- `getGoogleOAuthUrl()`: Calls backend to get authorization URL
- `handleGoogleCallback()`: Handles the OAuth callback (though in this implementation, the callback is handled entirely by the backend via redirect)

## Possible Causes of "invalid_client" Error (401)

Based on the error message "Access blocked: Authorization Error. The OAuth client was not found. Error 401: invalid_client", here are the most likely causes:

### 1. **Missing or Incorrect OAuth Credentials in .env**
   - **Issue**: `GOOGLE_CLIENT_ID` or `GOOGLE_CLIENT_SECRET` not set correctly in `.env` file
   - **Verification**: Check that `.env` contains:
     ```
     GOOGLE_CLIENT_ID=your_actual_client_id_here
     GOOGLE_CLIENT_SECRET=your_actual_client_secret_here
     GOOGLE_REDIRECT_URI=http://localhost:3000/api/v1/google/oauth/callback
     ```
   - **Note**: The redirect URI must match exactly what's configured in Google Cloud Console

### 2. **OAuth Client Not Properly Configured in Google Cloud Console**
   - **Issue**: The OAuth client ID/secret don't correspond to a valid, configured OAuth client
   - **Required Steps in Google Cloud Console**:
     1. Create a project (or select existing)
     2. Enable "Google Drive API" and "Google OAuth" APIs
     3. Go to "APIs & Services" > "Credentials"
     4. Create OAuth 2.0 Client ID (Application type: Web application)
     5. Set authorized redirect URIs to include: `http://localhost:3000/api/v1/google/oauth/callback`
     6. Copy the Client ID and Client Secret to your `.env` file

### 3. **OAuth Consent Screen Not Configured**
   - **Issue**: Google requires OAuth consent screen configuration for external users
   - **Required Steps**:
     1. In Google Cloud Console: "APIs & Services" > "OAuth consent screen"
     2. Select "External" user type (since this is not a Google Workspace internal app)
     3. Fill in required fields: App name, user support email, developer contact email
     4. Add required scopes: `https://www.googleapis.com/auth/drive.file` and `https://www.googleapis.com/auth/drive.readonly`
     5. **IMPORTANT**: Click "Save and Continue" through all steps, then publish the app (even for testing)
     6. For testing, add test users under "Test users" section

### 4. **Redirect URI Mismatch**
   - **Issue**: The redirect URI in the code doesn't match what's registered in Google Cloud Console
   - **Check**: 
     - In `.env`: `GOOGLE_REDIRECT_URI=http://localhost:3000/api/v1/google/oauth/callback`
     - In Google Cloud Console: Under OAuth 2.0 Client ID settings, "Authorized redirect URIs"
     - Must match exactly (including trailing slashes if present)

### 5. **API Not Enabled for the Project**
   - **Issue**: Google Drive API or OAuth API not enabled in the Google Cloud project
   - **Fix**: In Google Cloud Console, go to "APIs & Services" > "Library" and enable:
     - Google Drive API
     - (OAuth API is enabled by default when creating OAuth credentials)

### 6. **Using Wrong Credential Type**
   - **Issue**: Using API key or service account credentials instead of OAuth client ID
   - **Fix**: Ensure you're using OAuth 2.0 Client ID credentials (not API keys or service accounts)

### 7. **Environment Variable Not Loading**
   - **Issue**: Backend not reading the `.env` file correctly
   - **Check**: 
     - Ensure `.env` file is in the backend root directory (same level as `app/` folder)
     - Verify Python environment has `python-dotenv` installed (should be in requirements)
     - Check `backend/app/core/config.py` loads environment variables correctly

## Verification Steps

To diagnose and fix this issue:

1. **Check .env file**:
   ```bash
   cat /c/Users/devon/Downloads/Self\ Learning/Projects/Unified\ Storage\ Provider/backend/.env
   ```

2. **Verify Google Cloud Console Configuration**:
   - Go to https://console.cloud.google.com/
   - Select your project
   - Navigate to APIs & Services > Credentials
   - Find your OAuth 2.0 Client ID
   - Check:
     - Application type is "Web application"
     - Authorized redirect URIs includes `http://localhost:3000/api/v1/google/oauth/callback`
     - Client ID and Secret match your .env file

3. **Check OAuth Consent Screen**:
   - APIs & Services > OAuth consent screen
   - Ensure it's configured and published (even for testing)
   - Add your Google email as a test user if needed

4. **Test Backend Endpoint Directly**:
   - Start the backend server
   - Visit: `http://localhost:8000/api/v1/google/oauth/url`
   - Should return JSON with `auth_url` pointing to Google's OAuth endpoint
   - If you get an error here, the issue is in backend configuration

5. **Check Backend Logs**:
   - Look for error messages when starting the server or when making OAuth calls
   - The `google_drive_service.py` has logging that might reveal configuration issues

## Quick Fix Checklist

1. [ ] Verify `.env` file has correct GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET
2. [ ] Confirm Google Drive API is enabled in Google Cloud Console
3. [ ] Ensure OAuth consent screen is configured and published
4. [ ] Validate redirect URI matches exactly in .env and Google Cloud Console
5. [ ] Use OAuth 2.0 Client ID credentials (not API key or service account)
6. [ ] Restart backend after updating .env file
7. [ ] For testing, add your Google account as a test user in OAuth consent screen

The error "invalid_client" specifically indicates that Google cannot verify the application identity, which almost always points to issues with the OAuth client ID/secret configuration or the OAuth consent screen setup.