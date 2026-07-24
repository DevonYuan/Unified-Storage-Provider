import React from 'react';
import { useAuth } from '../context/AuthContext';
import GoogleDriveFileBrowser from '../components/google-drive/GoogleDriveFileBrowser';
import Button from '@/components/ui/Button';

const GoogleDrive: React.FC = () => {
  const { user } = useAuth();

  if (!user) {
    return (
      <div className="container py-12 text-center">
        <p className="text-gray-400">Please log in to access Google Drive.</p>
      </div>
    );
  }

  return (
    <div className="container py-12">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-bold text-white">Google Drive</h1>
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