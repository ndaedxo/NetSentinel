import { useState } from "react";
import { UserProfile } from "@/mock";
import { useApi } from "@/hooks";
import { PageLayout } from "@/components";
import {
  User,
  Mail,
  Phone,
  MapPin,
  Clock,
  Shield,
  Bell,
  Settings,
  Save,
  Edit,
  Camera,
  Key,
  Eye,
  EyeOff,
  Globe,
  Palette
} from "lucide-react";

export default function ProfilePage() {
  const { data: profile, refetch } = useApi<UserProfile>("/api/profile", 0);
  const [isEditing, setIsEditing] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [formData, setFormData] = useState<Partial<UserProfile>>({});
  const [activeTab, setActiveTab] = useState<'personal' | 'preferences' | 'security' | 'notifications'>('personal');

  const handleSave = async () => {
    try {
      // Mock API call - in real app this would save to backend
      console.log('Saving profile:', formData);
      setIsEditing(false);
      refetch();
    } catch (error) {
      console.error('Failed to save profile:', error);
    }
  };

  const handleInputChange = (field: string, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  if (!profile) {
    return (
      <PageLayout>
        <div className="flex items-center justify-center h-64">
          <div className="flex flex-col items-center space-y-4">
            <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
            <p className="text-slate-400">Loading profile...</p>
          </div>
        </div>
      </PageLayout>
    );
  }

  return (
    <PageLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div className="relative">
              <div className="absolute inset-0 bg-blue-500 blur-lg opacity-30"></div>
              <User className="relative w-8 h-8 text-blue-400" strokeWidth={1.5} />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-white">Profile Settings</h1>
              <p className="text-slate-400">Manage your account and preferences</p>
            </div>
          </div>
          <button
            onClick={() => setIsEditing(!isEditing)}
            className={`flex items-center space-x-2 px-4 py-2 rounded-lg transition-colors ${
              isEditing
                ? 'bg-green-600 hover:bg-green-500 text-white'
                : 'bg-blue-600 hover:bg-blue-500 text-white'
            }`}
          >
            {isEditing ? <Save className="w-4 h-4" /> : <Edit className="w-4 h-4" />}
            <span>{isEditing ? 'Save Changes' : 'Edit Profile'}</span>
          </button>
        </div>

        {/* Profile Avatar and Basic Info */}
        <div className="card-dark p-6">
          <div className="flex items-start space-x-6">
            <div className="relative">
              <div className="w-24 h-24 rounded-full bg-slate-700 flex items-center justify-center">
                {profile.avatar ? (
                  <img
                    src={profile.avatar}
                    alt={profile.name}
                    className="w-full h-full rounded-full object-cover"
                  />
                ) : (
                  <User className="w-12 h-12 text-slate-400" />
                )}
              </div>
              {isEditing && (
                <button className="absolute bottom-0 right-0 w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center hover:bg-blue-500 transition-colors">
                  <Camera className="w-4 h-4 text-white" />
                </button>
              )}
            </div>
            <div className="flex-1 space-y-4">
              <div>
                <h2 className="text-xl font-semibold text-white">{profile.name}</h2>
                <p className="text-slate-400">{profile.role.charAt(0).toUpperCase() + profile.role.slice(1)}</p>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="flex items-center space-x-2 text-slate-300">
                  <Mail className="w-4 h-4 text-slate-400" />
                  <span>{profile.email}</span>
                </div>
                <div className="flex items-center space-x-2 text-slate-300">
                  <MapPin className="w-4 h-4 text-slate-400" />
                  <span>{profile.location || 'Not specified'}</span>
                </div>
                <div className="flex items-center space-x-2 text-slate-300">
                  <Clock className="w-4 h-4 text-slate-400" />
                  <span>{profile.timezone}</span>
                </div>
                <div className="flex items-center space-x-2 text-slate-300">
                  <Globe className="w-4 h-4 text-slate-400" />
                  <span>{profile.language}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="border-b border-slate-700">
          <nav className="flex space-x-8">
            {[
              { id: 'personal', label: 'Personal Info', icon: User },
              { id: 'preferences', label: 'Preferences', icon: Settings },
              { id: 'security', label: 'Security', icon: Shield },
              { id: 'notifications', label: 'Notifications', icon: Bell },
            ].map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => setActiveTab(id as any)}
                className={`flex items-center space-x-2 py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                  activeTab === id
                    ? 'border-blue-500 text-blue-400'
                    : 'border-transparent text-slate-400 hover:text-slate-300'
                }`}
              >
                <Icon className="w-4 h-4" />
                <span>{label}</span>
              </button>
            ))}
          </nav>
        </div>

        {/* Tab Content */}
        <div className="space-y-6">
          {/* Personal Info Tab */}
          {activeTab === 'personal' && (
            <div className="card-dark p-6">
              <h3 className="text-lg font-semibold text-white mb-4">Personal Information</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">Full Name</label>
                  {isEditing ? (
                    <input
                      type="text"
                      value={formData.name || profile.name}
                      onChange={(e) => handleInputChange('name', e.target.value)}
                      className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-blue-500"
                    />
                  ) : (
                    <p className="text-slate-400">{profile.name}</p>
                  )}
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">Email</label>
                  <p className="text-slate-400">{profile.email}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">Phone</label>
                  {isEditing ? (
                    <input
                      type="tel"
                      value={formData.phone || profile.phone || ''}
                      onChange={(e) => handleInputChange('phone', e.target.value)}
                      className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-blue-500"
                    />
                  ) : (
                    <p className="text-slate-400">{profile.phone || 'Not specified'}</p>
                  )}
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">Department</label>
                  {isEditing ? (
                    <input
                      type="text"
                      value={formData.department || profile.department || ''}
                      onChange={(e) => handleInputChange('department', e.target.value)}
                      className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-blue-500"
                    />
                  ) : (
                    <p className="text-slate-400">{profile.department || 'Not specified'}</p>
                  )}
                </div>
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-slate-300 mb-2">Bio</label>
                  {isEditing ? (
                    <textarea
                      value={formData.bio || profile.bio || ''}
                      onChange={(e) => handleInputChange('bio', e.target.value)}
                      rows={3}
                      className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-blue-500"
                      placeholder="Tell us about yourself..."
                    />
                  ) : (
                    <p className="text-slate-400">{profile.bio || 'No bio provided'}</p>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Preferences Tab */}
          {activeTab === 'preferences' && (
            <div className="card-dark p-6">
              <h3 className="text-lg font-semibold text-white mb-4">Preferences</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">Theme</label>
                  {isEditing ? (
                    <select
                      value={formData.theme || profile.theme}
                      onChange={(e) => handleInputChange('theme', e.target.value)}
                      className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-blue-500"
                    >
                      <option value="light">Light</option>
                      <option value="dark">Dark</option>
                      <option value="auto">Auto</option>
                    </select>
                  ) : (
                    <p className="text-slate-400 capitalize">{profile.theme}</p>
                  )}
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">Language</label>
                  {isEditing ? (
                    <select
                      value={formData.language || profile.language}
                      onChange={(e) => handleInputChange('language', e.target.value)}
                      className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-blue-500"
                    >
                      <option value="en-US">English (US)</option>
                      <option value="en-GB">English (UK)</option>
                      <option value="de-DE">Deutsch</option>
                      <option value="fr-FR">Français</option>
                      <option value="es-ES">Español</option>
                    </select>
                  ) : (
                    <p className="text-slate-400">{profile.language}</p>
                  )}
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">Dashboard Layout</label>
                  {isEditing ? (
                    <select
                      value={formData.preferences?.dashboardLayout || profile.preferences.dashboardLayout}
                      onChange={(e) => handleInputChange('preferences', { ...profile.preferences, dashboardLayout: e.target.value })}
                      className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-blue-500"
                    >
                      <option value="grid">Grid</option>
                      <option value="list">List</option>
                    </select>
                  ) : (
                    <p className="text-slate-400 capitalize">{profile.preferences.dashboardLayout}</p>
                  )}
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">Items Per Page</label>
                  {isEditing ? (
                    <select
                      value={formData.preferences?.itemsPerPage || profile.preferences.itemsPerPage}
                      onChange={(e) => handleInputChange('preferences', { ...profile.preferences, itemsPerPage: parseInt(e.target.value) })}
                      className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-blue-500"
                    >
                      <option value={10}>10</option>
                      <option value={25}>25</option>
                      <option value={50}>50</option>
                      <option value={100}>100</option>
                    </select>
                  ) : (
                    <p className="text-slate-400">{profile.preferences.itemsPerPage}</p>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Security Tab */}
          {activeTab === 'security' && (
            <div className="space-y-6">
              <div className="card-dark p-6">
                <h3 className="text-lg font-semibold text-white mb-4">Security Settings</h3>
                <div className="space-y-4">
                  <div className="flex items-center justify-between p-4 bg-slate-800/50 rounded-lg">
                    <div>
                      <p className="text-white font-medium">Two-Factor Authentication</p>
                      <p className="text-slate-400 text-sm">Add an extra layer of security to your account</p>
                    </div>
                    <div className="flex items-center space-x-2">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        profile.security.twoFactorEnabled
                          ? 'bg-green-100 text-green-800'
                          : 'bg-red-100 text-red-800'
                      }`}>
                        {profile.security.twoFactorEnabled ? 'Enabled' : 'Disabled'}
                      </span>
                      {isEditing && (
                        <button className="text-blue-400 hover:text-blue-300 text-sm">
                          Configure
                        </button>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center justify-between p-4 bg-slate-800/50 rounded-lg">
                    <div>
                      <p className="text-white font-medium">Change Password</p>
                      <p className="text-slate-400 text-sm">Last changed {new Date(profile.security.lastPasswordChange).toLocaleDateString()}</p>
                    </div>
                    {isEditing && (
                      <button className="text-blue-400 hover:text-blue-300 text-sm">
                        Change Password
                      </button>
                    )}
                  </div>

                  <div className="flex items-center justify-between p-4 bg-slate-800/50 rounded-lg">
                    <div>
                      <p className="text-white font-medium">Login Activity</p>
                      <p className="text-slate-400 text-sm">{profile.security.loginAttempts} recent login attempts</p>
                    </div>
                    <button className="text-blue-400 hover:text-blue-300 text-sm">
                      View History
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Notifications Tab */}
          {activeTab === 'notifications' && (
            <div className="card-dark p-6">
              <h3 className="text-lg font-semibold text-white mb-4">Notification Preferences</h3>
              <div className="space-y-4">
                {Object.entries(profile.notifications).map(([key, value]) => (
                  <div key={key} className="flex items-center justify-between p-4 bg-slate-800/50 rounded-lg">
                    <div>
                      <p className="text-white font-medium capitalize">
                        {key.replace(/([A-Z])/g, ' $1').trim()}
                      </p>
                      <p className="text-slate-400 text-sm">
                        {key === 'email' && 'Receive notifications via email'}
                        {key === 'push' && 'Receive push notifications in browser'}
                        {key === 'sms' && 'Receive notifications via SMS'}
                        {key === 'threatAlerts' && 'Get notified of new threats and alerts'}
                        {key === 'systemAlerts' && 'Get notified of system status changes'}
                        {key === 'weeklyReports' && 'Receive weekly summary reports'}
                      </p>
                    </div>
                    {isEditing ? (
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          checked={formData.notifications?.[key as keyof typeof profile.notifications] ?? value}
                          onChange={(e) => handleInputChange('notifications', {
                            ...profile.notifications,
                            [key]: e.target.checked
                          })}
                          className="sr-only peer"
                        />
                        <div className="w-11 h-6 bg-slate-600 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                      </label>
                    ) : (
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        value
                          ? 'bg-green-100 text-green-800'
                          : 'bg-slate-100 text-slate-800'
                      }`}>
                        {value ? 'Enabled' : 'Disabled'}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Save/Cancel Buttons */}
        {isEditing && (
          <div className="flex justify-end space-x-4">
            <button
              onClick={() => {
                setIsEditing(false);
                setFormData({});
              }}
              className="px-4 py-2 text-slate-400 hover:text-slate-300 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition-colors"
            >
              Save Changes
            </button>
          </div>
        )}
      </div>
    </PageLayout>
  );
}
