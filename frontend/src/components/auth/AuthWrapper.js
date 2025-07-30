import React, { useState } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import TelegramLogin from './LoginForm';
import TelegramRegister from './RegisterForm';

const AuthWrapper = ({ children }) => {
  const { user, loading } = useAuth();
  const [isLogin, setIsLogin] = useState(true);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-2 text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return isLogin ? (
      <TelegramLogin onSwitchToRegister={() => setIsLogin(false)} />
    ) : (
      <TelegramRegister onSwitchToLogin={() => setIsLogin(true)} />
    );
  }

  return children;
};

export default AuthWrapper;