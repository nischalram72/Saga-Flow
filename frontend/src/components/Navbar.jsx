import { useContext } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { AuthContext } from '../context/AuthContext';

export default function Navbar() {
  const { token, userRole, logout } = useContext(AuthContext);
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <nav className="bg-gray-800 text-white shadow-lg">
      <div className="max-w-7xl mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          <div className="flex space-x-4 items-center">
            <Link to="/" className="text-xl font-bold text-white hover:text-gray-300">
              SagaStore
            </Link>
            
            {token && (
              <>
                <Link to="/" className="px-3 py-2 rounded-md text-sm font-medium hover:bg-gray-700 hover:text-white transition-colors">
                  Dashboard
                </Link>
                {userRole === 'admin' && (
                  <Link to="/admin" className="px-3 py-2 rounded-md text-sm font-medium hover:bg-gray-700 hover:text-white transition-colors text-purple-400">
                    Admin
                  </Link>
                )}
              </>
            )}
          </div>
          
          <div className="flex space-x-4 items-center">
            {!token ? (
              <>
                <Link to="/login" className="px-3 py-2 rounded-md text-sm font-medium hover:bg-gray-700 transition-colors">
                  Login
                </Link>
                <Link to="/register" className="px-3 py-2 rounded-md text-sm font-medium bg-blue-600 hover:bg-blue-700 transition-colors">
                  Register
                </Link>
              </>
            ) : (
              <button 
                onClick={handleLogout}
                className="px-3 py-2 rounded-md text-sm font-medium bg-red-600 hover:bg-red-700 transition-colors"
              >
                Logout
              </button>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
}
