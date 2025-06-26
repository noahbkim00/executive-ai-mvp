import React from 'react';
import { Link } from 'react-router-dom';

const ResultsPage: React.FC = () => {
  return (
    <div className="text-center">
      <h1 className="text-4xl font-bold mb-8">Results Page</h1>
      <div className="mb-8">
        <div className="bg-surface p-4 rounded-lg mb-4 max-w-md mx-auto">
          <p className="text-secondary">Testing surface background and secondary text color</p>
        </div>
        <div className="bg-primary p-4 rounded-lg mb-4 max-w-md mx-auto">
          <p className="text-white">Testing primary background</p>
        </div>
      </div>
      <Link 
        to="/" 
        className="bg-secondary text-white px-6 py-3 rounded-lg hover:bg-secondary/90 transition-colors"
      >
        Back to Search
      </Link>
    </div>
  );
};

export default ResultsPage;