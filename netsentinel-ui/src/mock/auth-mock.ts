import type { User } from '@/services/auth-service';

/**
 * Mock user data
 */
export const mockUser: User = {
  id: "user-123",
  email: "admin@Netsentinel.com",
  name: "Security Administrator",
  role: "admin"
};

/**
 * Mock session response
 */
export const mockSessionResponse = {
  token: "mock-jwt-token-12345",
  user: mockUser
};

/**
 * Mock OAuth redirect URL
 */
export const mockOAuthRedirectUrl = {
  url: "https://accounts.google.com/oauth/authorize?client_id=mock-client-id&redirect_uri=http://localhost:8787/auth/callback&scope=email%20profile"
};
