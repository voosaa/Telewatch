import React, { useState, useEffect, useRef } from 'react';
import { useForm } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import * as yup from 'yup';
import { useAuth } from '../../contexts/AuthContext';
import { UserPlus, AlertCircle, Building, Bot, Check, ExternalLink, MessageCircle } from 'lucide-react';

const schema = yup.object({
  organizationName: yup.string().required('Organization name is required'),
  telegramId: yup.string().required('Telegram ID is required'),
  firstName: yup.string().required('First name is required'),
  username: yup.string()
});

const TelegramRegister = ({ onSwitchToLogin }) => {
  const { telegramRegister } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [showManualForm, setShowManualForm] = useState(false);
  const [telegramUser, setTelegramUser] = useState(null);
  const [widgetLoaded, setWidgetLoaded] = useState(false);
  const widgetRef = useRef(null);

  const {
    register,
    handleSubmit,
    formState: { errors }
  } = useForm({
    resolver: yupResolver(schema)
  });

  const botUsername = 'Telewatch_test_bot';
  const botUrl = `https://t.me/${botUsername}`;

  // Handle Telegram Login callback for registration
  const handleTelegramAuth = async (user) => {
    setTelegramUser(user);
    setError('');
    
    // Show organization form after Telegram auth
    setShowManualForm(true);
  };

  // Load Telegram Widget script and initialize
  useEffect(() => {
    // Make the callback function globally available with consistent naming
    window.onTelegramAuthRegister = handleTelegramAuth;
    
    // Also set up alternative callback name for compatibility  
    window.telegramRegisterCallback = handleTelegramAuth;

    // Load Telegram Widget script if not already loaded
    if (!document.getElementById('telegram-widget-script')) {
      const script = document.createElement('script');
      script.id = 'telegram-widget-script';
      script.src = 'https://telegram.org/js/telegram-widget.js?22';
      script.async = true;
      script.onerror = () => {
        setError('Failed to load Telegram authentication widget. Please refresh and try again.');
      };
      
      document.head.appendChild(script);
    }

    // Initialize widget after a short delay to ensure script is loaded
    const initTimer = setTimeout(() => {
      if (!showManualForm) {
        createTelegramWidget();
      }
    }, 1000);

    return () => {
      // Clean up
      clearTimeout(initTimer);
      if (window.onTelegramAuthRegister) {
        delete window.onTelegramAuthRegister;
      }
      if (window.telegramRegisterCallback) {
        delete window.telegramRegisterCallback;
      }
    };
  }, [showManualForm]);

  const initializeTelegramWidget = () => {
    if (widgetRef.current && window.TelegramLoginWidget) {
      // Clear any existing widget
      widgetRef.current.innerHTML = '';
      
      // Create the widget manually as a fallback
      const widget = document.createElement('script');
      widget.setAttribute('src', 'https://telegram.org/js/telegram-widget.js?22');
      widget.setAttribute('data-telegram-login', botUsername);
      widget.setAttribute('data-size', 'large');
      widget.setAttribute('data-auth-url', window.location.origin + '/telegram-auth-register');
      widget.setAttribute('data-request-access', 'write');
      widget.setAttribute('data-onauth', 'onTelegramAuthRegister(user)');
      
      widgetRef.current.appendChild(widget);
      setWidgetLoaded(true);
    }
  };

  // Handle manual widget creation as iframe
  const createTelegramWidget = () => {
    if (!widgetRef.current || widgetLoaded) return;

    const widget = document.createElement('iframe');
    widget.src = `https://oauth.telegram.org/auth?bot_id=8342094196&origin=${encodeURIComponent(window.location.origin)}&return_to=${encodeURIComponent(window.location.origin)}&embed=1&request_access=write`;
    widget.width = '100%';
    widget.height = '186';
    widget.frameBorder = '0';
    widget.scrolling = 'no';
    widget.style.border = 'none';
    widget.style.borderRadius = '8px';
    
    // Listen for messages from the iframe
    const handleMessage = (event) => {
      if (event.origin !== 'https://oauth.telegram.org') return;
      
      if (event.data && typeof event.data === 'object' && event.data.user) {
        handleTelegramAuth(event.data.user);
      }
    };
    
    window.addEventListener('message', handleMessage);
    
    widgetRef.current.appendChild(widget);
    setWidgetLoaded(true);
  };

  // Auto-create widget after component mounts
  useEffect(() => {
    const timer = setTimeout(() => {
      if (!widgetLoaded && !showManualForm) {
        createTelegramWidget();
      }
    }, 2000);

    return () => clearTimeout(timer);
  }, [widgetLoaded, showManualForm]);

  const onSubmit = async (data) => {
    setIsLoading(true);
    setError('');

    let registrationData;

    if (telegramUser) {
      // Registration via Telegram Login Widget
      registrationData = {
        telegram_id: telegramUser.id,
        username: telegramUser.username || null,
        first_name: telegramUser.first_name,
        last_name: telegramUser.last_name || null,
        photo_url: telegramUser.photo_url || null,
        organization_name: data.organizationName
      };
    } else {
      // Manual registration
      const telegramId = parseInt(data.telegramId);
      if (isNaN(telegramId)) {
        setError('Telegram ID must be a number');
        setIsLoading(false);
        return;
      }

      registrationData = {
        telegram_id: telegramId,
        username: data.username || null,
        first_name: data.firstName,
        last_name: data.lastName || null,
        photo_url: null,
        organization_name: data.organizationName
      };
    }

    const result = await telegramRegister(registrationData);
    
    if (!result.success) {
      setError(result.error);
    }
    
    setIsLoading(false);
  };

  const handleGetTelegramId = () => {
    setError('To get your Telegram ID, send /start to our bot and it will display your user information.');
  };

  const resetForm = () => {
    setTelegramUser(null);
    setShowManualForm(false);
    setError('');
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <div className="mx-auto h-12 w-12 flex items-center justify-center rounded-full bg-green-600">
            <UserPlus className="h-6 w-6 text-white" />
          </div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
            Create your account
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            Already have an account?{' '}
            <button
              onClick={onSwitchToLogin}
              className="font-medium text-blue-600 hover:text-blue-500"
            >
              Sign in here
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

          {!showManualForm ? (
            // Registration Options with Telegram Widget
            <div className="bg-white p-6 rounded-lg shadow-md">
              <div className="text-center mb-6">
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  Quick Registration with Telegram
                </h3>
                <p className="text-sm text-gray-600">
                  Use your Telegram account to create your organization account.
                </p>
              </div>
              
              {/* Telegram Login Widget */}
              <div className="mb-6">
                <div ref={widgetRef} className="flex justify-center">
                  {!widgetLoaded && (
                    <div className="flex flex-col items-center space-y-3">
                      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-600"></div>
                      <p className="text-sm text-gray-600">Loading Telegram Registration Widget...</p>
                      <button
                        onClick={createTelegramWidget}
                        className="text-green-600 hover:text-green-700 underline text-sm"
                      >
                        Click here if widget doesn't load
                      </button>
                    </div>
                  )}
                </div>
              </div>

              <div className="border-t pt-4">
                <div className="text-center text-sm text-gray-600 mb-4">
                  Alternative Options
                </div>
                
                <div className="space-y-3">
                  {/* Bot Registration Option */}
                  <div className="border border-gray-200 rounded-lg p-3">
                    <div className="flex items-center gap-2 mb-2">
                      <MessageCircle className="h-4 w-4 text-blue-600" />
                      <h4 className="font-medium text-gray-900 text-sm">Register via Telegram Bot</h4>
                    </div>
                    <p className="text-xs text-gray-600 mb-2">
                      Let our bot guide you through the registration process.
                    </p>
                    <a
                      href={botUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 px-3 py-1 bg-blue-600 text-white rounded text-xs hover:bg-blue-700 transition-colors"
                    >
                      <ExternalLink className="h-3 w-3" />
                      Open @{botUsername}
                    </a>
                  </div>
                  
                  {/* Manual Registration Option */}
                  <div className="border border-gray-200 rounded-lg p-3">
                    <div className="flex items-center gap-2 mb-2">
                      <UserPlus className="h-4 w-4 text-green-600" />
                      <h4 className="font-medium text-gray-900 text-sm">Manual Registration</h4>
                    </div>
                    <p className="text-xs text-gray-600 mb-2">
                      Fill out the registration form manually.
                    </p>
                    <button
                      onClick={() => setShowManualForm(true)}
                      className="inline-flex items-center gap-1 px-3 py-1 bg-green-600 text-white rounded text-xs hover:bg-green-700 transition-colors"
                    >
                      Continue with Manual Form
                    </button>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            // Manual Registration Form or Organization Setup
            <div className="bg-white p-6 rounded-lg shadow-md">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-lg font-medium text-gray-900">
                  {telegramUser ? 'Complete Your Registration' : 'Manual Registration'}
                </h3>
                <button
                  onClick={resetForm}
                  className="text-sm text-gray-600 hover:text-gray-800"
                >
                  ← Back to options
                </button>
              </div>

              {telegramUser && (
                <div className="bg-green-50 border border-green-200 p-4 rounded-lg mb-6">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-green-600 rounded-full flex items-center justify-center text-white font-semibold">
                      {telegramUser.first_name.charAt(0)}
                    </div>
                    <div>
                      <div className="font-medium text-green-900">
                        {telegramUser.first_name} {telegramUser.last_name}
                      </div>
                      {telegramUser.username && (
                        <div className="text-sm text-green-700">@{telegramUser.username}</div>
                      )}
                    </div>
                  </div>
                  <p className="text-sm text-green-700 mt-2">
                    ✅ Telegram account verified! Just provide your organization details below.
                  </p>
                </div>
              )}

              <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
                <div>
                  <label htmlFor="organizationName" className="block text-sm font-medium text-gray-700">
                    <Building className="h-4 w-4 inline mr-1" />
                    Organization Name
                  </label>
                  <input
                    {...register('organizationName')}
                    type="text"
                    className="mt-1 appearance-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-lg focus:outline-none focus:ring-green-500 focus:border-green-500 focus:z-10 sm:text-sm"
                    placeholder="Enter your organization name"
                    disabled={isLoading}
                  />
                  {errors.organizationName && (
                    <p className="mt-1 text-sm text-red-600">{errors.organizationName.message}</p>
                  )}
                </div>

                {!telegramUser && (
                  <>
                    <div>
                      <label htmlFor="telegramId" className="block text-sm font-medium text-gray-700">
                        Telegram ID *
                      </label>
                      <input
                        {...register('telegramId')}
                        type="text"
                        className="mt-1 appearance-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-lg focus:outline-none focus:ring-green-500 focus:border-green-500 focus:z-10 sm:text-sm"
                        placeholder="Your Telegram user ID (numbers only)"
                        disabled={isLoading}
                      />
                      {errors.telegramId && (
                        <p className="mt-1 text-sm text-red-600">{errors.telegramId.message}</p>
                      )}
                      <div className="mt-1 text-xs text-gray-500">
                        Don't know your ID?{' '}
                        <button
                          type="button"
                          onClick={handleGetTelegramId}
                          className="text-blue-600 hover:text-blue-700 underline"
                        >
                          Get help
                        </button>
                      </div>
                    </div>

                    <div>
                      <label htmlFor="firstName" className="block text-sm font-medium text-gray-700">
                        First Name
                      </label>
                      <input
                        {...register('firstName')}
                        type="text"
                        className="mt-1 appearance-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-lg focus:outline-none focus:ring-green-500 focus:border-green-500 focus:z-10 sm:text-sm"
                        placeholder="Your first name"
                        disabled={isLoading}
                      />
                      {errors.firstName && (
                        <p className="mt-1 text-sm text-red-600">{errors.firstName.message}</p>
                      )}
                    </div>

                    <div>
                      <label htmlFor="lastName" className="block text-sm font-medium text-gray-700">
                        Last Name (Optional)
                      </label>
                      <input
                        {...register('lastName')}
                        type="text"
                        className="mt-1 appearance-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-lg focus:outline-none focus:ring-green-500 focus:border-green-500 focus:z-10 sm:text-sm"
                        placeholder="Your last name"
                        disabled={isLoading}
                      />
                    </div>

                    <div>
                      <label htmlFor="username" className="block text-sm font-medium text-gray-700">
                        Telegram Username (Optional)
                      </label>
                      <input
                        {...register('username')}
                        type="text"
                        className="mt-1 appearance-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-lg focus:outline-none focus:ring-green-500 focus:border-green-500 focus:z-10 sm:text-sm"
                        placeholder="@username (without @)"
                        disabled={isLoading}
                      />
                    </div>
                  </>
                )}

                <button
                  type="submit"
                  disabled={isLoading}
                  className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-lg text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isLoading ? (
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  ) : (
                    'Create Account'
                  )}
                </button>
              </form>
            </div>
          )}

          {/* Info Section */}
          <div className="bg-blue-50 p-4 rounded-lg">
            <div className="flex items-start">
              <div className="flex-shrink-0">
                <Bot className="h-5 w-5 text-blue-600" />
              </div>
              <div className="ml-3">
                <h3 className="text-sm font-medium text-blue-800">
                  Getting Started Steps
                </h3>
                <div className="mt-2 text-sm text-blue-700">
                  <ol className="list-decimal pl-4 space-y-1">
                    <li>Create your account (via Telegram widget, bot, or manual form)</li>
                    <li>Upload your Telegram session + JSON files</li>
                    <li>Activate accounts for monitoring</li>
                    <li>Configure groups and watchlists</li>
                    <li>Start monitoring with stealth user accounts</li>
                  </ol>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TelegramRegister;