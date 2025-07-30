import React, { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { 
  Upload, 
  FileText, 
  Play, 
  Pause, 
  Trash2, 
  AlertCircle, 
  CheckCircle, 
  Clock,
  User,
  Activity,
  Loader2
} from 'lucide-react';
import axios from 'axios';

const AccountManager = () => {
  const { currentUser } = useAuth();
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [uploadLoading, setUploadLoading] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState({ session: null, json: null });
  const [showUploadModal, setShowUploadModal] = useState(false);

  useEffect(() => {
    fetchAccounts();
  }, []);

  const fetchAccounts = async () => {
    try {
      const response = await axios.get(
        `${process.env.REACT_APP_BACKEND_URL}/api/accounts`,
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem('token')}`
          }
        }
      );
      setAccounts(response.data.accounts || []);
    } catch (err) {
      setError('Failed to load accounts');
    } finally {
      setLoading(false);
    }
  };

  const handleFileSelect = (event, fileType) => {
    const file = event.target.files[0];
    if (file) {
      setSelectedFiles(prev => ({
        ...prev,
        [fileType]: file
      }));
    }
  };

  const handleUpload = async () => {
    if (!selectedFiles.session || !selectedFiles.json) {
      setError('Please select both session and JSON files');
      return;
    }

    setUploadLoading(true);
    setError('');

    try {
      const formData = new FormData();
      formData.append('session_file', selectedFiles.session);
      formData.append('json_file', selectedFiles.json);

      const response = await axios.post(
        `${process.env.REACT_APP_BACKEND_URL}/api/accounts/upload`,
        formData,
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem('token')}`,
            'Content-Type': 'multipart/form-data'
          }
        }
      );

      setShowUploadModal(false);
      setSelectedFiles({ session: null, json: null });
      await fetchAccounts();
      
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to upload account files');
    } finally {
      setUploadLoading(false);
    }
  };

  const handleAccountAction = async (accountId, action) => {
    try {
      await axios.post(
        `${process.env.REACT_APP_BACKEND_URL}/api/accounts/${accountId}/${action}`,
        {},
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem('token')}`
          }
        }
      );
      await fetchAccounts();
    } catch (err) {
      setError(`Failed to ${action} account`);
    }
  };

  const handleDeleteAccount = async (accountId) => {
    if (!window.confirm('Are you sure you want to delete this account?')) {
      return;
    }

    try {
      await axios.delete(
        `${process.env.REACT_APP_BACKEND_URL}/api/accounts/${accountId}`,
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem('token')}`
          }
        }
      );
      await fetchAccounts();
    } catch (err) {
      setError('Failed to delete account');
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'active':
        return 'text-green-600 bg-green-100';
      case 'inactive':
        return 'text-gray-600 bg-gray-100';
      case 'error':
        return 'text-red-600 bg-red-100';
      default:
        return 'text-yellow-600 bg-yellow-100';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'active':
        return <CheckCircle className="h-4 w-4" />;
      case 'inactive':
        return <Pause className="h-4 w-4" />;
      case 'error':
        return <AlertCircle className="h-4 w-4" />;
      default:
        return <Clock className="h-4 w-4" />;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Account Management</h1>
            <p className="mt-2 text-gray-600">
              Manage your Telegram user accounts for stealth monitoring
            </p>
          </div>
          <button
            onClick={() => setShowUploadModal(true)}
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            <Upload className="h-4 w-4" />
            Add Account
          </button>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
          <div className="flex items-center gap-2">
            <AlertCircle className="h-5 w-5 text-red-600" />
            <span className="text-red-800">{error}</span>
          </div>
        </div>
      )}

      {/* Accounts Grid */}
      {accounts.length === 0 ? (
        <div className="text-center py-12">
          <User className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No accounts yet</h3>
          <p className="text-gray-600 mb-6">
            Upload your Telegram session files to start monitoring
          </p>
          <button
            onClick={() => setShowUploadModal(true)}
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            <Upload className="h-4 w-4" />
            Add Your First Account
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {accounts.map((account) => (
            <div key={account.id} className="bg-white rounded-lg border border-gray-200 p-6">
              {/* Account Header */}
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
                    <User className="h-5 w-5 text-blue-600" />
                  </div>
                  <div>
                    <h3 className="font-medium text-gray-900">
                      {account.phone_number || account.name || 'Unknown'}
                    </h3>
                    <p className="text-sm text-gray-600">ID: {account.user_id}</p>
                  </div>
                </div>
                <div className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(account.status)}`}>
                  {getStatusIcon(account.status)}
                  {account.status}
                </div>
              </div>

              {/* Account Stats */}
              <div className="grid grid-cols-2 gap-4 mb-4">
                <div className="text-center p-3 bg-gray-50 rounded-lg">
                  <div className="text-2xl font-bold text-gray-900">
                    {account.groups_count || 0}
                  </div>
                  <div className="text-sm text-gray-600">Groups</div>
                </div>
                <div className="text-center p-3 bg-gray-50 rounded-lg">
                  <div className="text-2xl font-bold text-gray-900">
                    {account.messages_count || 0}
                  </div>
                  <div className="text-sm text-gray-600">Messages</div>
                </div>
              </div>

              {/* Account Actions */}
              <div className="flex gap-2">
                {account.status === 'active' ? (
                  <button
                    onClick={() => handleAccountAction(account.id, 'deactivate')}
                    className="flex-1 inline-flex items-center justify-center gap-2 px-3 py-2 bg-yellow-100 text-yellow-800 rounded-lg hover:bg-yellow-200 transition-colors text-sm"
                  >
                    <Pause className="h-4 w-4" />
                    Pause
                  </button>
                ) : (
                  <button
                    onClick={() => handleAccountAction(account.id, 'activate')}
                    className="flex-1 inline-flex items-center justify-center gap-2 px-3 py-2 bg-green-100 text-green-800 rounded-lg hover:bg-green-200 transition-colors text-sm"
                  >
                    <Play className="h-4 w-4" />
                    Activate
                  </button>
                )}
                <button
                  onClick={() => handleDeleteAccount(account.id)}
                  className="px-3 py-2 bg-red-100 text-red-800 rounded-lg hover:bg-red-200 transition-colors"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>

              {/* Last Activity */}
              {account.last_activity && (
                <div className="mt-4 pt-4 border-t border-gray-200">
                  <div className="flex items-center gap-2 text-sm text-gray-600">
                    <Activity className="h-4 w-4" />
                    Last activity: {new Date(account.last_activity).toLocaleString()}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Upload Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 max-w-md w-full mx-4">
            <h3 className="text-xl font-semibold mb-4">Add Telegram Account</h3>
            
            <div className="space-y-4">
              {/* Session File */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Session File (.session)
                </label>
                <div className="border-2 border-dashed border-gray-300 rounded-lg p-4">
                  <input
                    type="file"
                    accept=".session"
                    onChange={(e) => handleFileSelect(e, 'session')}
                    className="hidden"
                    id="session-file"
                  />
                  <label
                    htmlFor="session-file"
                    className="cursor-pointer flex flex-col items-center"
                  >
                    <FileText className="h-8 w-8 text-gray-400 mb-2" />
                    <span className="text-sm text-gray-600">
                      {selectedFiles.session ? selectedFiles.session.name : 'Click to select session file'}
                    </span>
                  </label>
                </div>
              </div>

              {/* JSON File */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  JSON File (.json)
                </label>
                <div className="border-2 border-dashed border-gray-300 rounded-lg p-4">
                  <input
                    type="file"
                    accept=".json"
                    onChange={(e) => handleFileSelect(e, 'json')}
                    className="hidden"
                    id="json-file"
                  />
                  <label
                    htmlFor="json-file"
                    className="cursor-pointer flex flex-col items-center"
                  >
                    <FileText className="h-8 w-8 text-gray-400 mb-2" />
                    <span className="text-sm text-gray-600">
                      {selectedFiles.json ? selectedFiles.json.name : 'Click to select JSON file'}
                    </span>
                  </label>
                </div>
              </div>
            </div>

            {/* Info */}
            <div className="mt-4 p-3 bg-blue-50 rounded-lg">
              <p className="text-sm text-blue-800">
                <strong>How to get these files:</strong><br />
                1. Use Telethon or similar to create a session<br />
                2. Export your account data as JSON<br />
                3. Upload both files to start monitoring
              </p>
            </div>

            {/* Actions */}
            <div className="flex gap-3 mt-6">
              <button
                onClick={() => {
                  setShowUploadModal(false);
                  setSelectedFiles({ session: null, json: null });
                  setError('');
                }}
                className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleUpload}
                disabled={uploadLoading || !selectedFiles.session || !selectedFiles.json}
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {uploadLoading ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Uploading...
                  </>
                ) : (
                  <>
                    <Upload className="h-4 w-4" />
                    Upload Account
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AccountManager;