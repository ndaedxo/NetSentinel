import { faker } from '@faker-js/faker';

export interface UserProfile {
  id: string;
  email: string;
  name: string;
  role: 'admin' | 'analyst' | 'operator';
  avatar?: string;
  bio?: string;
  phone?: string;
  department?: string;
  location?: string;
  timezone: string;
  language: string;
  theme: 'light' | 'dark' | 'auto';
  notifications: {
    email: boolean;
    push: boolean;
    sms: boolean;
    threatAlerts: boolean;
    systemAlerts: boolean;
    weeklyReports: boolean;
  };
  security: {
    twoFactorEnabled: boolean;
    lastPasswordChange: string;
    loginAttempts: number;
    accountLocked: boolean;
  };
  preferences: {
    dashboardLayout: 'grid' | 'list';
    itemsPerPage: number;
    autoRefresh: boolean;
    refreshInterval: number;
  };
  createdAt: string;
  updatedAt: string;
}

/**
 * Mock user profile data
 */
export const mockUserProfile: UserProfile = {
  id: "user-123",
  email: "admin@netsentinel.com",
  name: "Security Administrator",
  role: "admin",
  avatar: `https://api.dicebear.com/7.x/avataaars/svg?seed=${faker.string.uuid()}`,
  bio: "Experienced cybersecurity professional with over 10 years in threat detection and incident response.",
  phone: "+1 (555) 123-4567",
  department: "Security Operations Center",
  location: "New York, NY",
  timezone: "America/New_York",
  language: "en-US",
  theme: "dark",
  notifications: {
    email: true,
    push: true,
    sms: false,
    threatAlerts: true,
    systemAlerts: true,
    weeklyReports: true,
  },
  security: {
    twoFactorEnabled: true,
    lastPasswordChange: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString(), // 30 days ago
    loginAttempts: 0,
    accountLocked: false,
  },
  preferences: {
    dashboardLayout: 'grid',
    itemsPerPage: 25,
    autoRefresh: true,
    refreshInterval: 30000, // 30 seconds
  },
  createdAt: new Date(Date.now() - 365 * 24 * 60 * 60 * 1000).toISOString(), // 1 year ago
  updatedAt: new Date().toISOString(),
};

/**
 * Generate mock profile for different users
 */
export const generateUserProfile = (userId: string, email: string, name: string, role: 'admin' | 'analyst' | 'operator' = 'analyst'): UserProfile => {
  const departments = {
    admin: ['Security Operations Center', 'IT Security', 'Risk Management'],
    analyst: ['Threat Intelligence', 'Incident Response', 'Network Security'],
    operator: ['SOC Operations', 'Monitoring', 'Support']
  };

  const locations = ['New York, NY', 'San Francisco, CA', 'Austin, TX', 'London, UK', 'Berlin, DE'];

  return {
    id: userId,
    email,
    name,
    role,
    avatar: `https://api.dicebear.com/7.x/avataaars/svg?seed=${faker.string.uuid()}`,
    bio: faker.lorem.sentence(),
    phone: faker.phone.number(),
    department: faker.helpers.arrayElement(departments[role]),
    location: faker.helpers.arrayElement(locations),
    timezone: faker.helpers.arrayElement([
      'America/New_York',
      'America/Los_Angeles',
      'Europe/London',
      'Europe/Berlin',
      'Asia/Tokyo'
    ]),
    language: faker.helpers.arrayElement(['en-US', 'en-GB', 'de-DE', 'fr-FR', 'es-ES']),
    theme: faker.helpers.arrayElement(['light', 'dark', 'auto']),
    notifications: {
      email: faker.datatype.boolean(),
      push: faker.datatype.boolean(),
      sms: faker.datatype.boolean(),
      threatAlerts: faker.datatype.boolean(),
      systemAlerts: faker.datatype.boolean(),
      weeklyReports: faker.datatype.boolean(),
    },
    security: {
      twoFactorEnabled: faker.datatype.boolean(),
      lastPasswordChange: faker.date.recent(90).toISOString(),
      loginAttempts: faker.number.int({ min: 0, max: 5 }),
      accountLocked: faker.datatype.boolean({ probability: 0.1 }),
    },
    preferences: {
      dashboardLayout: faker.helpers.arrayElement(['grid', 'list']),
      itemsPerPage: faker.helpers.arrayElement([10, 25, 50, 100]),
      autoRefresh: faker.datatype.boolean(),
      refreshInterval: faker.helpers.arrayElement([15000, 30000, 60000, 300000]), // 15s, 30s, 1min, 5min
    },
    createdAt: faker.date.past(2).toISOString(),
    updatedAt: faker.date.recent(30).toISOString(),
  };
};

/**
 * Mock profile update response
 */
export const mockProfileUpdateResponse = {
  success: true,
  message: "Profile updated successfully",
  profile: mockUserProfile,
};

/**
 * Mock password change response
 */
export const mockPasswordChangeResponse = {
  success: true,
  message: "Password changed successfully",
  lastPasswordChange: new Date().toISOString(),
};
