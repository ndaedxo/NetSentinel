import { NotificationItem, mockNotificationsResponse, getUnreadCount } from "@/mock";

export interface NotificationsResponse {
  notifications: NotificationItem[];
  total: number;
  unread: number;
  page: number;
  limit: number;
}

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
export async function markNotificationAsRead(notificationId: string): Promise<{ success: boolean }> {
  // Simulate API delay
  await new Promise(resolve => setTimeout(resolve, 200));

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
export async function deleteNotification(notificationId: string): Promise<{ success: boolean }> {
  // Simulate API delay
  await new Promise(resolve => setTimeout(resolve, 200));

  return { success: true };
}
