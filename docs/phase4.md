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
- Con: It is a bit inefficient to recreate the tree every single time. However, this is mitigated by the fact that if the user only uses OmniDrive, then it should be a relatively very fast process. 

For the situations where we are forcing the renaming of files, I propose adding "-google" and "-onedrive" at the end of the files.

## Edge Case: File-Folder Name Collision

The merge rules above handle same-name files and same-name folders separately, but then: **what if Google Drive has a file named "Budget" in root and OneDrive has a folder named "Budget" in root?**

Since a file and folder cannot coexist with the same name in a single directory, we need an explicit rule: We will treat file-folder name collisions as file collisions. Force-rename the file (not the folder) by appending the provider suffix. The folder retains its original name.

**Rationale**:
- Folders are more likely to be merge targets (they may contain shared content)
- Renaming a folder breaks the merge key for all its descendants
- Renaming a single file is a localized change
- This preserves the folder structure for potential merges at deeper levels

**Example**:
- Google Drive: `/Budget.xlsx` (file)
- OneDrive: `/Budget/` (folder containing reports)
- OmniDrive view: `/Budget-google.xlsx` and `/Budget/` (folder)

## Edge Case: Double-Collision on Forced Rename

When we force-rename a colliding file (e.g., `Budget.xlsx` → `Budget-google.xlsx`), there arises another risk: **what if a file already named `Budget-google.xlsx` exists in that same directory on Google Drive?**

Since this is deterministic logic running without user prompts, we need a defined fallback:

**Fallback Strategy**: Append a counter suffix until a unique name is found.

**Algorithm**:
1. Try `{original_name}-{provider}.{ext}` (e.g., `Budget-google.xlsx`)
2. If exists, try `{original_name}-{provider}-2.{ext}` (e.g., `Budget-google-2.xlsx`)
3. If exists, try `{original_name}-{provider}-3.{ext}`, incrementing until unique
4. Cap at reasonable limit (e.g., 100 attempts) to prevent infinite loops

**Example**:
- Google Drive: `/Budget.xlsx`, `/Budget-google.xlsx`, `/Budget-google-2.xlsx`
- OneDrive: `/Budget.xlsx`
- OmniDrive view: `/Budget-google-3.xlsx` (from Google), `/Budget-onedrive.xlsx` (from OneDrive) 

## Storage Pooling 
Firstly, we will not be chunking files. Secondly, let us discuss the plan for handling new uploads. When a file is uploaded to the root directory of OmniDrive OR when a folder is created (In the root directory), it will alternate between going into the root directory of Google Drive, and the root directory of OneDrive. This means: 
- The storage will be more evenly distributed across the 2 platforms. 
- It is easier to test. If I went with an alternative approach such as taking up all the space in Google Drive, then taking up all the space in OneDrive, I would have to upload so much content that I exhaust the free tier of one provider before moving onto the next. <br>

I am sure that there are more benefits as well as trade-offs, but these are the most immediate ones that come to mind. As for implementing this, we can create a separate table in the database with one row, where we keep on updating the variable telling us whether to add new uploads to Google Drive or OneDrive. Given that we are already using a SQLite database for phases 2 and 3, this seems to be the most efficent solution. <br>

As for handling new file uploads in existing folders: We will keep them in the respective provider's folder. For example, if I have a folder in Google Drive and I want to create a subfolder, that subfolder will NOT be "provisioned" in OneDrive. While this is a bit inefficient, consider Goal #2: This is to make sure that you can easily download the files / folders if you wanted to. While OmniDrive *could* have logic that will pull the files from each provider when you try to download a folder, that also means you can't download the file directory from Google Drive (Since 1 file would be located in OneDrive).

## Edge Case: Delete/Rename Propagation on Merged Folders

The merge logic described above handles the **read side** (how we construct the unified view), but not the **write side** (how user actions propagate back to providers). This is critical for merged folders.

