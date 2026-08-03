# Notes for Phase 4 
## Each Time We Run OmniDrive
Before we even talk about the architecture / what we are doing with the API's, let's figure out the logic behind the internal file system. We can imagine that both Google Drive and OneDrive's file systems are 2 different trees. We have 2 main goals:

1. To leave the smallest impact on the separate file systems while OmniDrive works.

2. For OmniDrive to still be functional even if the users go ahead and do their own things in their separate drives (Such as creating, deleting, renaming, and moving files). <br>

To achieve Goal #2, my plan is to create a new tree to represent OmniDrive's internal file system each time we actually open OmniDrive. We can create this new tree by merging the existing Google Drive and OneDrive trees. For the most part, this will be a smooth process, except for when there are multiple files / folders with the same name. 
- For **files** with the same name in the same directory of the respective providers (E. g. Copies of the same document in the root directory of Google Drive and OneDrive), we will have to force renaming to happen. 
- For **folders** with the same name, we can merge them into 1 folder, then recursively repeat the process of merging the contents within the 2 folders. <br>

This will also help us achieve goal 1 in the process, but there is a trade-off involved: 
- Pro: Local data storage is not as important, because we can create the internal file systems ourselves every time. We should not store the internal file system locally, especially when it is prone to changing without us knowing (Reference Goal #2). Note that assuming the user only uses OmniDrive (i. e. does not use Google Drive or OneDrive separately), the results will be the same every time. 
- Con: It is a bit inefficient to recreate the tree every single time. However, this is mitigated by the fact that if the user only uses OmniDrive, then it will be a relatively smooth process. 

For the situations where we are forcing the renaming of files, I propose adding "-google" and "-onedrive" at the end of the files. 

## Storage Pooling 
Firstly, we will not be chunking files. Secondly, let us discuss the plan for handling new uploads. When a file is uploaded to the root directory of OmniDrive OR when a folder is created (In the root directory), it will alternate between going into the root directory of Google Drive, and the root directory of OneDrive. This means: 
- The storage will be more evenly distributed across the 2 platforms. 
- It is easier to test. If I went with an alternative approach such as taking up all the space in Google Drive, then taking up all the space in OneDrive, I would have to upload so much content that I exhaust the free tier of one provider before moving onto the next. <br>

I am sure that there are more benefits as well as trade-offs, but these are the most immediate ones that come to mind. As for implementing this, we can create a separate table in the database with one row, where we keep on updating the variable telling us whether to add new uploads to Google Drive or OneDrive. Given that we are already using a SQLite database for phases 2 and 3, this seems to be the most efficent solution. <br>

As for handling new file uploads in existing folders: We will keep them in the respective provider's folder. For example, if I have a folder in Google Drive and I want to create a subfolder, that subfolder will NOT be "provisioned" in OneDrive. While this is a bit inefficient, consider Goal #2: This is to make sure that you can easily download the files / folders if you wanted to. While OmniDrive *could* have logic that will pull the files from each provider when you try to download a folder, that also means you can't download the file directory from Google Drive (Since 1 file would be located in OneDrive).  

## Defining the User Experience 
Before the implementation plan, let's figure out what the final state of OmniDrive *should* be so we have a clear idea of the functionalities that we want. 

Right now, when the user opens OmniDrive, they can click a button that opens up a drop-down with 2 options, where you can navigate Google Drive and OneDrive effectively by choosing which provider. I intend to keep this, BUT:
- We are going to add a new option, where we call it OmniDrive. 
- The user can click on this option to experience the purpose of the app: A unified storage pool that "merges" the 2 other providers together. 
- This will become the new default option. 
- When we use this option, just for clarity, we can include a small green or blue dot next to each file name to indicate whether the file is stored in Google Drive or OneDrive. For merged folders, we can have a "split" indicator with green on 1 side and blue on the other. 