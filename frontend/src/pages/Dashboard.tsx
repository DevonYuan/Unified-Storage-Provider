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
      <div className="container py-12">
        <h2 className="text-2xl font-bold mb-4 text-white">Dashboard</h2>
        <p className="text-gray-300">Please log in to access your dashboard.</p>
      </div>
    );
  }

  return (
    <div className="container py-12">
      <h2 className="text-2xl font-bold mb-6 text-white">Dashboard</h2>
      <p className="text-gray-300 mb-6">Welcome, {user.email}!</p>

      <div className="mb-8">
        <h3 className="text-xl font-semibold mb-4 text-white">Google Drive Integration</h3>
        <div className="space-y-4">
          {loading ? (
            <div className="text-gray-300">Checking connection...</div>
          ) : (
            <>
              <GoogleDriveConnector />
              {googleConnected ? (
                <>
                  <p className="text-green-400">✓ Connected to Google Drive</p>
                  {recentFiles.length > 0 && (
                    <>
                      <h4 className="font-medium mb-2 text-white">Recent Files</h4>
                      <div className="space-y-2">
                        {recentFiles.map((file) => (
                          <div key={file.id} className="card p-4 flex justify-between items-center">
                            <div className="flex items-center space-x-3">
                              <div className="w-8 h-8 flex items-center justify-center bg-blue-600/20 rounded-full text-sm">
                                {file.mime_type === 'application/vnd.google-apps.folder' ? '📁' : '📄'}
                              </div>
                              <div>
                                <div className="font-medium">{file.name}</div>
                                <div className="text-xs text-gray-400">{file.mime_type}</div>
                              </div>
                            </div>
                            <button
                              onClick={() => {
                                // In a full implementation, this would navigate to file details or download
                                alert(`Would open/download: ${file.name}`);
                              }}
                              className="text-sm text-blue-400 hover:text-blue-300"
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
                <p className="text-gray-400">Not connected to Google Drive. Click "Connect Google Drive" above to get started.</p>
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
        <p className="text-gray-300">Your unified storage pool is being set up.</p>
      </div>
    </div>
  );
};

export default Dashboard;
