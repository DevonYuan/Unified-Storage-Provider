import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { authService } from '../api/auth.service';

const ResetPassword: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('loading');
  const [message, setMessage] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  const token = searchParams.get('token');

  useEffect(() => {
    if (!token) {
      setStatus('error');
      setMessage('No reset token provided.');
      return;
    }
    setStatus('idle');
  }, [token]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (password !== confirmPassword) {
      setStatus('error');
      setMessage('Passwords do not match.');
      return;
    }

    if (password.length < 8) {
      setStatus('error');
      setMessage('Password must be at least 8 characters.');
      return;
    }

    setStatus('loading');
    
    try {
      const result = await authService.resetPassword(token, password);
      setStatus('success');
      setMessage(result.message);
    } catch (error: any) {
      setStatus('error');
      setMessage(error.response?.data?.detail || 'Password reset failed');
    }
  };

  return (
    <div style={{ maxWidth: '400px', margin: '2rem auto', padding: '1rem' }}>
      <h2>Reset Password</h2>
      
      {status === 'error' && !password && (
        <div>
          <p style={{ color: 'red' }}>{message}</p>
          <button onClick={() => navigate('/login')}>Back to Login</button>
        </div>
      )}
      
      {status === 'success' ? (
        <div>
          <p style={{ color: 'green' }}>{message}</p>
          <button onClick={() => navigate('/login')}>Go to Login</button>
        </div>
      ) : (
        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: '1rem' }}>
            <label htmlFor="password">New Password:</label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              style={{ width: '100%', padding: '0.5rem', marginTop: '0.25rem' }}
            />
          </div>
          
          <div style={{ marginBottom: '1rem' }}>
            <label htmlFor="confirmPassword">Confirm Password:</label>
            <input
              type="password"
              id="confirmPassword"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              style={{ width: '100%', padding: '0.5rem', marginTop: '0.25rem' }}
            />
          </div>
          
          {status === 'error' && password && (
            <p style={{ color: 'red', marginBottom: '1rem' }}>{message}</p>
          )}
          
          <button 
            type="submit" 
            disabled={status === 'loading'}
            style={{ width: '100%', padding: '0.5rem' }}
          >
            {status === 'loading' ? 'Resetting...' : 'Reset Password'}
          </button>
        </form>
      )}
    </div>
  );
};

export default ResetPassword;
