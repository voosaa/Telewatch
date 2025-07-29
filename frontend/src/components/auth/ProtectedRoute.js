import React from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { AlertCircle } from 'lucide-react';

const ProtectedRoute = ({ children, requiredRoles = null, fallback = null }) => {
  const { user, loading, isAuthenticated } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!isAuthenticated()) {
    return fallback || (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <AlertCircle className="mx-auto h-12 w-12 text-red-500" />
          <h3 className="mt-2 text-sm font-medium text-gray-900">Access Denied</h3>
          <p className="mt-1 text-sm text-gray-500">Please log in to access this page.</p>
        </div>
      </div>
    );
  }

  if (requiredRoles) {
    const hasRequiredRole = Array.isArray(requiredRoles) 
      ? requiredRoles.includes(user.role)
      : user.role === requiredRoles;

    if (!hasRequiredRole) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
          <div className="text-center">
            <AlertCircle className="mx-auto h-12 w-12 text-orange-500" />
            <h3 className="mt-2 text-sm font-medium text-gray-900">Insufficient Permissions</h3>
            <p className="mt-1 text-sm text-gray-500">
              You don't have the required permissions to access this page.
            </p>
            <p className="mt-1 text-xs text-gray-400">
              Required: {Array.isArray(requiredRoles) ? requiredRoles.join(', ') : requiredRoles}
            </p>
          </div>
        </div>
      );
    }
  }

  return children;
};

export default ProtectedRoute;