import type { User } from '@/services/auth-service';
import { faker } from '@faker-js/faker';

/**
 * Mock user data - base admin user
 */
export const mockUser: User = {
  id: "user-123",
  email: "admin@netsentinel.com",
  name: "Security Administrator",
  role: "admin"
};

/**
 * Generate dynamic mock users with different roles and properties
 */
export const generateMockUsers = (count: number = 5): User[] => {
  const roles: Array<'admin' | 'analyst' | 'operator'> = ['admin', 'analyst', 'operator'];

  const users: User[] = [mockUser]; // Always include base admin user

  for (let i = 1; i < count; i++) {
    const role = roles[Math.floor(Math.random() * roles.length)];
    const firstName = faker.person.firstName();
    const lastName = faker.person.lastName();
    const email = `${firstName.toLowerCase()}.${lastName.toLowerCase()}@netsentinel.com`;

    users.push({
      id: `user-${Date.now()}-${i}`,
      email,
      name: `${firstName} ${lastName}`,
      role
    });
  }

  return users;
};

/**
 * Generate user with specific role
 */
export const generateUserByRole = (role: 'admin' | 'analyst' | 'operator'): User => {
  const firstName = faker.person.firstName();
  const lastName = faker.person.lastName();
  const email = `${firstName.toLowerCase()}.${lastName.toLowerCase()}@netsentinel.com`;

  return {
    id: `user-${role}-${Date.now()}`,
    email,
    name: `${firstName} ${lastName}`,
    role
  };
};

/**
 * Mock session response
 */
export const mockSessionResponse = {
  token: `mock-jwt-token-${Date.now()}`,
  user: mockUser
};

/**
 * Generate dynamic session response for different users
 */
export const generateSessionResponse = (user?: User): typeof mockSessionResponse => {
  return {
    token: `mock-jwt-token-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
    user: user || mockUser
  };
};

/**
 * Mock OAuth redirect URL
 */
export const mockOAuthRedirectUrl = {
  url: "https://accounts.google.com/oauth/authorize?client_id=mock-client-id&redirect_uri=http://localhost:8787/auth/callback&scope=email%20profile"
};

/**
 * Generate OAuth URL for different providers
 */
export const generateOAuthUrl = (provider: 'google' | 'github' | 'microsoft' = 'google'): string => {
  const providers = {
    google: 'https://accounts.google.com/oauth/authorize',
    github: 'https://github.com/login/oauth/authorize',
    microsoft: 'https://login.microsoftonline.com/common/oauth2/v2.0/authorize'
  };

  const baseUrl = providers[provider];
  const clientId = `mock-${provider}-client-id`;
  const redirectUri = 'http://localhost:8787/auth/callback';
  const scope = provider === 'google' ? 'email%20profile' :
               provider === 'github' ? 'user:email' : 'openid%20profile%20email';

  return `${baseUrl}?client_id=${clientId}&redirect_uri=${redirectUri}&scope=${scope}`;
};

/**
 * Mock user permissions based on role
 */
export const getUserPermissions = (role: 'admin' | 'analyst' | 'operator'): string[] => {
  const permissions = {
    admin: [
      'read:threats', 'write:threats', 'delete:threats',
      'read:alerts', 'write:alerts', 'delete:alerts',
      'read:reports', 'write:reports',
      'read:users', 'write:users', 'delete:users',
      'read:settings', 'write:settings'
    ],
    analyst: [
      'read:threats', 'read:alerts', 'read:reports',
      'write:reports'
    ],
    operator: [
      'read:threats', 'write:threats',
      'read:alerts', 'write:alerts'
    ]
  };

  return permissions[role] || [];
};
