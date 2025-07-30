import React, { useState } from 'react';
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

  const {
    register,
    handleSubmit,
    formState: { errors }
  } = useForm({
    resolver: yupResolver(schema)
  });

  const botUsername = 'Telewatch_test_bot';
  const botUrl = `https://t.me/${botUsername}`;

  const onSubmit = async (data) => {
    setIsLoading(true);
    setError('');

    // Convert telegram_id to number
    const telegramId = parseInt(data.telegramId);
    if (isNaN(telegramId)) {
      setError('Telegram ID must be a number');
      setIsLoading(false);
      return;
    }

    const result = await telegramRegister({
      telegram_id: telegramId,
      username: data.username || null,
      first_name: data.firstName,
      last_name: data.lastName || null,
      photo_url: null,
      organization_name: data.organizationName
    });
    
    if (!result.success) {
      setError(result.error);
    }
    
    setIsLoading(false);
  };

  const handleGetTelegramId = () => {
    setError('To get your Telegram ID, send /start to our bot and it will display your user information.');
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
            // Registration Options
            <div className="bg-white p-6 rounded-lg shadow-md">
              <div className="text-center mb-6">
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  Registration Options
                </h3>
                <p className="text-sm text-gray-600">
                  Choose how you'd like to create your account.
                </p>
              </div>
              
              <div className="space-y-4">
                {/* Bot Registration Option */}
                <div className="border border-gray-200 rounded-lg p-4">
                  <div className="flex items-center gap-3 mb-3">
                    <MessageCircle className="h-5 w-5 text-blue-600" />
                    <h4 className="font-medium text-gray-900">Register via Telegram Bot</h4>
                  </div>
                  <p className="text-sm text-gray-600 mb-3">
                    The easiest way - let our bot guide you through the registration process.
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
                
                {/* Manual Registration Option */}
                <div className="border border-gray-200 rounded-lg p-4">
                  <div className="flex items-center gap-3 mb-3">
                    <UserPlus className="h-5 w-5 text-green-600" />
                    <h4 className="font-medium text-gray-900">Manual Registration</h4>
                  </div>
                  <p className="text-sm text-gray-600 mb-3">
                    Fill out the registration form manually if you prefer.
                  </p>
                  <button
                    onClick={() => setShowManualForm(true)}
                    className="inline-flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors text-sm"
                  >
                    Continue with Manual Form
                  </button>
                </div>
              </div>
            </div>
          ) : (
            // Manual Registration Form
            <div className="bg-white p-6 rounded-lg shadow-md">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-lg font-medium text-gray-900">
                  Manual Registration
                </h3>
                <button
                  onClick={() => setShowManualForm(false)}
                  className="text-sm text-gray-600 hover:text-gray-800"
                >
                  ← Back to options
                </button>
              </div>

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
                    <li>Create your account (via bot or manual form)</li>
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