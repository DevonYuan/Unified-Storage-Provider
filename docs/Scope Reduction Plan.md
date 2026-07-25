# OmniDrive Implementation Plan: Single-User Pivot

This document outlines the actionable steps to transition OmniDrive from a multi-user architecture to a streamlined, single-user personal tool. This pivot reduces unnecessary complexity while retaining the core infrastructure needed for the Unified Storage Pool.

## 1. Authentication & Email Verification Teardown
Since this tool is strictly for personal use, the complex registration and email verification loop will be removed in favor of a secure, single-user JWT login.

### Backend (FastAPI)
*   **Remove Brevo Integration:** Delete the `BREVO_API_KEY` from the `.env` file and remove all email-sending logic/services.
*   **Strip Registration Endpoints:** Delete the `/register` and `/verify-email` endpoints. 
*   **Simplify Auth:** Modify the `/login` endpoint. Instead of checking a database of users, validate against a single strong admin password or hash stored securely in your `.env` file. Keep the JWT generation logic intact.
*   **Clean up Models:** Remove `verification_token` and related fields from any existing Pydantic models or schemas.

### Frontend (React/Vite)
*   **Delete Signup UI:** Remove the Registration page and any links pointing to it.
*   **Remove Verification Pages:** Delete the verification success page and the 404 page associated with the verification routing.
*   **Streamline Login:** Ensure the login page simply takes a password (or dummy email + password) that matches your single-user backend logic.

## 2. Database Adjustments (PostgreSQL / Supabase)
The database remains critical for Phase 2 and Phase 4, but user-management overhead can be stripped.

*   **Clean Existing Tables:** Drop any tables or columns specifically created for user registration, email verification statuses, or password reset tokens.
*   **Prepare Phase 2 Tables:** Ensure your schema is ready for the `google_oauth_tokens` (id, access_token, refresh_token, expires_at) and `google_files` tables. You can drop the `user_id` foreign keys from these tables since you are the only user, or hardcode a single `user_id` (e.g., `1`) to avoid breaking future foreign key relationships.

## 3. Test Suite Refactoring
The testing rules strictly state that tests must be written and maintained. We need to align the Phase 1 tests with the new architecture.

*   **Backend Tests:** 
    *   Delete tests asserting Brevo API mocks or email sending behavior.
    *   Delete tests checking for the removed `verification_token`.
    *   Update login tests to authenticate using the single-user credentials rather than creating a mock user in the database first.
*   **Frontend Tests:**
    *   Remove tests that check for the presence of the signup form or verification messages.
    *   Ensure the login UI tests still pass.

## 4. Resuming Phase 2 (Google Drive Integration)
With the skeleton simplified, you can return focus to the Google Drive OAuth flow.

*   **Address Authentication Error:** Investigate the "not authenticated" error encountered after the Google callback.
*   **Validate Redirect URI:** Ensure the Google Cloud Console authorized redirect URI (`http://127.0.0.1:8000/auth/google/callback`) exactly matches the route in your FastAPI backend.
*   **Token Exchange:** Verify that the backend callback endpoint is successfully extracting the authorization code from the query parameters, exchanging it for an `access_token` and `refresh_token`, and storing them in the Supabase database.
