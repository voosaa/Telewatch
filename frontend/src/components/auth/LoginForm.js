import React, { useState } from 'react';
import TelegramLoginButton from 'react-telegram-login';
import { useAuth } from '../../contexts/AuthContext';
import { AlertCircle, Bot, LogIn } from 'lucide-react';

const TelegramLogin = ({ onSwitchToRegister }) => {
  const { telegramLogin } = useAuth();
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleTelegramResponse = async (user) => {
    setIsLoading(true);
    setError('');
    
    try {
      const result = await telegramLogin({
        id: user.id,
        first_name: user.first_name,
        last_name: user.last_name,
        username: user.username,
        photo_url: user.photo_url,
        auth_date: user.auth_date,
        hash: user.hash
      });
      
      if (!result.success) {
        if (result.error.includes('User not found')) {
          setError('Account not found. Please register first.');
        } else {
          setError(result.error);
        }
      }
    } catch (err) {
      setError('Authentication failed. Please try again.');
    }
    
    setIsLoading(false);
  };

  // Get bot username from Telegram token (8342094196:AAE-E8jIYLjYflUPtY0G02NLbogbDpN_FE8)
  const botName = 'Telewatch_test_bot'; // This should match your bot's username

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <div className="mx-auto h-12 w-12 flex items-center justify-center rounded-full bg-blue-600">
            <Bot className="h-6 w-6 text-white" />
          </div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
            Sign in with Telegram
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            Don't have an account?{' '}
            <button
              onClick={onSwitchToRegister}
              className="font-medium text-blue-600 hover:text-blue-500"
            >
              Sign up here
            </button>
          </p>
        </div>
        
        <div className="mt-8 space-y-6">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-lg flex items-center gap-2">
              <AlertCircle className="h-4 w-4" />
              {error}
            </div>
          )}

          <div className="bg-white p-6 rounded-lg shadow-md">
            <div className="text-center mb-6">
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                Authenticate with Telegram
              </h3>
              <p className="text-sm text-gray-600">
                Click the button below to sign in using your Telegram account.
                This is secure and we don't store your password.
              </p>
            </div>
            
            <div className="flex justify-center">
              {isLoading ? (
                <div className="flex items-center justify-center py-3 px-6 bg-gray-100 rounded-lg">
                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600 mr-2"></div>
                  <span className="text-gray-600">Authenticating...</span>
                </div>
              ) : (
                <TelegramLoginButton
                  dataOnauth={handleTelegramResponse}
                  botName={botName}
                  buttonSize="large"
                  cornerRadius={8}
                  requestAccess="write"
                />
              )}
            </div>
            
            <div className="mt-4 text-xs text-gray-500 text-center">
              By signing in, you agree to our Terms of Service and Privacy Policy
            </div>
          </div>

          <div className="bg-blue-50 p-4 rounded-lg">
            <div className="flex items-start">
              <div className="flex-shrink-0">
                <Bot className="h-5 w-5 text-blue-600" />
              </div>
              <div className="ml-3">
                <h3 className="text-sm font-medium text-blue-800">
                  Why Telegram Authentication?
                </h3>
                <div className="mt-2 text-sm text-blue-700">
                  <ul className="list-disc pl-4 space-y-1">
                    <li>Secure authentication using Telegram's infrastructure</li>
                    <li>No need to remember another password</li>
                    <li>Seamless integration with your Telegram bot monitoring</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TelegramLogin;