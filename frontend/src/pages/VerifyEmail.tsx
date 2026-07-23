import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { authService } from '../api/auth.service';

const VerifyEmail: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [message, setMessage] = useState('');

  const token = searchParams.get('token');

  useEffect(() => {
    if (!token) {
      setStatus('error');
      setMessage('No verification token provided.');
      return;
    }

    const verify = async () => {
      try {
        const result = await authService.verifyEmail(token);
        setStatus('success');
        setMessage(result.message);
      } catch (error: any) {
        setStatus('error');
        setMessage(error.response?.data?.detail || 'Verification failed');
      }
    };

    verify();
  }, [token]);

  const handleResend = async () => {
    const email = prompt('Enter your email to resend verification:');
    if (!email) return;
    try {
      await authService.resendVerification(email);
      alert('Verification email sent!');
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to resend verification');
    }
  };

  return (
    <div style={{ maxWidth: '400px', margin: '2rem auto', padding: '1rem' }}>
      <h2>Verify Email</h2>
      {status === 'loading' && <p>Verifying your email...</p>}
      {status === 'success' && (
        <div>
          <p style={{ color: 'green' }}>{message}</p>
          <button onClick={() => navigate('/login')}>Go to Login</button>
        </div>
      )}
      {status === 'error' && (
        <div>
          <p style={{ color: 'red' }}>{message}</p>
          <button onClick={handleResend} style={{ marginRight: '0.5rem' }}>Resend Verification</button>
          <button onClick={() => navigate('/login')}>Back to Login</button>
        </div>
      )}
    </div>
  );
};

export default VerifyEmail;
