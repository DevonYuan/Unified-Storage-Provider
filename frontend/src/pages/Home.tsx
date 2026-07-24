import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Link } from 'react-router-dom';

const Home: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="container text-center py-12">
      <h1 className="text-4xl font-bold mb-4 text-white">Welcome to OmniDrive</h1>
      <p className="text-xl text-gray-300 mb-8">
        The unified cloud storage pool that aggregates all your free-tier personal cloud accounts.
      </p>
      <div className="flex justify-center gap-4">
        <Link
          to="/login"
          className="px-6 py-3 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
        >
          Log In
        </Link>
        <Link
          to="/register"
          className="px-6 py-3 border border-gray-600 text-gray-200 rounded-md hover:border-gray-500 hover:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
        >
          Sign Up
        </Link>
      </div>
    </div>
  );
};

export default Home;
