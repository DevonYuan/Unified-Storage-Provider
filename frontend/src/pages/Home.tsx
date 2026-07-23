import React from 'react';
import { useNavigate } from 'react-router-dom';

const Home: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div style={{ maxWidth: '800px', margin: '4rem auto', textAlign: 'center', fontFamily: 'sans-serif' }}>
      <h1 style={{ fontSize: '3rem', marginBottom: '1rem' }}>Welcome to OmniDrive</h1>
      <p style={{ fontSize: '1.2rem', color: '#555', marginBottom: '2rem' }}>
        The unified cloud storage pool that aggregates all your free-tier personal cloud accounts.
      </p>
      <div style={{ display: 'flex', justifyContent: 'center', gap: '1rem' }}>
        <button 
          onClick={() => navigate('/login')}
          style={{ padding: '0.8rem 1.5rem', fontSize: '1rem', cursor: 'pointer', backgroundColor: '#007bff', color: 'white', border: 'none', borderRadius: '4px' }}
        >
          Log In
        </button>
        <button 
          onClick={() => navigate('/register')}
          style={{ padding: '0.8rem 1.5rem', fontSize: '1rem', cursor: 'pointer', backgroundColor: '#f8f9fa', color: '#333', border: '1px solid #ccc', borderRadius: '4px' }}
        >
          Sign Up
        </button>
      </div>
    </div>
  );
};

export default Home;
