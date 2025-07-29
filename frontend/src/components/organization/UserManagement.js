import React, { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { useForm } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import * as yup from 'yup';
import axios from 'axios';
import { 
  Users, 
  UserPlus, 
  Mail, 
  Shield, 
  Crown, 
  Eye, 
  Trash2, 
  RefreshCw,
  AlertCircle,
  CheckCircle
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const inviteSchema = yup.object({
  email: yup.string().email('Invalid email').required('Email is required'),
  fullName: yup.string().required('Full name is required'),
  role: yup.string().oneOf(['owner', 'admin', 'viewer']).required('Role is required')
});

const UserManagement = () => {
  const { user, isAdmin, isOwner } = useAuth();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showInviteForm, setShowInviteForm] = useState(false);
  const [isInviting, setIsInviting] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset
  } = useForm({
    resolver: yupResolver(inviteSchema)
  });

  useEffect(() => {
    fetchUsers();
  }, []);

  const fetchUsers = async () => {
    try {
      const response = await axios.get(`${API}/users`);
      setUsers(response.data);
    } catch (error) {
      console.error('Error fetching users:', error);
      setMessage({ type: 'error', text: 'Failed to load users' });
    } finally {
      setLoading(false);
    }
  };

  const handleInviteUser = async (data) => {
    setIsInviting(true);
    setMessage({ type: '', text: '' });

    try {
      await axios.post(`${API}/users/invite`, {
        email: data.email,
        full_name: data.fullName,
        role: data.role
      });
      
      setMessage({ 
        type: 'success', 
        text: `User invited successfully! They will receive login instructions via email.` 
      });
      reset();
      setShowInviteForm(false);
      fetchUsers();
    } catch (error) {
      console.error('Error inviting user:', error);
      setMessage({ 
        type: 'error', 
        text: error.response?.data?.detail || 'Failed to invite user' 
      });
    } finally {
      setIsInviting(false);
    }
  };

  const handleUpdateRole = async (userId, newRole) => {
    if (!isOwner()) {
      setMessage({ type: 'error', text: 'Only owners can change user roles' });
      return;
    }

    try {
      await axios.put(`${API}/users/${userId}/role`, null, {
        params: { new_role: newRole }
      });
      setMessage({ type: 'success', text: 'User role updated successfully' });
      fetchUsers();
    } catch (error) {
      console.error('Error updating role:', error);
      setMessage({ 
        type: 'error', 
        text: error.response?.data?.detail || 'Failed to update user role' 
      });
    }
  };

  const handleDeactivateUser = async (userId, userName) => {
    if (!isAdmin()) {
      setMessage({ type: 'error', text: 'You do not have permission to deactivate users' });
      return;
    }

    if (window.confirm(`Are you sure you want to deactivate ${userName}? They will lose access to the system.`)) {
      try {
        await axios.delete(`${API}/users/${userId}`);
        setMessage({ type: 'success', text: 'User deactivated successfully' });
        fetchUsers();
      } catch (error) {
        console.error('Error deactivating user:', error);
        setMessage({ 
          type: 'error', 
          text: error.response?.data?.detail || 'Failed to deactivate user' 
        });
      }
    }
  };

  const getRoleIcon = (role) => {
    switch (role) {
      case 'owner': return <Crown className="w-4 h-4 text-yellow-600" />;
      case 'admin': return <Shield className="w-4 h-4 text-blue-600" />;
      case 'viewer': return <Eye className="w-4 h-4 text-gray-600" />;
      default: return <Users className="w-4 h-4 text-gray-400" />;
    }
  };

  const getRoleBadgeColor = (role) => {
    switch (role) {
      case 'owner': return 'bg-yellow-100 text-yellow-800';
      case 'admin': return 'bg-blue-100 text-blue-800'; 
      case 'viewer': return 'bg-gray-100 text-gray-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  if (!isAdmin()) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <AlertCircle className="mx-auto h-12 w-12 text-orange-500" />
          <h3 className="mt-2 text-sm font-medium text-gray-900">Access Restricted</h3>
          <p className="mt-1 text-sm text-gray-500">
            You need Admin or Owner permissions to manage users.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Users className="h-8 w-8 text-blue-600" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">User Management</h1>
            <p className="text-gray-600">Manage team members and their permissions</p>
          </div>
        </div>
        
        <button
          onClick={() => setShowInviteForm(true)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          <UserPlus className="w-4 h-4" />
          Invite User
        </button>
      </div>

      {message.text && (
        <div className={`px-4 py-3 rounded-lg flex items-center gap-2 ${
          message.type === 'success' 
            ? 'bg-green-50 border border-green-200 text-green-800' 
            : 'bg-red-50 border border-red-200 text-red-800'
        }`}>
          {message.type === 'success' ? <CheckCircle className="h-4 w-4" /> : <AlertCircle className="h-4 w-4" />}
          {message.text}
        </div>
      )}

      {/* Invite User Form */}
      {showInviteForm && (
        <div className="bg-white rounded-lg shadow-md p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Invite New User</h3>
          <form onSubmit={handleSubmit(handleInviteUser)} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Email Address *
                </label>
                <input
                  {...register('email')}
                  type="email"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-500"
                  placeholder="user@example.com"
                />
                {errors.email && (
                  <p className="mt-1 text-sm text-red-600">{errors.email.message}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Full Name *
                </label>
                <input
                  {...register('fullName')}
                  type="text"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-500"
                  placeholder="John Doe"
                />
                {errors.fullName && (
                  <p className="mt-1 text-sm text-red-600">{errors.fullName.message}</p>
                )}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Role *
              </label>
              <select
                {...register('role')}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-500"
              >
                <option value="">Select a role...</option>
                <option value="viewer">Viewer - Can view data only</option>
                <option value="admin">Admin - Can manage resources and invite users</option>
                {isOwner() && <option value="owner">Owner - Full system access</option>}
              </select>
              {errors.role && (
                <p className="mt-1 text-sm text-red-600">{errors.role.message}</p>
              )}
            </div>

            <div className="flex gap-3">
              <button
                type="submit"
                disabled={isInviting}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
              >
                {isInviting ? (
                  <RefreshCw className="w-4 h-4 animate-spin" />
                ) : (
                  <Mail className="w-4 h-4" />
                )}
                {isInviting ? 'Sending...' : 'Send Invitation'}
              </button>
              <button
                type="button"
                onClick={() => setShowInviteForm(false)}
                className="px-4 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600 transition-colors"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Users List */}
      <div className="bg-white rounded-lg shadow-md">
        <div className="p-6 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">Team Members ({users.length})</h3>
        </div>
        
        <div className="divide-y divide-gray-200">
          {loading ? (
            <div className="p-6 text-center">
              <RefreshCw className="w-6 h-6 animate-spin text-blue-500 mx-auto" />
            </div>
          ) : users.length === 0 ? (
            <div className="p-6 text-center text-gray-500">
              No users found. Invite your first team member to get started.
            </div>
          ) : (
            users.map((teamUser) => (
              <div key={teamUser.id} className="p-6 hover:bg-gray-50">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 bg-blue-600 rounded-full flex items-center justify-center text-white font-semibold">
                      {teamUser.full_name.charAt(0).toUpperCase()}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h4 className="text-lg font-medium text-gray-900">{teamUser.full_name}</h4>
                        {teamUser.id === user.id && (
                          <span className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded-full">You</span>
                        )}
                      </div>
                      <p className="text-gray-600 text-sm">{teamUser.email}</p>
                      <div className="flex items-center gap-2 mt-1">
                        {getRoleIcon(teamUser.role)}
                        <span className={`px-2 py-1 text-xs rounded-full ${getRoleBadgeColor(teamUser.role)}`}>
                          {teamUser.role.charAt(0).toUpperCase() + teamUser.role.slice(1)}
                        </span>
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-2">
                    {isOwner() && teamUser.id !== user.id && (
                      <select
                        value={teamUser.role}
                        onChange={(e) => handleUpdateRole(teamUser.id, e.target.value)}
                        className="text-sm border border-gray-300 rounded px-2 py-1"
                      >
                        <option value="viewer">Viewer</option>
                        <option value="admin">Admin</option>
                        <option value="owner">Owner</option>
                      </select>
                    )}
                    
                    {isAdmin() && teamUser.id !== user.id && (
                      <button
                        onClick={() => handleDeactivateUser(teamUser.id, teamUser.full_name)}
                        className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                        title="Deactivate user"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                </div>
                
                <div className="mt-2 text-xs text-gray-500">
                  Joined: {new Date(teamUser.created_at).toLocaleDateString()} • 
                  Last login: {teamUser.last_login ? new Date(teamUser.last_login).toLocaleDateString() : 'Never'}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

export default UserManagement;