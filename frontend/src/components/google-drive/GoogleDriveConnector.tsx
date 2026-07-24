import React, { useState, useEffect } from 'react';
import { googleDriveService } from '../../api/googleDrive.service';
import Button from '@/components/ui/Button';

const GoogleDriveConnector: React.FC = () => {
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [debugInfo, setDebugInfo] = useState<string | null>(null);

  useEffect(() => {
    const checkConnectionStatus = async () => {
      console.log('[GoogleDriveConnector] Checking connection status');
      setDebugInfo('Checking connection...');
      try {
        await googleDriveService.getGoogleTokens();
        setIsConnected(true);
        setError(null);
        setDebugInfo('Successfully connected to Google Drive');
        console.log('[GoogleDriveConnector] User is connected to Google Drive');
      } catch (err: any) {
        setIsConnected(false);
        // Don't set error here as it might just mean not connected
        const errorMsg = err.response?.data?.detail || err.message || 'Unknown error';
        setDebugInfo(`Failed to connect: ${errorMsg}`);
        console.log('[GoogleDriveConnector] User is NOT connected to Google Drive:', errorMsg);
      }
    };

    checkConnectionStatus();
  }, []);

  const handleConnect = async () => {
    setIsConnecting(true);
    setError(null);
    setDebugInfo('Initiating Google Drive connection...');
    console.log('[GoogleDriveConnector] Initiating Google Drive connection');
    try {
      // Get OAuth URL from backend, no state needed
      const { auth_url } = await googleDriveService.getGoogleOAuthUrl();
      console.log('[GoogleDriveConnector] Got OAuth URL:', auth_url);
      setDebugInfo(`Got OAuth URL, redirecting to Google...`);
      // Redirect to Google OAuth page
      window.location.href = auth_url;
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || err.message || 'Failed to initiate connection';
      setError('Failed to initiate Google Drive connection');
      setDebugInfo(`Error: ${errorMsg}`);
      console.error('[GoogleDriveConnector] Failed to initiate Google Drive connection:', errorMsg);
    } finally {
      setIsConnecting(false);
    }
  };

  if (isConnecting) {
    return <Button variant="outline" disabled>Connecting...</Button>;
  }

  return (
    <div>
      {debugInfo && <p className="text-blue-500 text-sm">{debugInfo}</p>}
      {isConnected ? (
        <>
          <span className="text-green-600">Google Drive Connected</span>
          {/* In a full implementation, we might have a disconnect button here */}
        </>
      ) : (
        <>
          {error && <p className="text-red-500">{error}</p>}
          <Button onClick={handleConnect} variant="outline">
            Connect Google Drive
          </Button>
        </>
      )}
    </div>
  );
};

export default GoogleDriveConnector;