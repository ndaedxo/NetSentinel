import { UserProfile, mockUserProfile } from "@/mock";

/**
 * Get user profile data
 */
export async function getUserProfile(): Promise<UserProfile> {
  // Simulate API delay
  await new Promise(resolve => setTimeout(resolve, 500));

  return mockUserProfile;
}

/**
 * Update user profile
 */
export async function updateUserProfile(updates: Partial<UserProfile>): Promise<UserProfile> {
  // Simulate API delay
  await new Promise(resolve => setTimeout(resolve, 500));

  // Merge updates with existing profile
  const updatedProfile = { ...mockUserProfile, ...updates, updatedAt: new Date().toISOString() };

  return updatedProfile;
}

/**
 * Change user password
 */
export async function changePassword(currentPassword: string, newPassword: string): Promise<{ success: boolean; message: string }> {
  // Simulate API delay
  await new Promise(resolve => setTimeout(resolve, 1000));

  // Mock validation - in real app this would validate current password
  if (currentPassword.length < 8) {
    throw new Error("Current password is incorrect");
  }

  if (newPassword.length < 8) {
    throw new Error("New password must be at least 8 characters");
  }

  return {
    success: true,
    message: "Password changed successfully"
  };
}