**Scenario**: Google Drive has `/Documents/` and OneDrive has `/Documents/`. These merge into a single logical folder in OmniDrive. What happens when the user:

1. **Renames** the logical `/Documents/` folder to `/Docs/` in OmniDrive?
2. **Deletes** the logical `/Documents/` folder in OmniDrive?

**Decision**: Write operations on merged folders should **propagate to all underlying provider folders**.

**Rationale**:
- A merged folder represents a single logical entity spanning multiple providers
- If we only rename/delete on one provider, the merge breaks on next launch (name-matching key fails)
- User expects unified behavior — they see one folder, they act on one folder
- This is a one-to-many write, but it's the only way to maintain consistency without breaking everything

**Implementation**:
- **Rename**: When user renames a merged folder, issue rename API calls to all providers that have that folder. If any rename fails, rollback all successful renames and report error.
- **Delete**: When user deletes a merged folder, issue delete API calls to all providers that have that folder. Same rollback-on-error logic.
- **Metadata updates**: Same propagation logic applies to any folder metadata changes (e.g., color labels, descriptions if providers support them)

**Error Handling**:
- If a provider is offline or API fails, the operation should fail entirely (atomic across providers)
- Show clear error message indicating which provider failed and why
- Consider adding a "force" option for deletes (skip failed providers) in future phases

**Trade-off acknowledged**: This means users cannot have different folder names across providers for the same logical folder. This is intentional — the unified view requires unified naming.

## Edge Case: Mid-Session Drift

The tree is rebuilt at launch by fetching fresh data from both providers. However, users may upload/create/delete/rename files during an active OmniDrive session through the OmniDrive interface itself. Additionally, users might make changes in a browser tab to Google Drive or OneDrive while OmniDrive is open.

**Decision**: Accept that **only a full app restart reflects provider-side changes made outside OmniDrive**. For changes made through OmniDrive itself, we will **mutate the in-memory tree incrementally**.

**Rationale**:
- Incremental in-memory updates for OmniDrive-initiated actions are cheap and provide immediate feedback
- Polling providers for external changes would be complex (rate limits, conflict resolution, performance)
- Rebuilding the tree on app restart is simple and guarantees consistency
- This is a reasonable trade-off for a single-user desktop app

**Implementation**:
- **OmniDrive-initiated changes**: When user uploads/creates/deletes/renames through OmniDrive, immediately update the in-memory tree to reflect the change. Do NOT re-fetch from providers.
- **External provider changes**: If user makes changes in browser tab to Google Drive/OneDrive, those changes will NOT appear in OmniDrive until app restart. Show a subtle indicator (optional Phase 5) that a refresh is available.
- **Conflict detection**: If OmniDrive tries to perform an operation that fails because the provider state changed externally (e.g., delete a file that was already deleted in browser), handle the API error gracefully and refresh the tree.

**Alternative considered**: Implement periodic polling or webhooks. Rejected because:
- Adds significant complexity (webhook registration, endpoint exposure, rate limit management)
- Overkill for single-user desktop app
- User can simply restart app to sync  
- OmniDrive is not meant to be used this way anyways! Users should not be doing this, but we are just trying to prevent the app from crashing if it *does* happen. 

## Defining the User Experience 
Before the implementation plan, let's figure out what the final state of OmniDrive *should* be so we have a clear idea of the functionalities that we want. 

Right now, when the user opens OmniDrive, they can click a button that opens up a drop-down with 2 options, where you can navigate Google Drive and OneDrive effectively by choosing which provider. I intend to keep this, BUT:
- We are going to add a new option, where we call it OmniDrive. 
- The user can click on this option to experience the purpose of the app: A unified storage pool that "merges" the 2 other providers together. 
- This will become the new default option. 
- When we use this option, just for clarity, we can include a small green or blue dot next to each file name to indicate whether the file is stored in Google Drive or OneDrive. For merged folders, we can have a "split" indicator with green on 1 side and blue on the other. 