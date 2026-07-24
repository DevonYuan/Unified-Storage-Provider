import React, { useState, useEffect } from 'react';
import { googleDriveService } from '../../api/googleDrive.service';
import GoogleDriveConnector from './GoogleDriveConnector';
import GoogleDriveFileItem from './GoogleDriveFileItem';
import GoogleDriveUploadButton from './GoogleDriveUploadButton';
import GoogleDriveFolderCreator from './GoogleDriveFolderCreator';
import Button from '@/components/ui/Button';

const GoogleDriveFileBrowser: React.FC = () => {
  const [files, setFiles] = useState<Array<any>>([]);
  const [currentFolderId, setCurrentFolderId] = useState<string | null>(null);
  const [breadcrumb, setBreadcrumb] = useState<Array<{ id: string; name: string }>>([
    { id: 'root', name: 'My Drive' }
  ]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [showFolderModal, setShowFolderModal] = useState(false);

  // Load files when component mounts or folder changes
  useEffect(() => {
    loadFiles();
  }, [currentFolderId]);

  const loadFiles = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await googleDriveService.listGoogleFiles(currentFolderId);
      setFiles(response.files || []);
    } catch (err: any) {
      setError('Failed to load files');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleUpload = async (file: File) => {
    try {
      await googleDriveService.uploadGoogleFile(file, currentFolderId);
      await loadFiles(); // Refresh file list
    } catch (err: any) {
      throw new Error(err.message || 'Upload failed');
    }
  };

  const handleCreateFolder = async (folderName: string, parentId: string | null) => {
    try {
      await googleDriveService.createGoogleFolder({ name: folderName, parent_id: parentId });
      await loadFiles(); // Refresh file list
    } catch (err: any) {
      throw new Error(err.message || 'Failed to create folder');
    }
  };

  const handleDelete = async (fileId: string) => {
    if (!window.confirm('Are you sure you want to delete this file/folder?')) {
      return;
    }

    try {
      await googleDriveService.deleteGoogleFile(fileId);
      await loadFiles(); // Refresh file list
    } catch (err: any) {
      setError('Failed to delete file');
      console.error(err);
    }
  };

  const handleRename = async (fileId: string, newName: string) => {
    try {
      await googleDriveService.renameGoogleFile(fileId, { name: newName });
      await loadFiles(); // Refresh file list
    } catch (err: any) {
      setError('Failed to rename file');
      console.error(err);
    }
  };

  const navigateToFolder = (folder: any) => {
    setCurrentFolderId(folder.id);
    setBreadcrumb(prev => [
      ...prev.slice(0, prev.findIndex(item => item.id === folder.id) + 1),
      { id: folder.id, name: folder.name }
    ]);
  };

  const goBack = () => {
    if (breadcrumb.length <= 1) {
      setCurrentFolderId(null);
      setBreadcrumb([{ id: 'root', name: 'My Drive' }]);
    } else {
      const newBreadcrumb = breadcrumb.slice(0, -1);
      setBreadcrumb(newBreadcrumb);
      setCurrentFolderId(newBreadcrumb[newBreadcrumb.length - 1].id || null);
    }
  };

  const getFileIcon = (mimeType: string) => {
    if (mimeType === 'application/vnd.google-apps.folder') {
      return '📁';
    }
    if (mimeType.startsWith('image/')) {
      return '🖼️';
    }
    if (mimeType === 'application/pdf') {
      return '📄';
    }
    if (mimeType.includes('document') || mimeType.includes('text')) {
      return '📝';
    }
    if (mimeType.includes('spreadsheet')) {
      return '📊';
    }
    if (mimeType.includes('presentation')) {
      return '📊';
    }
    if (mimeType.includes('video')) {
      return '🎥';
    }
    if (mimeType.includes('audio')) {
      return '🎵';
    }
    return '📄'; // Default file icon
  };

  if (loading && files.length === 0) {
    return <div className="text-center py-8">Loading...</div>;
  }

  if (error) {
    return <div className="text-center text-red-600 py-8">{error}</div>;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center flex-wrap">
        <div>
          <h2 className="text-xl font-bold">Google Drive</h2>
          <p className="text-sm text-gray-600">{breadcrumb.length > 1 ? breadcrumb[breadcrumb.length - 1].name : 'My Drive'}</p>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={goBack}
            disabled={breadcrumb.length <= 1}
            className={`px-3 py-1 bg-white border border-gray-300 rounded-md
              text-sm hover:bg-gray-50 disabled:opacity-50 transition-colors`}
          >
            ← Back
          </button>
          <Button onClick={() => setShowUploadModal(true)} variant="outline">
            Upload
          </Button>
          <Button onClick={() => setShowFolderModal(true)} variant="outline">
            New Folder
          </Button>
        </div>
      </div>

      {/* Breadcrumb navigation */}
      <div className="flex items-center space-x-2 text-sm text-gray-600">
        {breadcrumb.map((crumb, index) => (
          <React.Fragment key={crumb.id}>
            {index > 0 && <span>/</span>}
            <button
              onClick={() => {
                const newBreadcrumb = breadcrumb.slice(0, index + 1);
                setBreadcrumb(newBreadcrumb);
                setCurrentFolderId(newBreadcrumb[newBreadcrumb.length - 1].id || null);
              }}
              className={`hover:text-violet-600 transition-colors`}
            >
              {crumb.name}
            </button>
          </React.Fragment>
        ))}
      </div>

      {/* Files grid */}
      <div className="space-y-4">
        {files.length === 0 ? (
          <div className="text-center py-8 text-gray-600">
            <p>This folder is empty</p>
            {!breadcrumb.length <= 1 && (
              <Button onClick={() => setShowFolderModal(true)} variant="outline" size="sm">
                Add Folder
              </Button>
            )}
          </div>
        ) : (
          <div className="space-y-4">
            {files.map((file) => (
              <div
                key={file.id}
                className="flex items-start space-x-4 p-4 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
              >
                <div className="flex-shrink-0">
                  <div className="w-12 h-12 flex items-center justify-center bg-gray-100 rounded-lg text-xl">
                    {getFileIcon(file.mime_type)}
                  </div>
                </div>
                <div className="flex-1 space-y-2">
                  <div className="flex justify-between items-start">
                    <h3 className="font-medium truncate max-w-xs">{file.name}</h3>
                    <div className="flex space-x-2">
                      <button
                        onClick={() => {
                          if (file.mime_type === 'application/vnd.google-apps.folder') {
                            navigateToFolder(file);
                          } else {
                            // For files, we could show a preview or download
                            // For now, just download
                            console.log('Would download file:', file.id);
                          }
                        }}
                        className={`p-1 rounded-hover text-gray-400 hover:text-gray-600 transition-colors`}
                      >
                        {/* In a real app, we'd have proper icons */}
                        📄
                      </button>
                      <button
                        onClick={() => {
                          // Open rename dialog (simplified - in reality would use a modal)
                          const newName = prompt('Enter new name:', file.name);
                          if (newName && newName !== file.name) {
                            handleRename(file.id, newName);
                          }
                        }}
                        className={`p-1 rounded-hover text-gray-400 hover:text-gray-600 transition-colors`}
                      >
                        ✏️
                      </button>
                      <button
                        onClick={() => handleDelete(file.id)}
                        className={`p-1 rounded-hover text-gray-400 hover:text-red-600 transition-colors`}
                      >
                        🗑️
                      </button>
                    </div>
                  </div>
                  <div className="text-sm text-gray-500 space-y-1">
                    <p>{file.mime_type}</p>
                    {file.size !== null && file.size !== undefined && (
                      <p>
                        {(file.size / 1024).toFixed(1)} KB
                      </p>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default GoogleDriveFileBrowser;