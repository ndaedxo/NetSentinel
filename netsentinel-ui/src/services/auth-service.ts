/**
 * User interface
 */
export interface User {
  id: string;
  email: string;
  name?: string;
  role?: string;
}

/**
 * Login request data
 */
export interface LoginData {
  email: string;
  password: string;
}

/**
 * Session response
 */
export interface SessionResponse {
  token: string;
  user: User;
}

/**
 * Get Google OAuth redirect URL
 */
export async function getGoogleOAuthRedirectUrl(): Promise<{ url: string }> {
  // Authentication disabled for development
  return { url: "#" };
}

/**
 * Create a new session (login)
 */
export async function createSession(loginData: LoginData): Promise<SessionResponse> {
  // Authentication disabled for development
  const mockUser: User = {
    id: "demo-user",
    email: loginData.email,
    name: "Demo User",
    role: "admin"
  };

  return {
    token: "demo-token",
    user: mockUser
  };
}

/**
 * Get current user information
 */
export async function getCurrentUser(): Promise<User> {
  // Authentication disabled for development
  return {
    id: "demo-user",
    email: "demo@example.com",
    name: "Demo User",
    role: "admin"
  };
}

/**
 * Logout current user
 */
export async function logout(): Promise<void> {
  // Authentication disabled for development
  console.log("Logout called - authentication disabled");
}
