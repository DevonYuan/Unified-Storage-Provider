import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { googleDriveService } from '../api/googleDrive.service';
import GoogleDriveConnector from '../components/google-drive/GoogleDriveConnector';
import Button from '@/components/ui/Button';

const Dashboard: React.FC = () => {
  const { user } = useAuth();
  const [googleConnected, setGoogleConnected] = useState(false);
  const [recentFiles, setRecentFiles] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    checkGoogleConnection();
  }, [user?.email]);

  const checkGoogleConnection = async () => {
    if (!user?.email) return;

    setLoading(true);
    try {
      await googleDriveService.getGoogleTokens();
      setGoogleConnected(true);
      loadRecentFiles();
    } catch (err) {
      setGoogleConnected(false);
    } finally {
      setLoading(false);
    }
  };

  const loadRecentFiles = async () => {
    try {
      const response = await googleDriveService.listGoogleFiles(undefined, { pageSize: 5 });
      setRecentFiles(response.files || []);
    } catch (err) {
      console.error('Failed to load recent files:', err);
    }
  };

  if (!user) {
    return (
      <div style={{ maxWidth: '800px', margin: '2rem auto', padding: '1rem' }}>
        <h2>Dashboard</h2>
        <p>Please log in to access your dashboard.</p>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: '800px', margin: '2rem auto', padding: '1rem' }}>
      <h2>Dashboard</h2>
      <p>Welcome, {user?.email}!</p>

      <div className="mt-6">
        <h3 className="text-lg font-semibold mb-4">Google Drive Integration</h3>
        <div className="space-y-4">
          {loading ? (
            <div>Checking connection...</div>
          ) : (
            <>
              <GoogleDriveConnector />
              {googleConnected ? (
                <>
                  <p className="text-green-600">✓ Connected to Google Drive</p>
                  {recentFiles.length > 0 && (
                    <>
                      <h4 className="font-medium mb-2">Recent Files</h4>
                      <div className="space-y-2">
                        {recentFiles.map((file) => (
                          <div key={file.id} className="flex justify-between items-center p-3 bg-gray-50 rounded-md">
                            <div className="flex items-center space-x-3">
                              <div className="w-8 h-8 flex items-center justify-center bg-blue-100 rounded-full text-sm">
                                {file.mime_type === 'application/vnd.google-apps.folder' ? '📁' : '📄'}
                              </div>
                              <div>
                                <div className="font-medium">{file.name}</div>
                                <div className="text-xs text-gray-500">{file.mime_type}</div>
                              </div>
                            </div>
                            <button
                              onClick={() => {
                                // In a full implementation, this would navigate to file details or download
                                alert(`Would open/download: ${file.name}`);
                              }}
                              className="text-sm text-blue-600 hover:text-blue-800"
                            >
                              Open
                            </button>
                          </div>
                        ))}
                      </div>
                    </>
                  )}
                </>
              ) : (
                <p className="text-gray-600">Not connected to Google Drive. Click "Connect Google Drive" above to get started.</p>
              )}
            </>
          )}
        </div>

        <div className="mt-6">
          <Button
            onClick={() => {
              // Navigate to full Google Drive interface
              window.location.href = '/google-drive';
            }}
            variant="outline"
            disabled={!googleConnected}
          >
            Browse Google Drive
          </Button>
        </div>
      </div>

      <div className="mt-8">
        <p>Your unified storage pool is being set up.</p>
      </div>
    </div>
  );
};

export default Dashboard;
