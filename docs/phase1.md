# Phase 1 - Web App Skeleton 
In this phase, we will implement a basic working web app. We will interact with a Supabase database, but the frontend and backend will remain locally running for now. 

## To-Do List 
### 1. Decide upon table definitions.
- Choose definitions for a basic web app with no functionality outside of being able to log in and log out. 
- We are not concerned with the functionality of later phases
- We will be using an email verification system via Brevo and JWT based authentication. I will manually add the environemnt variables.

**Acceptance Criteria:** 
- Define database schema for users table with fields: id, email, hashed_password, email_verified, created_at, updated_at
- Define Brevo email verification table with fields: id, user_id, token, expires_at, created_at
- Document JWT token structure and expiration times
- Consider adding fields for OAuth tokens for future Google/OneDrive integration
- Plan for future expansion to include file metadata tables

### 2. Write tests for the backend and frontend
- The tests apply strictly to the functionality of the login and authentication. 

**Acceptance Criteria:** 
- Write unit tests for user registration endpoint
- Write unit tests for login/logout endpoints
- Write unit tests for email verification flow
- Write frontend tests for login/logout UI components
- Write tests that verify JWT token creation and validation
- Ensure all tests clean up test data from database
- Use pytest for backend tests and Jest/Vitest for frontend tests
- Mock external services (Brevo email service) in tests

### 3. Implement the backend and frontend
- This one is self-explanatory. Tests MUST be written BEFORE this happens. 
- To run the backend tests added in task 2: Run with "pytest tests/phase1/ -v". Prior to this, you must install the depencies listed in requirements.txt (Which you can do by running "pip install -r requirements.txt")
- To run the frontend tests added task 2: Run with "npm test" or "yarn test". Prior to this, you must install the necessary dependencies (Which you can do by running "npm install" or "yarn install.")

**Acceptance Criteria:** 
- Implement user registration with email verification via Brevo
- Implement secure login/logout with JWT's
- Implement password reset functionality via email
- Create frontend login/register pages with form validation
- Create protected routes that require authentication
- Implement environment variable configuration for Brevo and JWT secrets
- Follow FastAPI best practices for dependency injection and error handling
- Use React hooks form library for form handling in frontend
- Implement proper loading states and error handling in UI

### 4. Manual testing 
- Ths one is also self-explanatory. 

**Acceptance Criteria:** 
- Test user registration flow end-to-end
- Test login/logout functionality
- Test email verification link functionality
- Test password reset flow
- Test protected routes redirect unauthenticated users
- Verify JWT tokens are properly set and cleared
- Test on both localhost and test deployment if available
- Test edge cases like invalid tokens, expired tokens, malformed requests 