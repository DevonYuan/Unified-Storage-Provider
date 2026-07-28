# Notes for Phase 2 
- A note on data storage: In this phase we will only store OAuth tokens so that the user does not have to connect Google Drive every single time. For phase 3, I will make sure to include a similar note for whatever the equivalent credentials are in MS graph files. 
- Lesson Learned: Keyring is a python library that is very useful for storing credentials locally. Essentially, keyring allows me to delegate the process of encrypting, storing and retrieving sensitive information to my OS so that I do not have to handle it myself. 
- Path to the DB is safe to expose since the data is stored locally. 

# Implementation Pan 
So far, I need to implement the dashboard so that the user can actually work with their Google Drive account. The ConnectedHomePage.jsx SHOULD be designed as follows: 
- The dashboard at the top should be identical to the one in the HomePage.jsx
- There should be a Main Content Area Beneath, where you actually see the files. 
- Header: Large "All files" title with a subtitle showing item count (For example: "14 items · sorted by recent").
- Controls (Right-aligned): Filter dropdown, Sort dropdown, Grid/List view toggle, and an "↑ Upload" button.
- File Grid Layout: A responsive grid of large card components representing files and folders:
- Folders: Display a large folder icon centered in the dark card block, with the folder name and item count at the bottom.
- Media/Images: The top half of the card renders a full image preview/thumbnail, with the filename, size, and timestamp at the bottom.
- Documents/Files: Display a generic file/text/sheet icon centered, with details at the bottom.
- Indicators: Cards should support a small top-left color dot (green for Google Drive origin) and an optional top-right favorite star icon.
- A reference is found in design-inspo 

