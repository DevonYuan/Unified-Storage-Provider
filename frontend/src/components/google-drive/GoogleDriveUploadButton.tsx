import React, { useState } from 'react';

const GoogleDriveUploadButton: React.FC<{
  onUpload: (file: File) => Promise<void>;
  onCancel: () => void;
  parentId?: string | null;
}> = ({ onUpload, onCancel, parentId }) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] || null;
    setSelectedFile(file);
    setError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) return;

    setUploading(true);
    setError(null);
    try {
      await onUpload(selectedFile);
      // Reset form on success
      setSelectedFile(null);
      // Note: We don't close the modal here - parent component handles that
    } catch (err: any) {
      setError(err.message || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label htmlFor="file-upload" className="block text-sm font-medium mb-1">
          Select file to upload
        </label>
        <input
          id="file-upload"
          type="file"
          onChange={handleFileChange}
          disabled={uploading}
          className={`block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4
            file:rounded-md file:border-0 file:text-sm file:font-semibold
            file:bg-violet-50 file:text-violet-600 hover:file:bg-violet-100
            disabled:opacity-50`}
        />
        {selectedFile && (
          <p className="mt-2 text-sm text-gray-600 truncate">
            Selected: {selectedFile.name}
          </p>
        )}
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <div className="flex justify-end space-x-3">
        <button
          type="button"
          onClick={onCancel}
          disabled={uploading}
          className={`px-4 py-2 bg-white border border-gray-300 rounded-md
            text-sm font-medium hover:bg-gray-50 disabled:opacity-50
            transition-colors`}
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={!selectedFile || uploading}
          className={`px-4 py-2 bg-violet-600 text-white rounded-md
            text-sm font-medium hover:bg-violet-700 disabled:opacity-50
            transition-colors`}
        >
          {uploading ? 'Uploading...' : 'Upload'}
        </button>
      </div>
    </form>
  );
};

export default GoogleDriveUploadButton;