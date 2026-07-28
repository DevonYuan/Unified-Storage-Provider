# Phase 2 Implementation Plan: Google Drive Integration

## Context
Based on reviewing README.md and the existing phase2.md notes, Phase 2 focuses on implementing Google Drive integration so users can work with their Google Drive accounts through the OmniDrive interface. The goal is to enable users to navigate and interact with their Google Drive files as if using Google Drive directly.

## Current State Analysis
From examining the codebase:
- Phase 1 (authentication skeleton) is complete
- Google Drive OAuth flow is implemented in backend (`backend/routers/auth.py`)
- Storage account management is implemented (`backend/routers/storage.py`)
- Google Drive service layer exists (`backend/services/google_drive.py`)
- Frontend has basic structure with HomePage and ConnectedHomePage components
- FileCard component exists for displaying files
- API client connects frontend to backend

## Implementation Plan

### Backend Changes Needed:
1. **File Upload Endpoint** - Add file upload capability to storage router
   - Endpoint: `POST /storage/{account_id}/files/upload`
   - Handle multipart/form-data for file uploads
   - Integrate with Google Drive API for file creation/upload
   - Return file metadata consistent with existing FileItem model

2. **Enhanced Storage Router** - Update existing endpoints if needed:
   - Ensure list_files endpoint properly handles pagination for larger folders
   - Add error handling for common Google Drive API issues

### Frontend Changes Needed:
1. **ConnectedHomePage.jsx Enhancements**:
   - Add Upload button to controls section (next to view toggle)
   - Implement file upload handler using storageApi
   - Fix item count display to match spec: "{itemCount} item(s) · sorted by recent"
   - Add visual feedback during upload (progress indicator)

2. **FileCard.jsx Enhancements**:
   - Implement visual indicators as specified in phase2.md:
     - Top-left color dot (green for Google Drive origin) - already partially implemented as `file-card__origin`
     - Top-right favorite star icon (optional feature for future enhancement)
   - Ensure proper styling for all file types as described:
     - Folders: large folder icon centered
     - Media/Images: preview thumbnail top half, details bottom
     - Documents/Files: generic file/text/sheet icon centered, details bottom

3. **Styling Updates**:
   - Ensure `file-card__origin` displays as colored dot (green for Google Drive)
   - Add favorite star styling if implementing that feature
   - Verify responsive behavior matches specifications

### API Endpoints to Implement:
**Backend:**
- POST `/storage/{account_id}/files/upload` - Upload file to Google Drive account

**Frontend API Usage:**
- `storageApi.uploadFile(accountId, file, parentId)` - New method to handle uploads

### Verification Steps:
1. Manual testing of Google Drive OAuth flow
2. Verify file listing shows proper icons and metadata
3. Test file upload functionality with various file types
4. Verify visual indicators (origin dot, file type icons) display correctly
5. Test filtering, sorting, and view toggling functionality
6. Ensure responsive design works across screen sizes
7. Confirm error handling works properly (network issues, auth errors, etc.)

### Dependencies:
- Google Drive API credentials properly configured in backend
- Frontend API client updated to support file uploads
- Proper error handling for upload failures and quota exceeded scenarios

### Risk Assessment:
- Low risk: Backend upload endpoint follows existing patterns
- Medium risk: Frontend upload implementation requires handling file selection and FormData
- Low risk: Visual enhancements are primarily CSS/styling changes
- Medium risk: Ensuring proper error handling and user feedback during upload operations

## Files to Modify:
1. `backend/routers/storage.py` - Add upload endpoint
2. `frontend/src/api/client.js` - Add uploadFile method to storageApi
3. `frontend/src/components/ConnectedHomePage.jsx` - Add upload button and handler
4. `frontend/src/components/FileCard.jsx` - Enhance visual indicators
5. `frontend/src/styles/FileCard.css` - Style origin indicator and visual elements
6. `frontend/src/styles/ConnectedHomePage.css` - Style upload button (if needed)

## Acceptance Criteria:
- User can successfully connect Google Drive account via OAuth
- ConnectedHomePage displays Google Drive files with proper icons and metadata
- File cards show appropriate visual indicators (file type icons, origin dot)
- Users can filter, sort, and toggle between grid/list views
- Users can upload files to connected Google Drive account
- Upload shows appropriate feedback and handles errors gracefully
- Interface matches the specifications outlined in phase2.md