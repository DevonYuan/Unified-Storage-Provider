import React from 'react';

const GoogleDriveFileItem: React.FC<{
  file: any;
  onClick: (file: any) => void;
}> = ({ file, onClick }) => {
  // Determine file type for icon
  const getFileIcon = (mimeType: string) => {
    if (mimeType === 'application/vnd.google-apps.folder') {
      return '📁'; // Folder icon
    }
    if (mimeType.startsWith('image/')) {
      return '🖼️'; // Image icon
    }
    if (mimeType === 'application/pdf') {
      return '📄'; // PDF icon
    }
    if (mimeType.startsWith('video/')) {
      return '🎥'; // Video icon
    }
    if (mimeType.startsWith('audio/')) {
      return '🎵'; // Audio icon
    }
    if (mimeType.includes('text/') || mimeType === 'application/json') {
      return '📝'; // Text icon
    }
    if (mimeType.includes('spreadsheet') || mimeType.includes('excel')) {
      return '📊'; // Spreadsheet icon
    }
    if (mimeType.includes('presentation') || mimeType.includes('powerpoint')) {
      return '🎯'; // Presentation icon
    }
    return '📄'; // Default file icon
  };

  return (
    <div
      onClick={() => onClick(file)}
      className="flex items-center p-3 bg-gray-50 rounded-lg hover:bg-gray-100 cursor-pointer transition-colors"
    >
      <div className="text-2xl mr-3">{getFileIcon(file.mime_type || '')}</div>
      <div className="flex-1 min-w-0">
        <div className="font-medium truncate">{file.name}</div>
        <div className="text-xs text-gray-500">
          {file.mime_type || 'Unknown type'}
        </div>
      </div>
      {!file.parent_id && (
        <div className="text-xs text-gray-400">(Root)</div>
      )}
    </div>
  );
};

export default GoogleDriveFileItem;