# Phase 1 
July 21, 2026: 
- Created the table definitions 
- Tables are now created in the Supabase DB. (Task 1 complete)
- Added BREVO_API_KEY (For sending emails) and DATABASE_URL (For working with the DB via code) in the .env file 
- Added tests but I need to make sure that they fail (Since no implementation has been done yet)

July 22, 2026:
- I verified that the backend tests run and fail 
- Still unable to run the frontend tests because I am missing the script "test". 
- This is now verified: I can run the frontend tests and they fail. (COMPLETED PHASE 1 TASK 2)
- A backend is added, but I am now working on debugging the tests. Have not ran the app itself yet, but I need to figure out the ModuleError for the backend tests. 
- Update: The ModuleError is removed but the backend tests still fail 
- Update: Frontend tests pass 
- Update: I can run the app but there is no option to sign up through the UI 
- Update: The UI signup system sucks
- Update: Removed dev verification link from frontend Register page and replaced with rendered success message
- Update: Removed verification_token from backend register response for security 
- Update: The email message shows up in the UI but it is still not sending 