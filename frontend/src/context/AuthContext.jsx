import { createContext, useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

export const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [token, setToken] = useState(localStorage.getItem('token') || null);
  const [userRole, setUserRole] = useState(null);

  useEffect(() => {
    if (token) {
      try {
        // Simple JWT payload decoding (base64)
        const payloadBase64 = token.split('.')[1];
        if (payloadBase64) {
          const payloadJson = atob(payloadBase64);
          const payload = JSON.parse(payloadJson);
          // Assuming the token payload has a 'sub' or 'role' claim. 
          // Our backend includes user id in 'sub', but let's check if role is there.
          if (payload.role) {
            setUserRole(payload.role);
          } else {
            // Defaulting if not strictly present in JWT for now, can adjust
            setUserRole('customer');
          }
        }
      } catch (err) {
        console.error("Failed to parse JWT", err);
      }
    } else {
      setUserRole(null);
    }
  }, [token]);

  const login = (newToken) => {
    localStorage.setItem('token', newToken);
    setToken(newToken);
  };

  const logout = () => {
    localStorage.removeItem('token');
    setToken(null);
  };

  return (
    <AuthContext.Provider value={{ token, userRole, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};
