import React from 'react';
import { useAuth } from '../context/AuthContext';
import GoogleDriveFileBrowser from '../components/google-drive/GoogleDriveFileBrowser';
import Button from '@/components/ui/Button';

const GoogleDrive: React.FC = () => {
  const { user } = useAuth();

  if (!user) {
    return <div>Please log in to access Google Drive.</div>;
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-bold text-gray-900">
          Google Drive
        </h1>
        <div className="flex items-center space-x-4">
          <Button variant="outline" onClick={() => { /* Refresh functionality */ }}>
            Refresh
          </Button>
          <Button
            onClick={() => { /* New file/upload functionality */ }}
            variant="primary"
          >
            New
          </Button>
        </div>
      </div>

      <GoogleDriveFileBrowser />
    </div>
  );
};

export default GoogleDrive;