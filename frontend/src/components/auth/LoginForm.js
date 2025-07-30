import React, { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { AlertCircle, Bot, ExternalLink, MessageCircle } from 'lucide-react';

const TelegramLogin = ({ onSwitchToRegister }) => {
  const { telegramLogin } = useAuth();
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showInstructions, setShowInstructions] = useState(false);

  const botUsername = 'Telewatch_test_bot';
  const botUrl = `https://t.me/${botUsername}`;

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

          <div className="bg-white p-6 rounded-lg shadow-md">
            <div className="text-center mb-6">
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                Authentication Options
              </h3>
              <p className="text-sm text-gray-600">
                Choose how you'd like to access the monitoring system.
              </p>
            </div>
            
            <div className="space-y-4">
              {/* Telegram Bot Option */}
              <div className="border border-gray-200 rounded-lg p-4">
                <div className="flex items-center gap-3 mb-3">
                  <MessageCircle className="h-5 w-5 text-blue-600" />
                  <h4 className="font-medium text-gray-900">Via Telegram Bot</h4>
                </div>
                <p className="text-sm text-gray-600 mb-3">
                  Interact with the monitoring system directly through our Telegram bot.
                </p>
                <a
                  href={botUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm"
                >
                  <ExternalLink className="h-4 w-4" />
                  Open @{botUsername}
                </a>
              </div>
              
              {/* Web Interface Option */}
              <div className="border border-gray-200 rounded-lg p-4">
                <div className="flex items-center gap-3 mb-3">
                  <Bot className="h-5 w-5 text-green-600" />
                  <h4 className="font-medium text-gray-900">Register for Web Access</h4>
                </div>
                <p className="text-sm text-gray-600 mb-3">
                  Create an account to access the full web dashboard with all monitoring features.
                </p>
                <button
                  onClick={onSwitchToRegister}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors text-sm"
                >
                  Create Account
                </button>
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
                <p><strong>Option 1 - Telegram Bot:</strong></p>
                <ol className="list-decimal pl-4 space-y-1">
                  <li>Click "Open @{botUsername}" above</li>
                  <li>Send /start to the bot</li>
                  <li>Follow the bot's instructions</li>
                </ol>
                <p><strong>Option 2 - Web Registration:</strong></p>
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