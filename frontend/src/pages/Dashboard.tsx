import React from 'react';
import { useAuth } from '../context/AuthContext';

const Dashboard: React.FC = () => {
  const { user } = useAuth();

  return (
    <div style={{ maxWidth: '800px', margin: '2rem auto', padding: '1rem' }}>
      <h2>Dashboard</h2>
      <p>Welcome, {user?.email}!</p>
      <p>Your unified storage pool is being set up.</p>
    </div>
  );
};

export default Dashboard;
