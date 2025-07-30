import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { AlertCircle, Bot, ExternalLink, MessageCircle } from 'lucide-react';

const TelegramLogin = ({ onSwitchToRegister }) => {
  const { telegramLogin } = useAuth();
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showInstructions, setShowInstructions] = useState(false);
  const [widgetLoaded, setWidgetLoaded] = useState(false);
  const widgetRef = useRef(null);

  const botUsername = 'Telewatch_test_bot';
  const botUrl = `https://t.me/${botUsername}`;

  // Handle Telegram Login callback
  const handleTelegramAuth = async (user) => {
    setIsLoading(true);
    setError('');
    
    try {
      const result = await telegramLogin(user);
      
      if (!result.success) {
        setError(result.error);
      }
    } catch (err) {
      setError('Failed to authenticate with Telegram. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  // Load Telegram Widget script and initialize
  useEffect(() => {
    // Make the callback function globally available
    window.onTelegramAuth = handleTelegramAuth;

    // Check if script is already loaded
    if (document.getElementById('telegram-widget-script')) {
      initializeTelegramWidget();
      return;
    }

    // Load Telegram Widget script
    const script = document.createElement('script');
    script.id = 'telegram-widget-script';
    script.src = 'https://telegram.org/js/telegram-widget.js?22';
    script.async = true;
    script.onload = () => {
      initializeTelegramWidget();
    };
    script.onerror = () => {
      setError('Failed to load Telegram authentication widget. Please refresh and try again.');
    };
    
    document.head.appendChild(script);

    return () => {
      // Clean up global callback
      if (window.onTelegramAuth) {
        delete window.onTelegramAuth;
      }
    };
  }, []);

  const initializeTelegramWidget = () => {
    if (widgetRef.current && window.TelegramLoginWidget) {
      // Clear any existing widget
      widgetRef.current.innerHTML = '';
      
      // Create the widget manually as a fallback
      const widget = document.createElement('script');
      widget.setAttribute('src', 'https://telegram.org/js/telegram-widget.js?22');
      widget.setAttribute('data-telegram-login', botUsername);
      widget.setAttribute('data-size', 'large');
      widget.setAttribute('data-auth-url', window.location.origin + '/telegram-auth');
      widget.setAttribute('data-request-access', 'write');
      widget.setAttribute('data-onauth', 'onTelegramAuth(user)');
      
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
      if (!widgetLoaded) {
        createTelegramWidget();
      }
    }, 2000);

    return () => clearTimeout(timer);
  }, [widgetLoaded]);

  const handleBotLogin = async () => {
    setError('For development purposes, please use the registration flow or contact support for access.');
    setShowInstructions(true);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <div className="mx-auto h-12 w-12 flex items-center justify-center rounded-full bg-blue-600">
            <Bot className="h-6 w-6 text-white" />
          </div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
            Welcome to Telegram Monitor
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            Multi-Account Session Monitoring System
          </p>
          <p className="mt-1 text-center text-sm text-gray-600">
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

          {isLoading && (
            <div className="bg-blue-50 border border-blue-200 text-blue-800 px-4 py-3 rounded-lg flex items-center gap-2">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
              Authenticating with Telegram...
            </div>
          )}

          <div className="bg-white p-6 rounded-lg shadow-md">
            <div className="text-center mb-6">
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                Sign in with Telegram
              </h3>
              <p className="text-sm text-gray-600">
                Use your Telegram account to access the monitoring system.
              </p>
            </div>
            
            {/* Telegram Login Widget */}
            <div className="mb-6">
              <div ref={widgetRef} className="flex justify-center">
                {!widgetLoaded && (
                  <div className="flex flex-col items-center space-y-3">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                    <p className="text-sm text-gray-600">Loading Telegram Login Widget...</p>
                    <button
                      onClick={createTelegramWidget}
                      className="text-blue-600 hover:text-blue-700 underline text-sm"
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
                {/* Telegram Bot Option */}
                <div className="border border-gray-200 rounded-lg p-3">
                  <div className="flex items-center gap-2 mb-2">
                    <MessageCircle className="h-4 w-4 text-blue-600" />
                    <h4 className="font-medium text-gray-900 text-sm">Via Telegram Bot</h4>
                  </div>
                  <p className="text-xs text-gray-600 mb-2">
                    Interact directly through our Telegram bot.
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
                
                {/* Web Registration Option */}
                <div className="border border-gray-200 rounded-lg p-3">
                  <div className="flex items-center gap-2 mb-2">
                    <Bot className="h-4 w-4 text-green-600" />
                    <h4 className="font-medium text-gray-900 text-sm">Register for Web Access</h4>
                  </div>
                  <p className="text-xs text-gray-600 mb-2">
                    Create an account manually.
                  </p>
                  <button
                    onClick={onSwitchToRegister}
                    className="inline-flex items-center gap-1 px-3 py-1 bg-green-600 text-white rounded text-xs hover:bg-green-700 transition-colors"
                  >
                    Create Account
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* System Features */}
          <div className="bg-blue-50 p-4 rounded-lg">
            <div className="flex items-start">
              <div className="flex-shrink-0">
                <Bot className="h-5 w-5 text-blue-600" />
              </div>
              <div className="ml-3">
                <h3 className="text-sm font-medium text-blue-800">
                  System Features
                </h3>
                <div className="mt-2 text-sm text-blue-700">
                  <ul className="list-disc pl-4 space-y-1">
                    <li>Multi-account session-based monitoring</li>
                    <li>Stealth group monitoring without bot detection</li>
                    <li>Advanced message filtering and forwarding</li>
                    <li>Real-time analytics and health monitoring</li>
                    <li>Professional web dashboard and Telegram bot interface</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>

          {showInstructions && (
            <div className="bg-yellow-50 border border-yellow-200 p-4 rounded-lg">
              <h4 className="font-medium text-yellow-900 mb-2">Getting Started Instructions</h4>
              <div className="text-sm text-yellow-800 space-y-2">
                <p><strong>Option 1 - Telegram Login Widget:</strong></p>
                <ol className="list-decimal pl-4 space-y-1">
                  <li>Click the "Log in with Telegram" button above</li>
                  <li>Authorize the application in Telegram</li>
                  <li>You'll be automatically logged in</li>
                </ol>
                <p><strong>Option 2 - Telegram Bot:</strong></p>
                <ol className="list-decimal pl-4 space-y-1">
                  <li>Click "Open @{botUsername}" above</li>
                  <li>Send /start to the bot</li>
                  <li>Follow the bot's instructions</li>
                </ol>
                <p><strong>Option 3 - Web Registration:</strong></p>
                <ol className="list-decimal pl-4 space-y-1">
                  <li>Click "Create Account" above</li>
                  <li>Follow the registration process</li>
                  <li>Upload your account session files</li>
                </ol>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default TelegramLogin;