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
      setMessage(error.response?.data?.error.response?.data?.detail || 'Password reset failed');
    }
  };

  return (
    <div className="auth-container">
      <h2>Reset Password</h2>

      {status === 'error' && !password && (
        <div>
          <p className="error-message">{message}</p>
          <button onClick={() => navigate('/login')} className="btn-secondary">Back to Login</button>
        </div>
      )}

      {status === 'success' && (
<div>
          <p className="success' ? (
        <div>
          <p className="success-message">{message}</p>
          <button onClick={() => navigate('/login')} className="btn-primary">Go to Login</button>
        </div>
      ) : (
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="password">New Password:</label>
            <input
              type="password"
              id="password"
              className="form-input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="confirmPassword">Confirm Password:</label>
            <input
              type="password"
              id="confirmPassword"
              className="form-input"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
            />
          </div>

          {status === 'error' && password && (
            <p className="error-message">{message}</p>
          )}

          <button
            type="submit"
            disabled={status === 'loading'}
            className={`btn-primary w-full ${status === 'loading' ? 'opacity-50' : ''}`}
          >
            {status === 'loading' ? 'Resetting...' : 'Reset Password'}
          </button>
        </form>
      )}
    </div>
  );
};

export default ResetPassword;
