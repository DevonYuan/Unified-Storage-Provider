import React, { useState } from 'react';

const GoogleDriveFolderCreator: React.FC<{
  onCreate: (folderName: string, parentId: string | null) => Promise<void>;
  onCancel: () => void;
  parentId: string | null;
}> = ({ onCreate, onCancel, parentId }) => {
  const [folderName, setFolderName] = useState('');
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!folderName.trim()) {
      setError('Folder name is required');
      return;
    }

    setCreating(true);
    setError(null);
    try {
      await onCreate(folderName.trim(), parentId);
      setFolderName(''); // Clear form on success
      // Note: We don't close the modal here - parent component handles that
    } catch (err: any) {
      setError(err.message || 'Failed to create folder');
    } finally {
      setCreating(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label htmlFor="folder-name" className="block text-sm font-medium mb-1">
          Folder name
        </label>
        <input
          id="folder-name"
          type="text"
          value={folderName}
          onChange={(e) => setFolderName(e.target.value)}
          disabled={creating}
          placeholder="Enter folder name"
          className={`block w-full px-3 py-2 border border-gray-300 rounded-md
            text-sm focus:outline-none focus:ring-2 focus:ring-violet-500
            disabled:opacity-50`}
        />
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <div className="flex justify-end space-x-3">
        <button
          type="button"
          onClick={onCancel}
          disabled={creating}
          className={`px-4 py-2 bg-white border border-gray-300 rounded-md
            text-sm font-medium hover:bg-gray-50 disabled:opacity-50
            transition-colors`}
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={!folderName.trim() || creating}
          className={`px-4 py-2 bg-violet-600 text-white rounded-md
            text-sm font-medium hover:bg-violet-700 disabled:opacity-50
            transition-colors`}
        >
          {creating ? 'Creating...' : 'Create Folder'}
        </button>
      </div>
    </form>
  );
};

export default GoogleDriveFolderCreator;