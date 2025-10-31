import { useEffect, useState, useCallback } from 'react';
import { PageLayout } from '@/components';
import { UserProfile } from '@/mock';
import { getUserProfile, updateUserProfile } from '@/services';
import { useToast } from '@/hooks';

export default function Profile() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [formData, setFormData] = useState<Partial<UserProfile>>({});

  const { showToast } = useToast();

  const loadProfile = useCallback(async () => {
    try {
      const data = await getUserProfile();
      setProfile(data);
      setFormData(data);
    } catch {
      showToast('error', 'Failed to load profile');
    } finally {
      setLoading(false);
    }
  }, [showToast]);

  useEffect(() => {
    loadProfile();
  }, [loadProfile]);

  const handleInputChange = (field: keyof UserProfile, value: string) => {
    // Handle different field types appropriately
    if (field === 'role') {
      setFormData(prev => ({ ...prev, [field]: value as UserProfile['role'] }));
    } else if (field === 'theme') {
      setFormData(prev => ({ ...prev, [field]: value as UserProfile['theme'] }));
    } else {
      setFormData(prev => ({ ...prev, [field]: value }));
    }
  };

  const handleSave = async () => {
    if (!profile) return;

    setSaving(true);
    try {
      const updated = await updateUserProfile(formData);
      setProfile(updated);
      showToast('success', 'Profile updated successfully');
    } catch {
      showToast('error', 'Failed to update profile');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <PageLayout title="Profile Settings" subtitle="Manage your account settings">
        <div className="flex justify-center items-center h-64">
          <div className="text-slate-400">Loading profile...</div>
        </div>
      </PageLayout>
    );
  }

  if (!profile) {
    return (
      <PageLayout title="Profile Settings" subtitle="Manage your account settings">
        <div className="flex justify-center items-center h-64">
          <div className="text-red-400">Failed to load profile</div>
        </div>
      </PageLayout>
    );
  }

  return (
    <PageLayout title="Profile Settings" subtitle="Manage your account settings">
      <div className="max-w-4xl mx-auto space-mobile-y">
        {/* Profile Header */}
        <div className="bg-slate-900/60 border border-slate-700/50 rounded-lg p-4 md:p-6">
          <div className="flex flex-col md:flex-row items-start md:items-center space-y-4 md:space-y-0 md:space-x-6">
            {/* Avatar Section */}
            <div className="relative">
              {profile.avatar ? (
                <img
                  src={profile.avatar}
                  alt="Profile avatar"
                  className="w-20 h-20 rounded-full border-2 border-slate-600"
                />
              ) : (
                <div className="w-20 h-20 rounded-full bg-slate-700 flex items-center justify-center">
                  <span className="text-slate-400 text-2xl font-semibold">
                    {profile.name.charAt(0).toUpperCase()}
                  </span>
                </div>
              )}
            </div>

            {/* Basic Info */}
            <div className="flex-1">
              <h2 className="text-xl font-semibold text-white">{profile.name}</h2>
              <p className="text-slate-400">{profile.email}</p>
              <p className="text-slate-500 text-sm capitalize">{profile.role}</p>
              {profile.bio && (
                <p className="text-slate-300 mt-2">{profile.bio}</p>
              )}
            </div>
          </div>
        </div>

        {/* Profile Form */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Personal Information */}
          <div className="bg-slate-900/60 border border-slate-700/50 rounded-lg p-4 md:p-6">
            <h3 className="text-mobile-responsive-lg font-semibold text-white mb-4">Personal Information</h3>
            <div className="space-mobile-y">
              <div>
                <label htmlFor="name" className="block text-sm font-medium text-slate-300 mb-2">
                  Full Name
                </label>
                <input
                  id="name"
                  type="text"
                  className="w-full px-4 py-3 bg-slate-800 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-blue-500 text-base"
                  value={formData.name || ''}
                  onChange={(e) => handleInputChange('name', e.target.value)}
                />
              </div>

              <div>
                <label htmlFor="email" className="block text-sm font-medium text-slate-300 mb-2">
                  Email
                </label>
                <input
                  id="email"
                  type="email"
                  className="w-full px-4 py-3 bg-slate-800 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-blue-500 text-base"
                  value={formData.email || ''}
                  onChange={(e) => handleInputChange('email', e.target.value)}
                />
              </div>

              <div>
                <label htmlFor="phone" className="block text-sm font-medium text-slate-300 mb-2">
                  Phone
                </label>
                <input
                  id="phone"
                  type="tel"
                  className="w-full px-4 py-3 bg-slate-800 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-blue-500 text-base"
                  value={formData.phone || ''}
                  onChange={(e) => handleInputChange('phone', e.target.value)}
                />
              </div>

              <div>
                <label htmlFor="bio" className="block text-sm font-medium text-slate-300 mb-2">
                  Bio
                </label>
                <textarea
                  id="bio"
                  rows={3}
                  className="w-full px-4 py-3 bg-slate-800 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-blue-500 text-base resize-none"
                  value={formData.bio || ''}
                  onChange={(e) => handleInputChange('bio', e.target.value)}
                  placeholder="Tell us about yourself..."
                />
              </div>
            </div>
          </div>

          {/* Professional Information */}
          <div className="bg-slate-900/60 border border-slate-700/50 rounded-lg p-4 md:p-6">
            <h3 className="text-mobile-responsive-lg font-semibold text-white mb-4">Professional Information</h3>
            <div className="space-mobile-y">
              <div>
                <label htmlFor="department" className="block text-sm font-medium text-slate-300 mb-2">
                  Department
                </label>
                <input
                  id="department"
                  type="text"
                  className="w-full px-4 py-3 bg-slate-800 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-blue-500 text-base"
                  value={formData.department || ''}
                  onChange={(e) => handleInputChange('department', e.target.value)}
                />
              </div>

              <div>
                <label htmlFor="location" className="block text-sm font-medium text-slate-300 mb-2">
                  Location
                </label>
                <input
                  id="location"
                  type="text"
                  className="w-full px-4 py-3 bg-slate-800 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-blue-500 text-base"
                  value={formData.location || ''}
                  onChange={(e) => handleInputChange('location', e.target.value)}
                />
              </div>

              <div>
                <label htmlFor="role" className="block text-sm font-medium text-slate-300 mb-2">
                  Role
                </label>
                <select
                  id="role"
                  className="w-full px-4 py-3 bg-slate-800 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-blue-500 text-base"
                  value={formData.role || ''}
                  onChange={(e) => handleInputChange('role', e.target.value)}
                >
                  <option value="admin">Administrator</option>
                  <option value="analyst">Analyst</option>
                  <option value="operator">Operator</option>
                </select>
              </div>
            </div>
          </div>
        </div>

        {/* Preferences */}
        <div className="bg-slate-900/60 border border-slate-700/50 rounded-lg p-4 md:p-6">
          <h3 className="text-mobile-responsive-lg font-semibold text-white mb-4">Preferences</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 md:gap-6">
            <div>
              <label htmlFor="theme" className="block text-sm font-medium text-slate-300 mb-2">
                Theme
              </label>
              <select
                id="theme"
                className="w-full px-4 py-3 bg-slate-800 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-blue-500 text-base"
                value={formData.theme || 'dark'}
                onChange={(e) => handleInputChange('theme', e.target.value)}
              >
                <option value="light">Light</option>
                <option value="dark">Dark</option>
                <option value="auto">Auto</option>
              </select>
            </div>

            <div>
              <label htmlFor="language" className="block text-sm font-medium text-slate-300 mb-2">
                Language
              </label>
              <select
                id="language"
                className="w-full px-4 py-3 bg-slate-800 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-blue-500 text-base"
                value={formData.language || 'en-US'}
                onChange={(e) => handleInputChange('language', e.target.value)}
              >
                <option value="en-US">English (US)</option>
                <option value="en-GB">English (UK)</option>
                <option value="de-DE">Deutsch</option>
                <option value="fr-FR">Français</option>
                <option value="es-ES">Español</option>
              </select>
            </div>
          </div>
        </div>

        {/* Save Button */}
        <div className="flex justify-end">
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed text-base font-medium min-h-[44px]"
          >
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </div>
    </PageLayout>
  );
}