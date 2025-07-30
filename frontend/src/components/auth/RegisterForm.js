import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import * as yup from 'yup';
import TelegramLoginButton from 'react-telegram-login';
import { useAuth } from '../../contexts/AuthContext';
import { UserPlus, AlertCircle, Building, Bot, Check } from 'lucide-react';

const schema = yup.object({
  organizationName: yup.string().required('Organization name is required')
});

const TelegramRegister = ({ onSwitchToLogin }) => {
  const { telegramRegister } = useAuth();
  const [showOrgForm, setShowOrgForm] = useState(false);
  const [telegramData, setTelegramData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const {
    register,
    handleSubmit,
    formState: { errors }
  } = useForm({
    resolver: yupResolver(schema)
  });

  const handleTelegramResponse = (user) => {
    setTelegramData({
      id: user.id,
      first_name: user.first_name,
      last_name: user.last_name,
      username: user.username,
      photo_url: user.photo_url,
      auth_date: user.auth_date,
      hash: user.hash
    });
    setShowOrgForm(true);
    setError('');
  };

  const onSubmit = async (data) => {
    if (!telegramData) {
      setError('Please authenticate with Telegram first');
      return;
    }

    setIsLoading(true);
    setError('');

    const result = await telegramRegister({
      telegram_id: telegramData.id,
      username: telegramData.username,
      first_name: telegramData.first_name,
      last_name: telegramData.last_name,
      photo_url: telegramData.photo_url,
      organization_name: data.organizationName
    });
    
    if (!result.success) {
      setError(result.error);
    }
    
    setIsLoading(false);
  };

  const resetForm = () => {
    setShowOrgForm(false);
    setTelegramData(null);
    setError('');
  };

  // Get bot username from Telegram token
  const botName = 'Telewatch_test_bot'; // This should match your bot's username

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

          {!showOrgForm ? (
            // Step 1: Telegram Authentication
            <div className="bg-white p-6 rounded-lg shadow-md">
              <div className="text-center mb-6">
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  Step 1: Authenticate with Telegram
                </h3>
                <p className="text-sm text-gray-600">
                  First, we need to verify your Telegram account. Click the button below to continue.
                </p>
              </div>
              
              <div className="flex justify-center">
                <TelegramLoginButton
                  dataOnauth={handleTelegramResponse}
                  botName={botName}
                  buttonSize="large"
                  cornerRadius={8}
                  requestAccess="write"
                />
              </div>
              
              <div className="mt-4 text-xs text-gray-500 text-center">
                We use Telegram for secure authentication and seamless integration
              </div>
            </div>
          ) : (
            // Step 2: Organization Setup
            <div className="bg-white p-6 rounded-lg shadow-md">
              {/* Telegram User Info */}
              <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg">
                <div className="flex items-center gap-3 mb-2">
                  <Check className="h-5 w-5 text-green-600" />
                  <span className="font-medium text-green-900">Telegram Account Verified</span>
                </div>
                <div className="flex items-center gap-3">
                  {telegramData?.photo_url && (
                    <img 
                      src={telegramData.photo_url} 
                      alt="Profile" 
                      className="w-8 h-8 rounded-full"
                    />
                  )}
                  <div className="text-sm text-green-800">
                    <div className="font-medium">
                      {telegramData?.first_name} {telegramData?.last_name}
                    </div>
                    {telegramData?.username && (
                      <div className="text-green-600">@{telegramData.username}</div>
                    )}
                  </div>
                </div>
                <button
                  onClick={resetForm}
                  className="mt-2 text-xs text-green-700 hover:text-green-800 underline"
                >
                  Use different account
                </button>
              </div>

              {/* Organization Form */}
              <div className="text-center mb-6">
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  Step 2: Create Organization
                </h3>
                <p className="text-sm text-gray-600">
                  Set up your organization workspace for team collaboration.
                </p>
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
                  />
                  {errors.organizationName && (
                    <p className="mt-1 text-sm text-red-600">{errors.organizationName.message}</p>
                  )}
                  <p className="mt-1 text-xs text-gray-500">This will be your organization's workspace</p>
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

              <div className="mt-4 text-xs text-gray-500 text-center">
                By creating an account, you agree to our Terms of Service and Privacy Policy
              </div>
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
                  Why Telegram Authentication?
                </h3>
                <div className="mt-2 text-sm text-blue-700">
                  <ul className="list-disc pl-4 space-y-1">
                    <li>Secure and verified identity through Telegram</li>
                    <li>Seamless integration with bot monitoring features</li>
                    <li>No passwords to remember or manage</li>
                    <li>Quick setup for team collaboration</li>
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

export default TelegramRegister;