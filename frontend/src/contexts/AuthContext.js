import React, { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';

const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [organization, setOrganization] = useState(null);
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState(localStorage.getItem('authToken'));

  // Setup axios interceptor for authentication
  useEffect(() => {
    const interceptor = axios.interceptors.request.use(
      (config) => {
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Response interceptor for handling 401s
    const responseInterceptor = axios.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          logout();
        }
        return Promise.reject(error);
      }
    );

    return () => {
      axios.interceptors.request.eject(interceptor);
      axios.interceptors.response.eject(responseInterceptor);
    };
  }, [token]);

  // Check if user is logged in on app load
  useEffect(() => {
    const checkAuth = async () => {
      if (token) {
        try {
          const response = await axios.get(`${API}/auth/me`);
          setUser(response.data);
          await fetchOrganization();
        } catch (error) {
          console.error('Auth check failed:', error);
          logout();
        }
      }
      setLoading(false);
    };

    checkAuth();
  }, [token]);

  const fetchOrganization = async () => {
    try {
      const response = await axios.get(`${API}/organizations/current`);
      setOrganization(response.data);
    } catch (error) {
      console.error('Failed to fetch organization:', error);
    }
  };

  const telegramLogin = async (telegramData) => {
    try {
      const response = await axios.post(`${API}/auth/telegram`, telegramData);
      const { access_token, user: userData } = response.data;
      
      setToken(access_token);
      setUser(userData);
      localStorage.setItem('authToken', access_token);
      
      await fetchOrganization();
      
      return { success: true };
    } catch (error) {
      console.error('Telegram login failed:', error);
      return { 
        success: false, 
        error: error.response?.data?.detail || 'Telegram authentication failed' 
      };
    }
  };

  const telegramRegister = async (userData) => {
    try {
      const response = await axios.post(`${API}/auth/register`, userData);
      const { access_token, user: responseUserData } = response.data;
      
      setToken(access_token);
      setUser(responseUserData);
      localStorage.setItem('authToken', access_token);
      
      await fetchOrganization();
      
      return { success: true };
    } catch (error) {
      console.error('Telegram registration failed:', error);
      return { 
        success: false, 
        error: error.response?.data?.detail || 'Registration failed' 
      };
    }
  };

  const login = async (email, password) => {
    // Legacy method - deprecated for Telegram auth
    try {
      const response = await axios.post(`${API}/auth/login`, { email, password });
      return { 
        success: false, 
        error: 'Email/password login has been replaced with Telegram authentication' 
      };
    } catch (error) {
      return { 
        success: false, 
        error: 'Email/password login has been replaced with Telegram authentication' 
      };
    }
  };

  const register = async (email, password, fullName, organizationName) => {
    // Legacy method - deprecated for Telegram auth  
    return { 
      success: false, 
      error: 'Email/password registration has been replaced with Telegram authentication' 
    };
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    setOrganization(null);
    localStorage.removeItem('authToken');
  };

  const updateUser = (userData) => {
    setUser(userData);
  };

  const updateOrganization = (orgData) => {
    setOrganization(orgData);
  };

  const hasRole = (requiredRoles) => {
    if (!user) return false;
    if (Array.isArray(requiredRoles)) {
      return requiredRoles.includes(user.role);
    }
    return user.role === requiredRoles;
  };

  const isOwner = () => hasRole('owner');
  const isAdmin = () => hasRole(['owner', 'admin']);
  const canView = () => hasRole(['owner', 'admin', 'viewer']);

  const value = {
    user,
    organization,
    loading,
    token,
    login,
    register,
    telegramLogin,
    telegramRegister,
    logout,
    updateUser,
    updateOrganization,
    fetchOrganization,
    hasRole,
    isOwner,
    isAdmin,
    canView,
    isAuthenticated: () => !!user
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};