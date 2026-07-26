# OmniDrive: Unified Cloud Storage Pool

This is a personal tool that I made for myself, to manage my two cloud storage accounts (specifically Google Drive and Microsoft OneDrive) into a single seamless, and unified virtual storage pool. 

Instead of jumping between different interfaces and managing fragmented storage limits, OmniDrive acts as a router and abstraction layer. It presents a single interface where your total available storage is the sum of your connected providers, automatically handling distribution and retrieval across APIs without costing a dime in infrastructure fees.

## Tech Stack 
**Backend**:
- Backend framework: FastAPI 
- Managing Google Drive: Google Drive API
- Managing Microsoft: Microsoft Graph Files API

**Frontend**: React with Vite<br>

Once the backend and frontend run locally, we will package the app as a desktop app using Electron. 

## Phases
We will elaborate more on this in separate documents. 
### Phase 1 - Skeleton
Build a working skeleton of a web app. I intend for this to be an app where users can store their required data locally, meaning they will not need to log in with authentication because I will not be collecting data. 

### Phase 2 - Google Drive Integration
Add support for Google Drive. The end goal is that you can effectively navigate the app, as if you were using Google Drive directly. Under the hood, we will be working with the Google Drive API. 

### Phase 3 - Microsoft OneDrive Integration
Add support for Microsoft OneDrive. The end goal is that you can effectively navigate the app, as if you were using OneDrive directly. Under the hood, we will be working with the Microsoft Graph Files API. Note that at the end of the phase the user should be able to choose which provider they are using. 

### Phase 4 - Unified Storage Pool
Implement the core functionality that merges the storage from both providers into a single virtual filesystem. This includes handling file chunking, automatic distribution across providers based on available space, and seamless retrieval regardless of where the file is physically stored. The user should experience this as a single, unified drive with combined storage capacity. 

### Phase 5 - Polishing (Optional)
Explore different UI styles and experiment with different AI tools to only enhance the UI, but do NOT break the functionality of the app? 

## Footnote 
I originally intended for this app to suport several users, but it must undergo Google's verification process to allow users without having to explicitly add them to a list in the GCP console. I fully intend on preparing demo videos and submitting them for review in the future, but until then, you will have to contact me, so that I can add you to a list of test users. 