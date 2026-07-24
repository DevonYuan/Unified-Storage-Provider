import React, { useState, useEffect } from 'react';
import { googleDriveService } from '../../api/googleDrive.service';
import Button from '@/components/ui/Button';

const GoogleDriveConnector: React.FC = () => {
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const checkConnectionStatus = async () => {
      try {
        await googleDriveService.getGoogleTokens();
        setIsConnected(true);
        setError(null);
      } catch (err: any) {
        setIsConnected(false);
        // Don't set error here as it might just mean not connected
      }
    };

    checkConnectionStatus();
  }, []);

  const handleConnect = async () => {
    setIsConnecting(true);
    setError(null);
    try {
      // Get OAuth URL from backend
      const { auth_url } = await googleDriveService.getGoogleOAuthUrl();
      // Redirect to Google OAuth page
      window.location.href = auth_url;
    } catch (err: any) {
      setError('Failed to initiate Google Drive connection');
      console.error(err);
    } finally {
      setIsConnecting(false);
    }
  };

  if (isConnecting) {
    return <Button variant="outline" disabled>Connecting...</Button>;
  }

  return (
    <div>
      {isConnected ? (
        <>
          <span>Google Drive Connected</span>
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