import React, { useState, useEffect } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import AuthWrapper from "./components/auth/AuthWrapper";
import ProtectedRoute from "./components/auth/ProtectedRoute";
import OrganizationSettings from "./components/organization/OrganizationSettings";
import UserManagement from "./components/organization/UserManagement";
import axios from "axios";
import { 
  Activity, 
  Users, 
  MessageSquare, 
  Settings, 
  Search, 
  Plus,
  Trash2,
  Eye,
  BarChart3,
  Bot,
  Shield,
  ChevronRight,
  RefreshCw,
  Building,
  UserCog,
  LogOut,
  User,
  CreditCard,
  Crown,
  Check,
  X
} from "lucide-react";
import "./App.css";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// =================== MULTI-TENANT COMPONENTS ===================

const Sidebar = ({ activeTab, setActiveTab, user, organization, logout }) => {
  const menuItems = [
    { id: 'dashboard', label: 'Dashboard', icon: BarChart3, roles: ['owner', 'admin', 'viewer'] },
    { id: 'groups', label: 'Groups', icon: Users, roles: ['owner', 'admin', 'viewer'] },
    { id: 'watchlist', label: 'Watchlist', icon: Shield, roles: ['owner', 'admin', 'viewer'] },
    { id: 'forwarding', label: 'Forwarding', icon: ChevronRight, roles: ['owner', 'admin', 'viewer'] },
    { id: 'messages', label: 'Messages', icon: MessageSquare, roles: ['owner', 'admin', 'viewer'] },
    { id: 'bot', label: 'Bot Status', icon: Bot, roles: ['owner', 'admin', 'viewer'] },
    { id: 'users', label: 'Team', icon: UserCog, roles: ['owner', 'admin'] },
    { id: 'subscription', label: 'Subscription', icon: CreditCard, roles: ['owner', 'admin'] },
    { id: 'org-settings', label: 'Organization', icon: Building, roles: ['owner', 'admin'] },
    { id: 'settings', label: 'Settings', icon: Settings, roles: ['owner', 'admin', 'viewer'] },
  ];

  const filteredMenuItems = menuItems.filter(item => 
    item.roles.includes(user?.role)
  );

  return (
    <div className="w-64 bg-gray-900 text-white min-h-screen flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-gray-700">
        <div className="flex items-center gap-2 mb-2">
          <Bot className="w-6 h-6 text-blue-500" />
          <h1 className="text-xl font-bold">Telegram Monitor</h1>
        </div>
        <div className="text-xs text-gray-400">
          <div className="flex items-center gap-1">
            <Building className="w-3 h-3" />
            {organization?.name || 'Loading...'}
          </div>
          <div className="flex items-center gap-1 mt-1">
            <User className="w-3 h-3" />
            {user?.full_name} ({user?.role})
          </div>
        </div>
      </div>
      
      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-2">
        {filteredMenuItems.map((item) => {
          const Icon = item.icon;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg transition-colors ${
                activeTab === item.id
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-300 hover:bg-gray-800 hover:text-white'
              }`}
            >
              <Icon className="w-5 h-5" />
              {item.label}
            </button>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-gray-700">
        <button
          onClick={logout}
          className="w-full flex items-center gap-3 px-3 py-2 text-gray-300 hover:bg-red-600 hover:text-white rounded-lg transition-colors"
        >
          <LogOut className="w-5 h-5" />
          Sign Out
        </button>
      </div>
    </div>
  );
};

const Dashboard = ({ user }) => {
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      const response = await axios.get(`${API}/stats`);
      setStats(response.data);
    } catch (error) {
      console.error('Error fetching stats:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center h-64">
      <RefreshCw className="w-8 h-8 animate-spin text-blue-500" />
    </div>;
  }

  const statCards = [
    { 
      title: 'Active Groups', 
      value: stats.total_groups || 0, 
      icon: Users, 
      color: 'bg-blue-500' 
    },
    { 
      title: 'Watchlist Users', 
      value: stats.total_watchlist_users || 0, 
      icon: Shield, 
      color: 'bg-green-500' 
    },
    { 
      title: 'Forwarding Destinations', 
      value: stats.total_forwarding_destinations || 0, 
      icon: ChevronRight, 
      color: 'bg-indigo-500' 
    },
    { 
      title: 'Total Messages', 
      value: stats.total_messages || 0, 
      icon: MessageSquare, 
      color: 'bg-purple-500' 
    },
    { 
      title: 'Messages Forwarded', 
      value: stats.total_forwarded || 0, 
      icon: Activity, 
      color: 'bg-orange-500' 
    },
    { 
      title: 'Forwarding Success Rate', 
      value: `${stats.forwarding_success_rate || 0}%`, 
      icon: Activity, 
      color: 'bg-emerald-500' 
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-600">Welcome back, {user?.full_name}!</p>
        </div>
        <button 
          onClick={fetchStats}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {statCards.map((stat, index) => {
          const Icon = stat.icon;
          return (
            <div key={index} className="bg-white rounded-lg shadow-md p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-600 text-sm">{stat.title}</p>
                  <p className="text-3xl font-bold text-gray-900">{stat.value}</p>
                </div>
                <div className={`${stat.color} p-3 rounded-lg`}>
                  <Icon className="w-6 h-6 text-white" />
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Quick Actions */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {(user?.role === 'owner' || user?.role === 'admin') && (
            <>
              <button className="p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors text-left">
                <Users className="w-6 h-6 text-blue-600 mb-2" />
                <h4 className="font-medium text-gray-900">Add Group</h4>
                <p className="text-sm text-gray-600">Monitor a new Telegram group</p>
              </button>
              <button className="p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors text-left">
                <Shield className="w-6 h-6 text-green-600 mb-2" />
                <h4 className="font-medium text-gray-900">Add to Watchlist</h4>
                <p className="text-sm text-gray-600">Monitor a new user</p>
              </button>
              <button className="p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors text-left">
                <ChevronRight className="w-6 h-6 text-indigo-600 mb-2" />
                <h4 className="font-medium text-gray-900">Setup Forwarding</h4>
                <p className="text-sm text-gray-600">Configure message forwarding</p>
              </button>
            </>
          )}
        </div>
      </div>

      {/* Recent Activity */}
      {stats.recent_forwards && stats.recent_forwards.length > 0 && (
        <div className="bg-white rounded-lg shadow-md p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Recent Activity</h3>
          <div className="space-y-3">
            {stats.recent_forwards.map((activity, index) => (
              <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center text-white text-sm font-semibold">
                    {activity.username.charAt(0).toUpperCase()}
                  </div>
                  <div>
                    <div className="font-medium text-gray-900">@{activity.username}</div>
                    <div className="text-sm text-gray-600">{activity.group_name}</div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-sm font-medium text-gray-900">
                    {activity.destination_count} destinations
                  </div>
                  <div className="text-xs text-gray-500">
                    {new Date(activity.forwarded_at).toLocaleString()}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

const GroupsManager = () => {
  const [groups, setGroups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [newGroup, setNewGroup] = useState({
    group_id: '',
    group_name: '',
    group_type: 'group',
    invite_link: '',
    description: ''
  });

  useEffect(() => {
    fetchGroups();
  }, []);

  const fetchGroups = async () => {
    try {
      const response = await axios.get(`${API}/groups`);
      setGroups(response.data);
    } catch (error) {
      console.error('Error fetching groups:', error);
      setErrorMessage('Failed to load groups: ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  const handleAddGroup = async (e) => {
    e.preventDefault();
    setErrorMessage('');
    setSuccessMessage('');
    
    try {
      const response = await axios.post(`${API}/groups`, newGroup);
      setNewGroup({ group_id: '', group_name: '', group_type: 'group', invite_link: '', description: '' });
      setShowAddForm(false);
      setSuccessMessage(`Group "${response.data.group_name}" added successfully!`);
      fetchGroups();
      // Clear success message after 3 seconds
      setTimeout(() => setSuccessMessage(''), 3000);
    } catch (error) {
      console.error('Error adding group:', error);
      const errorMsg = error.response?.data?.detail || error.message;
      setErrorMessage(`Failed to add group: ${errorMsg}`);
    }
  };

  const handleDeleteGroup = async (groupId) => {
    if (window.confirm('Are you sure you want to remove this group from monitoring?')) {
      try {
        await axios.delete(`${API}/groups/${groupId}`);
        setSuccessMessage('Group removed successfully!');
        fetchGroups();
        setTimeout(() => setSuccessMessage(''), 3000);
      } catch (error) {
        console.error('Error deleting group:', error);
        setErrorMessage('Failed to delete group: ' + (error.response?.data?.detail || error.message));
      }
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">Groups Management</h1>
        <button
          onClick={() => {
            setShowAddForm(true);
            setErrorMessage('');
            setSuccessMessage('');
          }}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          <Plus className="w-4 h-4" />
          Add Group
        </button>
      </div>

      {/* Success/Error Messages */}
      {successMessage && (
        <div className="bg-green-50 border border-green-200 text-green-800 px-4 py-3 rounded-lg">
          ✅ {successMessage}
        </div>
      )}
      {errorMessage && (
        <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-lg">
          ❌ {errorMessage}
        </div>
      )}

      {/* Add Group Form */}
      {showAddForm && (
        <div className="bg-white rounded-lg shadow-md p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Add New Group</h3>
          <form onSubmit={handleAddGroup} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Group ID *
                </label>
                <input
                  type="text"
                  value={newGroup.group_id}
                  onChange={(e) => setNewGroup({ ...newGroup, group_id: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-500"
                  placeholder="-1001234567890"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Group Name *
                </label>
                <input
                  type="text"
                  value={newGroup.group_name}
                  onChange={(e) => setNewGroup({ ...newGroup, group_name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-500"
                  placeholder="My Telegram Group"
                  required
                />
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Group Type
                </label>
                <select
                  value={newGroup.group_type}
                  onChange={(e) => setNewGroup({ ...newGroup, group_type: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-500"
                >
                  <option value="group">Group</option>
                  <option value="supergroup">Supergroup</option>
                  <option value="channel">Channel</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Invite Link
                </label>
                <input
                  type="url"
                  value={newGroup.invite_link}
                  onChange={(e) => setNewGroup({ ...newGroup, invite_link: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-500"
                  placeholder="https://t.me/joinchat/..."
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Description
              </label>
              <textarea
                value={newGroup.description}
                onChange={(e) => setNewGroup({ ...newGroup, description: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-500"
                rows="3"
                placeholder="Group description..."
              />
            </div>
            <div className="flex gap-3">
              <button
                type="submit"
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                Add Group
              </button>
              <button
                type="button"
                onClick={() => setShowAddForm(false)}
                className="px-4 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600 transition-colors"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Groups List */}
      <div className="bg-white rounded-lg shadow-md">
        <div className="p-6 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">Monitored Groups ({groups.length})</h3>
        </div>
        <div className="divide-y divide-gray-200">
          {loading ? (
            <div className="p-6 text-center">
              <RefreshCw className="w-6 h-6 animate-spin text-blue-500 mx-auto" />
            </div>
          ) : groups.length === 0 ? (
            <div className="p-6 text-center text-gray-500">
              No groups configured. Add your first group to start monitoring.
            </div>
          ) : (
            groups.map((group) => (
              <div key={group.id} className="p-6 hover:bg-gray-50">
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h4 className="text-lg font-medium text-gray-900">{group.group_name}</h4>
                      <span className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded-full">
                        {group.group_type}
                      </span>
                    </div>
                    <p className="text-gray-600 text-sm">ID: {group.group_id}</p>
                    {group.description && (
                      <p className="text-gray-600 text-sm mt-1">{group.description}</p>
                    )}
                    <p className="text-gray-400 text-xs mt-2">
                      Added: {new Date(group.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    {group.invite_link && (
                      <a
                        href={group.invite_link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                      >
                        <Eye className="w-4 h-4" />
                      </a>
                    )}
                    <button
                      onClick={() => handleDeleteGroup(group.id)}
                      className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

const WatchlistManager = () => {
  const [users, setUsers] = useState([]);
  const [groups, setGroups] = useState([]);
  const [destinations, setDestinations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [newUser, setNewUser] = useState({
    username: '',
    user_id: '',
    full_name: '',
    group_ids: [],
    keywords: [],
    forwarding_destinations: []
  });

  useEffect(() => {
    fetchUsers();
    fetchGroups();
    fetchDestinations();
  }, []);

  const fetchUsers = async () => {
    try {
      const response = await axios.get(`${API}/watchlist`);
      setUsers(response.data);
    } catch (error) {
      console.error('Error fetching users:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchGroups = async () => {
    try {
      const response = await axios.get(`${API}/groups`);
      setGroups(response.data);
    } catch (error) {
      console.error('Error fetching groups:', error);
    }
  };

  const fetchDestinations = async () => {
    try {
      const response = await axios.get(`${API}/forwarding-destinations`);
      setDestinations(response.data);
    } catch (error) {
      console.error('Error fetching destinations:', error);
    }
  };

  const handleAddUser = async (e) => {
    e.preventDefault();
    setErrorMessage('');
    setSuccessMessage('');
    
    try {
      const response = await axios.post(`${API}/watchlist`, newUser);
      setNewUser({ username: '', user_id: '', full_name: '', group_ids: [], keywords: [], forwarding_destinations: [] });
      setShowAddForm(false);
      setSuccessMessage(`User "@${response.data.username}" added to watchlist successfully!`);
      fetchUsers();
      setTimeout(() => setSuccessMessage(''), 3000);
    } catch (error) {
      console.error('Error adding user:', error);
      const errorMsg = error.response?.data?.detail || error.message;
      setErrorMessage(`Failed to add user: ${errorMsg}`);
    }
  };

  const handleDeleteUser = async (userId) => {
    if (window.confirm('Are you sure you want to remove this user from watchlist?')) {
      try {
        await axios.delete(`${API}/watchlist/${userId}`);
        setSuccessMessage('User removed from watchlist successfully!');
        fetchUsers();
        setTimeout(() => setSuccessMessage(''), 3000);
      } catch (error) {
        console.error('Error deleting user:', error);
        setErrorMessage('Failed to delete user: ' + (error.response?.data?.detail || error.message));
      }
    }
  };

  const handleGroupToggle = (groupId) => {
    const newGroupIds = newUser.group_ids.includes(groupId)
      ? newUser.group_ids.filter(id => id !== groupId)
      : [...newUser.group_ids, groupId];
    setNewUser({ ...newUser, group_ids: newGroupIds });
  };

  const handleDestinationToggle = (destinationId) => {
    const newDestinationIds = newUser.forwarding_destinations.includes(destinationId)
      ? newUser.forwarding_destinations.filter(id => id !== destinationId)
      : [...newUser.forwarding_destinations, destinationId];
    setNewUser({ ...newUser, forwarding_destinations: newDestinationIds });
  };

  const handleKeywordsChange = (value) => {
    const keywords = value.split(',').map(k => k.trim()).filter(k => k);
    setNewUser({ ...newUser, keywords });
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">Watchlist Management</h1>
        <button
          onClick={() => {
            setShowAddForm(true);
            setErrorMessage('');
            setSuccessMessage('');
          }}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          <Plus className="w-4 h-4" />
          Add User
        </button>
      </div>

      {/* Success/Error Messages */}
      {successMessage && (
        <div className="bg-green-50 border border-green-200 text-green-800 px-4 py-3 rounded-lg">
          ✅ {successMessage}
        </div>
      )}
      {errorMessage && (
        <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-lg">
          ❌ {errorMessage}
        </div>
      )}

      {/* Add User Form */}
      {showAddForm && (
        <div className="bg-white rounded-lg shadow-md p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Add User to Watchlist</h3>
          <form onSubmit={handleAddUser} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Username *
                </label>
                <input
                  type="text"
                  value={newUser.username}
                  onChange={(e) => setNewUser({ ...newUser, username: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-500"
                  placeholder="username (without @)"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  User ID
                </label>
                <input
                  type="text"
                  value={newUser.user_id}
                  onChange={(e) => setNewUser({ ...newUser, user_id: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-500"
                  placeholder="123456789"
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Full Name
              </label>
              <input
                type="text"
                value={newUser.full_name}
                onChange={(e) => setNewUser({ ...newUser, full_name: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-500"
                placeholder="John Doe"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Keywords (comma-separated)
              </label>
              <input
                type="text"
                value={newUser.keywords.join(', ')}
                onChange={(e) => handleKeywordsChange(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-500"
                placeholder="crypto, bitcoin, trading"
              />
              <p className="text-xs text-gray-500 mt-1">Leave empty to monitor all messages</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Monitor in Groups (leave empty for global monitoring)
              </label>
              <div className="space-y-2 max-h-40 overflow-y-auto">
                {groups.map((group) => (
                  <label key={group.id} className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={newUser.group_ids.includes(group.id)}
                      onChange={() => handleGroupToggle(group.id)}
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <span className="text-sm">{group.group_name}</span>
                  </label>
                ))}
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Forwarding Destinations (where to forward messages from this user)
              </label>
              <div className="space-y-2 max-h-40 overflow-y-auto">
                {destinations.length === 0 ? (
                  <p className="text-sm text-gray-500">No forwarding destinations available. Add destinations in the Forwarding tab first.</p>
                ) : (
                  destinations.map((destination) => (
                    <label key={destination.id} className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={newUser.forwarding_destinations.includes(destination.id)}
                        onChange={() => handleDestinationToggle(destination.id)}
                        className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                      />
                      <span className="text-sm">{destination.destination_name} ({destination.destination_type})</span>
                    </label>
                  ))
                )}
              </div>
              <p className="text-xs text-gray-500 mt-1">Select where to forward messages from this user</p>
            </div>
            <div className="flex gap-3">
              <button
                type="submit"
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                Add User
              </button>
              <button
                type="button"
                onClick={() => setShowAddForm(false)}
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
          <h3 className="text-lg font-semibold text-gray-900">Watchlist Users ({users.length})</h3>
        </div>
        <div className="divide-y divide-gray-200">
          {loading ? (
            <div className="p-6 text-center">
              <RefreshCw className="w-6 h-6 animate-spin text-blue-500 mx-auto" />
            </div>
          ) : users.length === 0 ? (
            <div className="p-6 text-center text-gray-500">
              No users in watchlist. Add users to start monitoring their messages.
            </div>
          ) : (
            users.map((user) => (
              <div key={user.id} className="p-6 hover:bg-gray-50">
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h4 className="text-lg font-medium text-gray-900">@{user.username}</h4>
                      {user.full_name && (
                        <span className="text-gray-600">({user.full_name})</span>
                      )}
                    </div>
                    {user.user_id && (
                      <p className="text-gray-600 text-sm">ID: {user.user_id}</p>
                    )}
                    {user.keywords.length > 0 && (
                      <div className="mt-2">
                        <p className="text-sm text-gray-600 mb-1">Keywords:</p>
                        <div className="flex flex-wrap gap-1">
                          {user.keywords.map((keyword, index) => (
                            <span key={index} className="px-2 py-1 bg-yellow-100 text-yellow-800 text-xs rounded-full">
                              {keyword}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                    <div className="mt-2">
                      <span className="text-sm text-gray-600">
                        Monitoring: {user.group_ids.length === 0 ? 'All groups' : `${user.group_ids.length} specific groups`}
                      </span>
                    </div>
                    <p className="text-gray-400 text-xs mt-2">
                      Added: {new Date(user.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleDeleteUser(user.id)}
                      className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

const ForwardingManager = () => {
  const [destinations, setDestinations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [newDestination, setNewDestination] = useState({
    destination_id: '',
    destination_name: '',
    destination_type: 'channel',
    description: ''
  });

  useEffect(() => {
    fetchDestinations();
  }, []);

  const fetchDestinations = async () => {
    try {
      const response = await axios.get(`${API}/forwarding-destinations`);
      setDestinations(response.data);
    } catch (error) {
      console.error('Error fetching destinations:', error);
      setErrorMessage('Failed to load destinations: ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  const handleAddDestination = async (e) => {
    e.preventDefault();
    setErrorMessage('');
    setSuccessMessage('');
    
    try {
      const response = await axios.post(`${API}/forwarding-destinations`, newDestination);
      setNewDestination({ destination_id: '', destination_name: '', destination_type: 'channel', description: '' });
      setShowAddForm(false);
      setSuccessMessage(`Destination "${response.data.destination_name}" added successfully!`);
      fetchDestinations();
      setTimeout(() => setSuccessMessage(''), 3000);
    } catch (error) {
      console.error('Error adding destination:', error);
      const errorMsg = error.response?.data?.detail || error.message;
      setErrorMessage(`Failed to add destination: ${errorMsg}`);
    }
  };

  const handleDeleteDestination = async (destinationId) => {
    if (window.confirm('Are you sure you want to remove this forwarding destination?')) {
      try {
        await axios.delete(`${API}/forwarding-destinations/${destinationId}`);
        setSuccessMessage('Destination removed successfully!');
        fetchDestinations();
        setTimeout(() => setSuccessMessage(''), 3000);
      } catch (error) {
        console.error('Error deleting destination:', error);
        setErrorMessage('Failed to delete destination: ' + (error.response?.data?.detail || error.message));
      }
    }
  };

  const handleTestDestination = async (destinationId, destinationName) => {
    try {
      await axios.post(`${API}/forwarding-destinations/${destinationId}/test`);
      setSuccessMessage(`Test message sent to "${destinationName}" successfully!`);
      setTimeout(() => setSuccessMessage(''), 3000);
    } catch (error) {
      console.error('Error testing destination:', error);
      setErrorMessage(`Failed to test "${destinationName}": ` + (error.response?.data?.detail || error.message));
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">Forwarding Destinations</h1>
        <button
          onClick={() => {
            setShowAddForm(true);
            setErrorMessage('');
            setSuccessMessage('');
          }}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          <Plus className="w-4 h-4" />
          Add Destination
        </button>
      </div>

      {/* Success/Error Messages */}
      {successMessage && (
        <div className="bg-green-50 border border-green-200 text-green-800 px-4 py-3 rounded-lg">
          ✅ {successMessage}
        </div>
      )}
      {errorMessage && (
        <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-lg">
          ❌ {errorMessage}
        </div>
      )}

      {/* Info Box */}
      <div className="bg-blue-50 border border-blue-200 text-blue-800 px-4 py-3 rounded-lg">
        <p className="text-sm">
          <strong>ℹ️ How to get Chat/Channel IDs:</strong> Add your bot to the channel/group as admin, then forward a message 
          from that channel to @userinfobot to get the Chat ID (it will be negative for groups/channels).
        </p>
      </div>

      {/* Add Destination Form */}
      {showAddForm && (
        <div className="bg-white rounded-lg shadow-md p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Add Forwarding Destination</h3>
          <form onSubmit={handleAddDestination} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Destination ID *
                </label>
                <input
                  type="text"
                  value={newDestination.destination_id}
                  onChange={(e) => setNewDestination({ ...newDestination, destination_id: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-500"
                  placeholder="-1001234567890"
                  required
                />
                <p className="text-xs text-gray-500 mt-1">Chat ID of the channel/group (negative for channels/groups)</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Destination Name *
                </label>
                <input
                  type="text"
                  value={newDestination.destination_name}
                  onChange={(e) => setNewDestination({ ...newDestination, destination_name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-500"
                  placeholder="My Alert Channel"
                  required
                />
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Destination Type
                </label>
                <select
                  value={newDestination.destination_type}
                  onChange={(e) => setNewDestination({ ...newDestination, destination_type: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-500"
                >
                  <option value="channel">Channel</option>
                  <option value="group">Group</option>
                  <option value="user">User</option>
                </select>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Description
              </label>
              <textarea
                value={newDestination.description}
                onChange={(e) => setNewDestination({ ...newDestination, description: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-500"
                rows="3"
                placeholder="Description of this forwarding destination..."
              />
            </div>
            <div className="flex gap-3">
              <button
                type="submit"
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                Add Destination
              </button>
              <button
                type="button"
                onClick={() => setShowAddForm(false)}
                className="px-4 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600 transition-colors"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Destinations List */}
      <div className="bg-white rounded-lg shadow-md">
        <div className="p-6 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">Forwarding Destinations ({destinations.length})</h3>
        </div>
        <div className="divide-y divide-gray-200">
          {loading ? (
            <div className="p-6 text-center">
              <RefreshCw className="w-6 h-6 animate-spin text-blue-500 mx-auto" />
            </div>
          ) : destinations.length === 0 ? (
            <div className="p-6 text-center text-gray-500">
              No forwarding destinations configured. Add destinations to start forwarding monitored messages.
            </div>
          ) : (
            destinations.map((destination) => (
              <div key={destination.id} className="p-6 hover:bg-gray-50">
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h4 className="text-lg font-medium text-gray-900">{destination.destination_name}</h4>
                      <span className="px-2 py-1 bg-indigo-100 text-indigo-800 text-xs rounded-full">
                        {destination.destination_type}
                      </span>
                    </div>
                    <p className="text-gray-600 text-sm">ID: {destination.destination_id}</p>
                    {destination.description && (
                      <p className="text-gray-600 text-sm mt-1">{destination.description}</p>
                    )}
                    <div className="flex items-center gap-4 mt-2">
                      <p className="text-gray-400 text-xs">
                        Messages forwarded: {destination.message_count || 0}
                      </p>
                      {destination.last_forwarded && (
                        <p className="text-gray-400 text-xs">
                          Last used: {new Date(destination.last_forwarded).toLocaleDateString()}
                        </p>
                      )}
                    </div>
                    <p className="text-gray-400 text-xs mt-1">
                      Added: {new Date(destination.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleTestDestination(destination.id, destination.destination_name)}
                      className="px-3 py-1 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors text-sm"
                    >
                      Test
                    </button>
                    <button
                      onClick={() => handleDeleteDestination(destination.id)}
                      className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

const MessagesViewer = () => {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterGroup, setFilterGroup] = useState('');
  const [filterType, setFilterType] = useState('');
  const [groups, setGroups] = useState([]);

  useEffect(() => {
    fetchMessages();
    fetchGroups();
  }, []);

  const fetchMessages = async () => {
    try {
      const params = new URLSearchParams();
      if (filterGroup) params.append('group_id', filterGroup);
      if (filterType) params.append('message_type', filterType);
      
      const response = await axios.get(`${API}/messages?${params.toString()}`);
      setMessages(response.data);
    } catch (error) {
      console.error('Error fetching messages:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchGroups = async () => {
    try {
      const response = await axios.get(`${API}/groups`);
      setGroups(response.data);
    } catch (error) {
      console.error('Error fetching groups:', error);
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      fetchMessages();
      return;
    }

    try {
      setLoading(true);
      const response = await axios.get(`${API}/messages/search?q=${encodeURIComponent(searchQuery)}`);
      setMessages(response.data.messages);
    } catch (error) {
      console.error('Error searching messages:', error);
    } finally {
      setLoading(false);
    }
  };

  const getMessageTypeIcon = (type) => {
    switch (type) {
      case 'photo': return '🖼️';
      case 'video': return '🎥';
      case 'document': return '📄';
      case 'audio': return '🎵';
      case 'voice': return '🎤';
      case 'sticker': return '😀';
      default: return '💬';
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">Message Archive</h1>
        <button
          onClick={fetchMessages}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {/* Search and Filters */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
          <div className="md:col-span-2">
            <label className="block text-sm font-medium text-gray-700 mb-1">Search Messages</label>
            <div className="flex gap-2">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-500"
                placeholder="Search by message text, username, or group..."
                onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
              />
              <button
                onClick={handleSearch}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                <Search className="w-4 h-4" />
              </button>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Filter by Group</label>
            <select
              value={filterGroup}
              onChange={(e) => setFilterGroup(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-500"
            >
              <option value="">All Groups</option>
              {groups.map((group) => (
                <option key={group.id} value={group.group_id}>{group.group_name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Filter by Type</label>
            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-500"
            >
              <option value="">All Types</option>
              <option value="text">Text</option>
              <option value="photo">Photo</option>
              <option value="video">Video</option>
              <option value="document">Document</option>
              <option value="audio">Audio</option>
              <option value="voice">Voice</option>
              <option value="sticker">Sticker</option>
            </select>
          </div>
        </div>
        <button
          onClick={fetchMessages}
          className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
        >
          Apply Filters
        </button>
      </div>

      {/* Messages List */}
      <div className="bg-white rounded-lg shadow-md">
        <div className="p-6 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">
            Messages ({messages.length})
          </h3>
        </div>
        <div className="divide-y divide-gray-200 max-h-96 overflow-y-auto">
          {loading ? (
            <div className="p-6 text-center">
              <RefreshCw className="w-6 h-6 animate-spin text-blue-500 mx-auto" />
            </div>
          ) : messages.length === 0 ? (
            <div className="p-6 text-center text-gray-500">
              No messages found. Messages will appear here when monitored users post in configured groups.
            </div>
          ) : (
            messages.map((message) => (
              <div key={message.id} className="p-4 hover:bg-gray-50">
                <div className="flex items-start gap-3">
                  <div className="text-2xl">{getMessageTypeIcon(message.message_type)}</div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-medium text-gray-900">@{message.username}</span>
                      <ChevronRight className="w-4 h-4 text-gray-400" />
                      <span className="text-gray-600 text-sm">{message.group_name}</span>
                      <span className="text-gray-400 text-xs">
                        {new Date(message.timestamp).toLocaleString()}
                      </span>
                    </div>
                    {message.message_text && (
                      <p className="text-gray-700 text-sm mb-2 break-words">{message.message_text}</p>
                    )}
                    {message.matched_keywords.length > 0 && (
                      <div className="flex flex-wrap gap-1 mb-2">
                        {message.matched_keywords.map((keyword, index) => (
                          <span key={index} className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded-full">
                            {keyword}
                          </span>
                        ))}
                      </div>
                    )}
                    {message.media_info && Object.keys(message.media_info).length > 0 && (
                      <div className="text-xs text-gray-500">
                        Media info: {JSON.stringify(message.media_info, null, 2)}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

const BotStatus = () => {
  const [botInfo, setBotInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [testResult, setTestResult] = useState('');

  useEffect(() => {
    testBotConnection();
  }, []);

  const testBotConnection = async () => {
    try {
      const response = await axios.post(`${API}/test/bot`);
      setBotInfo(response.data.bot_info);
      setTestResult('✅ Bot connection successful');
    } catch (error) {
      console.error('Bot test failed:', error);
      setTestResult('❌ Bot connection failed: ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">Bot Status</h1>
        <button
          onClick={testBotConnection}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          Test Connection
        </button>
      </div>

      <div className="bg-white rounded-lg shadow-md p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Telegram Bot Information</h3>
        
        {loading ? (
          <div className="text-center">
            <RefreshCw className="w-6 h-6 animate-spin text-blue-500 mx-auto" />
            <p className="text-gray-600 mt-2">Testing bot connection...</p>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="font-medium">{testResult}</p>
            </div>
            
            {botInfo && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Bot ID</label>
                  <p className="text-gray-900">{botInfo.id}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Username</label>
                  <p className="text-gray-900">@{botInfo.username}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
                  <p className="text-gray-900">{botInfo.first_name}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Is Bot</label>
                  <p className="text-gray-900">{botInfo.is_bot ? 'Yes' : 'No'}</p>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      <div className="bg-white rounded-lg shadow-md p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Setup Instructions</h3>
        <div className="space-y-4 text-sm text-gray-700">
          <div>
            <h4 className="font-medium text-gray-900 mb-2">1. Add Bot to Groups</h4>
            <p>Add your bot (@{botInfo?.username || 'your_bot'}) to the Telegram groups you want to monitor.</p>
          </div>
          <div>
            <h4 className="font-medium text-gray-900 mb-2">2. Get Group IDs</h4>
            <p>Forward a message from the group to @userinfobot or check the browser console when the bot receives messages.</p>
          </div>
          <div>
            <h4 className="font-medium text-gray-900 mb-2">3. Configure Groups</h4>
            <p>Add the group IDs and details in the Groups section of this dashboard.</p>
          </div>
          <div>
            <h4 className="font-medium text-gray-900 mb-2">4. Add Users to Watchlist</h4>
            <p>Configure which users you want to monitor in the Watchlist section.</p>
          </div>
        </div>
      </div>
    </div>
  );
};

const SettingsPage = () => {
  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-gray-900">Settings</h1>
      
      <div className="bg-white rounded-lg shadow-md p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">System Configuration</h3>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Telegram Bot Token</label>
            <input
              type="password"
              value="8342094196:AAE-E8jIYLjYflUPtY0G02NLbogbDpN_FE8"
              disabled
              className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-100"
            />
            <p className="text-xs text-gray-500 mt-1">Bot token is configured in environment variables</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Database</label>
            <p className="text-gray-900">MongoDB - telegram_bot_db</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">API Endpoint</label>
            <p className="text-gray-900">{BACKEND_URL}/api</p>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow-md p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Features Status</h3>
        <div className="space-y-3">
          <div className="flex items-center justify-between p-3 bg-green-50 rounded-lg">
            <span className="font-medium text-green-900">✅ Group Management</span>
            <span className="text-green-700">Active</span>
          </div>
          <div className="flex items-center justify-between p-3 bg-green-50 rounded-lg">
            <span className="font-medium text-green-900">✅ Watchlist Management</span>
            <span className="text-green-700">Active</span>
          </div>
          <div className="flex items-center justify-between p-3 bg-green-50 rounded-lg">
            <span className="font-medium text-green-900">✅ Message Monitoring</span>
            <span className="text-green-700">Active</span>
          </div>
          <div className="flex items-center justify-between p-3 bg-green-50 rounded-lg">
            <span className="font-medium text-green-900">✅ Media Support</span>
            <span className="text-green-700">Active</span>
          </div>
          <div className="flex items-center justify-between p-3 bg-green-50 rounded-lg">
            <span className="font-medium text-green-900">✅ Message Archive</span>
            <span className="text-green-700">Active</span>
          </div>
          <div className="flex items-center justify-between p-3 bg-yellow-50 rounded-lg">
            <span className="font-medium text-yellow-900">⚠️ Message Forwarding</span>
            <span className="text-yellow-700">Planned</span>
          </div>
          <div className="flex items-center justify-between p-3 bg-yellow-50 rounded-lg">
            <span className="font-medium text-yellow-900">⚠️ Monetization</span>
            <span className="text-yellow-700">Planned</span>
          </div>
        </div>
      </div>
    </div>
  );
};

// =================== SUBSCRIPTION MANAGEMENT COMPONENT ===================

const SubscriptionManager = () => {
  const [currentOrg, setCurrentOrg] = useState(null);
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [updatingPlan, setUpdatingPlan] = useState(false);

  useEffect(() => {
    fetchCurrentOrganization();
  }, []);

  const fetchCurrentOrganization = async () => {
    try {
      const response = await axios.get(`${API}/organizations/current`);
      setCurrentOrg(response.data);
    } catch (error) {
      console.error('Error fetching organization:', error);
      setErrorMessage('Failed to load organization details: ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  const updatePlan = async (newPlan) => {
    setUpdatingPlan(true);
    setErrorMessage('');
    setSuccessMessage('');
    
    try {
      const response = await axios.put(`${API}/organizations/current`, {
        name: currentOrg.name,
        description: currentOrg.description,
        plan: newPlan
      });
      
      setCurrentOrg(response.data);
      setSuccessMessage(`Successfully upgraded to ${newPlan.toUpperCase()} plan!`);
      setTimeout(() => setSuccessMessage(''), 5000);
    } catch (error) {
      console.error('Error updating plan:', error);
      setErrorMessage('Failed to update plan: ' + (error.response?.data?.detail || error.message));
    } finally {
      setUpdatingPlan(false);
    }
  };

  const planFeatures = {
    free: [
      'Up to 3 monitored groups',
      'Up to 10 watchlist users',
      'Basic message forwarding',
      '1,000 messages per month',
      'Email support'
    ],
    pro: [
      'Up to 20 monitored groups',
      'Up to 100 watchlist users',
      'Advanced message forwarding',
      'Unlimited messages',
      'Advanced analytics',
      'Priority support',
      'Custom webhooks'
    ],
    enterprise: [
      'Unlimited monitored groups',
      'Unlimited watchlist users',
      'Advanced message forwarding',
      'Unlimited messages',
      'Advanced analytics',
      'Dedicated support',
      'Custom integrations',
      'SLA guarantees',
      'Advanced security features'
    ]
  };

  const planPrices = {
    free: { monthly: 0, yearly: 0 },
    pro: { monthly: 29, yearly: 290 },
    enterprise: { monthly: 99, yearly: 990 }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Subscription Management</h1>
          <p className="text-gray-600">Manage your organization's subscription plan</p>
        </div>
        <div className="text-right">
          <div className="text-sm text-gray-600">Current Plan</div>
          <div className="flex items-center gap-2">
            <Crown className={`w-5 h-5 ${currentOrg?.plan === 'enterprise' ? 'text-purple-600' : currentOrg?.plan === 'pro' ? 'text-blue-600' : 'text-gray-600'}`} />
            <span className="text-xl font-semibold capitalize">{currentOrg?.plan || 'Free'}</span>
          </div>
        </div>
      </div>

      {/* Success/Error Messages */}
      {successMessage && (
        <div className="bg-green-50 border border-green-200 text-green-800 px-4 py-3 rounded-lg">
          ✅ {successMessage}
        </div>
      )}
      {errorMessage && (
        <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-lg">
          ❌ {errorMessage}
        </div>
      )}

      {/* Current Plan Overview */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Current Plan Details</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <h4 className="font-medium text-gray-900 mb-2">Plan Features</h4>
            <ul className="space-y-2">
              {planFeatures[currentOrg?.plan || 'free'].map((feature, index) => (
                <li key={index} className="flex items-center gap-2">
                  <Check className="w-4 h-4 text-green-500" />
                  <span className="text-sm text-gray-600">{feature}</span>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <h4 className="font-medium text-gray-900 mb-2">Usage Statistics</h4>
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Groups:</span>
                <span className="font-medium">{currentOrg?.usage_stats?.total_groups || 0}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Watchlist Users:</span>
                <span className="font-medium">{currentOrg?.usage_stats?.total_users || 0}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Messages:</span>
                <span className="font-medium">{currentOrg?.usage_stats?.total_messages || 0}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Forwarded:</span>
                <span className="font-medium">{currentOrg?.usage_stats?.total_forwarded || 0}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Available Plans */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {Object.entries(planFeatures).map(([plan, features]) => {
          const isCurrentPlan = currentOrg?.plan === plan;
          const isUpgrade = (currentOrg?.plan === 'free' && plan !== 'free') || 
                           (currentOrg?.plan === 'pro' && plan === 'enterprise');
          const isDowngrade = (currentOrg?.plan === 'enterprise' && plan !== 'enterprise') ||
                             (currentOrg?.plan === 'pro' && plan === 'free');
          
          return (
            <div 
              key={plan}
              className={`bg-white rounded-lg shadow-md p-6 border-2 ${
                isCurrentPlan 
                  ? 'border-blue-500 bg-blue-50' 
                  : plan === 'enterprise' 
                    ? 'border-purple-200' 
                    : 'border-gray-200'
              }`}
            >
              <div className="text-center mb-4">
                <div className="flex items-center justify-center gap-2 mb-2">
                  <Crown className={`w-6 h-6 ${
                    plan === 'enterprise' ? 'text-purple-600' : 
                    plan === 'pro' ? 'text-blue-600' : 
                    'text-gray-600'
                  }`} />
                  <h3 className="text-xl font-bold capitalize">{plan}</h3>
                  {isCurrentPlan && (
                    <span className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded-full">Current</span>
                  )}
                </div>
                <div className="text-3xl font-bold text-gray-900">
                  ${planPrices[plan].monthly}
                  <span className="text-lg font-normal text-gray-600">/month</span>
                </div>
                {planPrices[plan].yearly > 0 && (
                  <div className="text-sm text-gray-600">
                    ${planPrices[plan].yearly}/year (save ${planPrices[plan].monthly * 12 - planPrices[plan].yearly})
                  </div>
                )}
              </div>

              <ul className="space-y-2 mb-6">
                {features.map((feature, index) => (
                  <li key={index} className="flex items-start gap-2">
                    <Check className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                    <span className="text-sm text-gray-600">{feature}</span>
                  </li>
                ))}
              </ul>

              <div className="space-y-2">
                {isCurrentPlan ? (
                  <button 
                    disabled
                    className="w-full py-2 px-4 bg-gray-100 text-gray-500 rounded-lg cursor-not-allowed"
                  >
                    Current Plan
                  </button>
                ) : (
                  <>
                    <button
                      onClick={() => updatePlan(plan)}
                      disabled={updatingPlan}
                      className={`w-full py-2 px-4 rounded-lg transition-colors ${
                        isUpgrade
                          ? 'bg-blue-600 hover:bg-blue-700 text-white'
                          : isDowngrade
                          ? 'bg-gray-500 hover:bg-gray-600 text-white'
                          : 'bg-gray-200 hover:bg-gray-300 text-gray-800'
                      } ${updatingPlan ? 'opacity-50 cursor-not-allowed' : ''}`}
                    >
                      {updatingPlan ? (
                        <RefreshCw className="w-4 h-4 animate-spin mx-auto" />
                      ) : (
                        <>
                          {isUpgrade ? 'Upgrade' : isDowngrade ? 'Downgrade' : 'Select'}
                          {plan !== 'free' && ` to ${plan.charAt(0).toUpperCase() + plan.slice(1)}`}
                        </>
                      )}
                    </button>
                    {plan !== 'free' && (
                      <div className="text-xs text-gray-500 text-center">
                        {isUpgrade ? '✨ Instant upgrade' : isDowngrade ? '⚠️ Changes apply at next billing cycle' : ''}
                      </div>
                    )}
                  </>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Billing Information */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Billing Information</h3>
        <div className="bg-blue-50 border border-blue-200 text-blue-800 px-4 py-3 rounded-lg">
          <p className="text-sm">
            <strong>💡 Note:</strong> This is a demo subscription system. In a production environment, 
            this would integrate with payment processors like Stripe for actual billing management.
          </p>
        </div>
      </div>

      {/* Support */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Need Help?</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="p-4 border border-gray-200 rounded-lg">
            <h4 className="font-medium text-gray-900 mb-2">Contact Support</h4>
            <p className="text-sm text-gray-600 mb-3">
              Have questions about plans or need assistance?
            </p>
            <button className="text-sm text-blue-600 hover:text-blue-700">
              Contact Support →
            </button>
          </div>
          <div className="p-4 border border-gray-200 rounded-lg">
            <h4 className="font-medium text-gray-900 mb-2">Documentation</h4>
            <p className="text-sm text-gray-600 mb-3">
              Learn more about features and usage limits
            </p>
            <button className="text-sm text-blue-600 hover:text-blue-700">
              View Docs →
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

// =================== MAIN APP COMPONENT ===================

const MainApp = () => {
  const { user, organization, logout } = useAuth();
  const [activeTab, setActiveTab] = useState('dashboard');

  const renderContent = () => {
    switch (activeTab) {
      case 'dashboard':
        return <Dashboard user={user} />;
      case 'groups':
        return (
          <ProtectedRoute requiredRoles={['owner', 'admin', 'viewer']}>
            <GroupsManager />
          </ProtectedRoute>
        );
      case 'watchlist':
        return (
          <ProtectedRoute requiredRoles={['owner', 'admin', 'viewer']}>
            <WatchlistManager />
          </ProtectedRoute>
        );
      case 'forwarding':
        return (
          <ProtectedRoute requiredRoles={['owner', 'admin', 'viewer']}>
            <ForwardingManager />
          </ProtectedRoute>
        );
      case 'messages':
        return (
          <ProtectedRoute requiredRoles={['owner', 'admin', 'viewer']}>
            <MessagesViewer />
          </ProtectedRoute>
        );
      case 'bot':
        return (
          <ProtectedRoute requiredRoles={['owner', 'admin', 'viewer']}>
            <BotStatus />
          </ProtectedRoute>
        );
      case 'users':
        return (
          <ProtectedRoute requiredRoles={['owner', 'admin']}>
            <UserManagement />
          </ProtectedRoute>
        );
      case 'org-settings':
        return (
          <ProtectedRoute requiredRoles={['owner', 'admin']}>
            <OrganizationSettings />
          </ProtectedRoute>
        );
      case 'settings':
        return (
          <ProtectedRoute requiredRoles={['owner', 'admin', 'viewer']}>
            <SettingsPage />
          </ProtectedRoute>
        );
      default:
        return <Dashboard user={user} />;
    }
  };

  return (
    <div className="flex min-h-screen bg-gray-100">
      <Sidebar 
        activeTab={activeTab} 
        setActiveTab={setActiveTab}
        user={user}
        organization={organization}
        logout={logout}
      />
      <main className="flex-1 p-6">
        {renderContent()}
      </main>
    </div>
  );
};

function App() {
  return (
    <AuthProvider>
      <div className="App">
        <BrowserRouter>
          <Routes>
            <Route 
              path="/*" 
              element={
                <AuthWrapper>
                  <MainApp />
                </AuthWrapper>
              } 
            />
          </Routes>
        </BrowserRouter>
      </div>
    </AuthProvider>
  );
}

export default App;