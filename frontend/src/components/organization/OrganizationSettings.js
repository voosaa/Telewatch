import React, { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { useForm } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import * as yup from 'yup';
import axios from 'axios';
import { Building, Save, RefreshCw, AlertCircle } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const schema = yup.object({
  name: yup.string().required('Organization name is required'),
  description: yup.string(),
  plan: yup.string().oneOf(['free', 'pro', 'enterprise']).required()
});

const OrganizationSettings = () => {
  const { organization, updateOrganization, isAdmin } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset
  } = useForm({
    resolver: yupResolver(schema),
    defaultValues: {
      name: organization?.name || '',
      description: organization?.description || '',
      plan: organization?.plan || 'free'
    }
  });

  useEffect(() => {
    if (organization) {
      reset({
        name: organization.name,
        description: organization.description || '',
        plan: organization.plan
      });
    }
  }, [organization, reset]);

  const onSubmit = async (data) => {
    if (!isAdmin()) {
      setMessage({ type: 'error', text: 'You do not have permission to update organization settings' });
      return;
    }

    setIsLoading(true);
    setMessage({ type: '', text: '' });

    try {
      const response = await axios.put(`${API}/organizations/current`, data);
      updateOrganization(response.data);
      setMessage({ type: 'success', text: 'Organization settings updated successfully!' });
    } catch (error) {
      console.error('Error updating organization:', error);
      setMessage({ 
        type: 'error', 
        text: error.response?.data?.detail || 'Failed to update organization settings' 
      });
    } finally {
      setIsLoading(false);
    }
  };

  const planOptions = [
    { value: 'free', label: 'Free Plan', description: 'Basic features for small teams' },
    { value: 'pro', label: 'Pro Plan', description: 'Advanced features for growing teams' },
    { value: 'enterprise', label: 'Enterprise Plan', description: 'Full features for large organizations' }
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Building className="h-8 w-8 text-blue-600" />
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Organization Settings</h1>
          <p className="text-gray-600">Manage your organization's configuration and preferences</p>
        </div>
      </div>

      {message.text && (
        <div className={`px-4 py-3 rounded-lg flex items-center gap-2 ${
          message.type === 'success' 
            ? 'bg-green-50 border border-green-200 text-green-800' 
            : 'bg-red-50 border border-red-200 text-red-800'
        }`}>
          <AlertCircle className="h-4 w-4" />
          {message.text}
        </div>
      )}

      <div className="bg-white rounded-lg shadow-md">
        <div className="p-6 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Organization Information</h2>
        </div>
        
        <form onSubmit={handleSubmit(onSubmit)} className="p-6 space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-1">
                Organization Name *
              </label>
              <input
                {...register('name')}
                type="text"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-500"
                placeholder="Your organization name"
                disabled={!isAdmin()}
              />
              {errors.name && (
                <p className="mt-1 text-sm text-red-600">{errors.name.message}</p>
              )}
            </div>

            <div>
              <label htmlFor="plan" className="block text-sm font-medium text-gray-700 mb-1">
                Plan
              </label>
              <select
                {...register('plan')}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-500"
                disabled={!isAdmin()}
              >
                {planOptions.map((plan) => (
                  <option key={plan.value} value={plan.value}>
                    {plan.label}
                  </option>
                ))}
              </select>
              {errors.plan && (
                <p className="mt-1 text-sm text-red-600">{errors.plan.message}</p>
              )}
            </div>
          </div>

          <div>
            <label htmlFor="description" className="block text-sm font-medium text-gray-700 mb-1">
              Description
            </label>
            <textarea
              {...register('description')}
              rows="3"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-500"
              placeholder="Describe your organization..."
              disabled={!isAdmin()}
            />
            {errors.description && (
              <p className="mt-1 text-sm text-red-600">{errors.description.message}</p>
            )}
          </div>

          {isAdmin() && (
            <div className="flex justify-end">
              <button
                type="submit"
                disabled={isLoading}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? (
                  <RefreshCw className="w-4 h-4 animate-spin" />
                ) : (
                  <Save className="w-4 h-4" />
                )}
                {isLoading ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          )}
        </form>
      </div>

      {/* Organization Stats */}
      {organization && (
        <div className="bg-white rounded-lg shadow-md">
          <div className="p-6 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">Organization Statistics</h2>
          </div>
          <div className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">
                  {organization.usage_stats?.total_groups || 0}
                </div>
                <div className="text-sm text-gray-600">Monitored Groups</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">
                  {organization.usage_stats?.total_users || 0}
                </div>
                <div className="text-sm text-gray-600">Watchlist Users</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-purple-600">
                  {organization.usage_stats?.total_messages || 0}
                </div>
                <div className="text-sm text-gray-600">Total Messages</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-orange-600">
                  {organization.usage_stats?.total_forwarded || 0}
                </div>
                <div className="text-sm text-gray-600">Messages Forwarded</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {!isAdmin() && (
        <div className="bg-yellow-50 border border-yellow-200 text-yellow-800 px-4 py-3 rounded-lg">
          <p className="text-sm">
            <strong>Note:</strong> You need Admin or Owner permissions to modify organization settings.
            Contact your organization owner to request access.
          </p>
        </div>
      )}
    </div>
  );
};

export default OrganizationSettings;