import { mockNotificationsResponse } from "@/mock";
import type { NotificationPreferences, ChannelConfig, NotificationsResponse } from '@/types';

/**
 * Get user notifications
 */
export async function getUserNotifications(page: number = 1, limit: number = 50): Promise<NotificationsResponse> {
  // Simulate API delay
  await new Promise(resolve => setTimeout(resolve, 300));

  // For now, return all notifications (in real app, this would be paginated)
  return {
    ...mockNotificationsResponse,
    page,
    limit
  };
}

/**
 * Mark notification as read
 */
export async function markNotificationAsRead(_notificationId: string): Promise<{ success: boolean }> {
  // Simulate API delay
  await new Promise(resolve => setTimeout(resolve, 200));
  void _notificationId;

  return { success: true };
}

/**
 * Mark all notifications as read
 */
export async function markAllNotificationsAsRead(): Promise<{ success: boolean }> {
  // Simulate API delay
  await new Promise(resolve => setTimeout(resolve, 300));

  return { success: true };
}

/**
 * Delete notification
 */
export async function deleteNotification(_notificationId: string): Promise<{ success: boolean }> {
  // Simulate API delay
  await new Promise(resolve => setTimeout(resolve, 200));
  void _notificationId;

  return { success: true };
}

// Mock in-memory prefs
let prefs: NotificationPreferences = {
  emailEnabled: true,
  smsEnabled: false,
  slackEnabled: false,
  severities: ['high','critical'],
};
let channels: ChannelConfig = {
  email: { from: 'alerts@netsentinel.local' },
};

export async function getNotificationPreferences(): Promise<NotificationPreferences> {
  await new Promise(r => setTimeout(r, 150));
  return { ...prefs };
}

export async function updateNotificationPreferences(update: Partial<NotificationPreferences>): Promise<NotificationPreferences> {
  await new Promise(r => setTimeout(r, 200));
  prefs = { ...prefs, ...update };
  return { ...prefs };
}

export async function getChannelConfig(): Promise<ChannelConfig> {
  await new Promise(r => setTimeout(r, 150));
  return { ...channels };
}

export async function updateChannelConfig(update: Partial<ChannelConfig>): Promise<ChannelConfig> {
  await new Promise(r => setTimeout(r, 200));
  channels = { ...channels, ...update };
  return { ...channels };
}
