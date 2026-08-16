import { useContext } from 'react';
import { AuthContext } from '../context/AuthContext';

export default function Home() {
  const { userRole } = useContext(AuthContext);

  return (
    <div className="max-w-7xl mx-auto py-12 px-4 sm:px-6 lg:px-8">
      <div className="bg-white rounded-lg shadow px-5 py-6 sm:px-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-4">Welcome to the Dashboard</h1>
        <p className="text-gray-600 mb-8">
          You are successfully logged in! Your current role is: <span className="font-bold text-blue-600">{userRole}</span>
        </p>
        
        <div className="border-4 border-dashed border-gray-200 rounded-lg h-96 flex items-center justify-center">
          <p className="text-gray-400">Content goes here...</p>
        </div>
      </div>
    </div>
  );
}
