import { faker } from '@faker-js/faker';

export type NotificationType = 'threat' | 'system' | 'alert' | 'report' | 'maintenance' | 'security';

export type NotificationPriority = 'low' | 'medium' | 'high' | 'critical';

export interface NotificationItem {
  id: string;
  type: NotificationType;
  priority: NotificationPriority;
  title: string;
  message: string;
  read: boolean;
  createdAt: string;
  userId: string;
  metadata?: {
    threatId?: string;
    alertId?: string;
    reportId?: string;
    actionUrl?: string;
    [key: string]: any;
  };
}

/**
 * Mock notification data
 */
const generateNotification = (
  type: NotificationType,
  priority: NotificationPriority,
  title: string,
  message: string,
  metadata?: any
): Omit<NotificationItem, 'id' | 'read' | 'createdAt' | 'userId'> => ({
  type,
  priority,
  title,
  message,
  metadata,
});

/**
 * Generate mock notifications
 */
export const generateMockNotifications = (count: number = 50): NotificationItem[] => {
  const notifications: NotificationItem[] = [];

  const threatNotifications = [
    generateNotification('threat', 'critical', 'Critical Threat Detected', 'High-priority threat detected from IP 192.168.1.100 targeting port 443', { threatId: 'threat-001', actionUrl: '/threats' }),
    generateNotification('threat', 'high', 'Suspicious Activity', 'Multiple failed login attempts detected from unknown IP', { threatId: 'threat-002', actionUrl: '/threats' }),
    generateNotification('threat', 'medium', 'Potential Malware', 'File upload detected with suspicious signatures', { threatId: 'threat-003', actionUrl: '/threats' }),
    generateNotification('threat', 'low', 'Traffic Anomaly', 'Unusual traffic pattern detected on network segment', { threatId: 'threat-004', actionUrl: '/network' }),
  ];

  const systemNotifications = [
    generateNotification('system', 'medium', 'System Update Available', 'Security update v2.1.4 is available for deployment', { actionUrl: '/reports' }),
    generateNotification('system', 'low', 'Backup Completed', 'Daily system backup completed successfully', {}),
    generateNotification('system', 'high', 'Disk Space Warning', 'Server disk usage is above 85%', { actionUrl: '/reports' }),
    generateNotification('system', 'medium', 'Service Restarted', 'Honeypot service has been automatically restarted', { actionUrl: '/honeypots' }),
  ];

  const alertNotifications = [
    generateNotification('alert', 'high', 'Alert Threshold Exceeded', 'CPU usage alert: Server load exceeds 90%', { alertId: 'alert-001', actionUrl: '/alerts' }),
    generateNotification('alert', 'medium', 'Network Latency', 'Network latency increased by 25% in the last hour', { alertId: 'alert-002', actionUrl: '/network' }),
    generateNotification('alert', 'low', 'Scheduled Maintenance', 'System maintenance scheduled for tonight at 2 AM', { actionUrl: '/reports' }),
  ];

  const reportNotifications = [
    generateNotification('report', 'low', 'Weekly Report Generated', 'Your weekly security report is now available', { reportId: 'report-001', actionUrl: '/reports' }),
    generateNotification('report', 'low', 'Monthly Analytics Ready', 'Monthly threat analytics report has been generated', { reportId: 'report-002', actionUrl: '/reports' }),
  ];

  const maintenanceNotifications = [
    generateNotification('maintenance', 'medium', 'Scheduled Maintenance', 'System maintenance window starts in 2 hours', { actionUrl: '/reports' }),
    generateNotification('maintenance', 'low', 'Component Update', 'ML model updated to version 3.2.1', { actionUrl: '/ml-models' }),
  ];

  const securityNotifications = [
    generateNotification('security', 'critical', 'Security Policy Violation', 'Unauthorized access attempt blocked', {}),
    generateNotification('security', 'high', 'Password Expiry', 'Your password will expire in 3 days', { actionUrl: '/profile' }),
    generateNotification('security', 'medium', 'New Login Detected', 'New login from Chrome browser on Windows', {}),
  ];

  const allNotificationTemplates = [
    ...threatNotifications,
    ...systemNotifications,
    ...alertNotifications,
    ...reportNotifications,
    ...maintenanceNotifications,
    ...securityNotifications,
  ];

  for (let i = 0; i < count; i++) {
    const template = faker.helpers.arrayElement(allNotificationTemplates);
    const isRead = faker.datatype.boolean({ probability: 0.7 }); // 70% read
    const daysAgo = faker.number.int({ min: 0, max: 30 });

    notifications.push({
      id: `notification-${Date.now()}-${i}`,
      ...template,
      read: isRead,
      createdAt: new Date(Date.now() - daysAgo * 24 * 60 * 60 * 1000).toISOString(),
      userId: 'user-123',
    });
  }

  // Sort by creation date (newest first)
  return notifications.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());
};

/**
 * Mock notifications data
 */
export const mockNotifications = generateMockNotifications(35);

/**
 * Get unread notifications count
 */
export const getUnreadCount = (notifications: NotificationItem[]): number => {
  return notifications.filter(n => !n.read).length;
};

/**
 * Mark notification as read
 */
export const markAsRead = (notificationId: string, notifications: NotificationItem[]): NotificationItem[] => {
  return notifications.map(n =>
    n.id === notificationId ? { ...n, read: true } : n
  );
};

/**
 * Mark all notifications as read
 */
export const markAllAsRead = (notifications: NotificationItem[]): NotificationItem[] => {
  return notifications.map(n => ({ ...n, read: true }));
};

/**
 * Delete notification
 */
export const deleteNotification = (notificationId: string, notifications: NotificationItem[]): NotificationItem[] => {
  return notifications.filter(n => n.id !== notificationId);
};

/**
 * Filter notifications by type
 */
export const filterByType = (type: NotificationType, notifications: NotificationItem[]): NotificationItem[] => {
  return notifications.filter(n => n.type === type);
};

/**
 * Filter notifications by priority
 */
export const filterByPriority = (priority: NotificationPriority, notifications: NotificationItem[]): NotificationItem[] => {
  return notifications.filter(n => n.priority === priority);
};

/**
 * Get notifications by read status
 */
export const getByReadStatus = (read: boolean, notifications: NotificationItem[]): NotificationItem[] => {
  return notifications.filter(n => n.read === read);
};

/**
 * Mock API response for notifications
 */
export const mockNotificationsResponse = {
  notifications: mockNotifications,
  total: mockNotifications.length,
  unread: getUnreadCount(mockNotifications),
  page: 1,
  limit: 50,
};
