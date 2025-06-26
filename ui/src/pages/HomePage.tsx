import React from 'react';
import { Link } from 'react-router-dom';

const HomePage: React.FC = () => {
  return (
    <div className="text-center">
      <h1 className="text-4xl font-bold mb-8">Search Page</h1>
      <Link 
        to="/results" 
        className="bg-primary text-white px-6 py-3 rounded-lg hover:bg-primary/90 transition-colors"
      >
        Go to Results
      </Link>
    </div>
  );
};

export default HomePage;