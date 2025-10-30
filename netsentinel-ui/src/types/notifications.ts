import type { NotificationItem } from '@/mock';

export interface NotificationPreferences {
  emailEnabled: boolean;
  smsEnabled: boolean;
  slackEnabled: boolean;
  quietHours?: { start: string; end: string };
  severities: Array<'low' | 'medium' | 'high' | 'critical'>;
}

export interface ChannelConfig {
  email?: { from: string; testRecipient?: string };
  sms?: { provider: 'twilio' | 'other'; fromNumber?: string };
  slack?: { webhookUrl?: string; channel?: string };
}

export interface NotificationsResponse {
  notifications: NotificationItem[];
  total: number;
  unread: number;
  page: number;
  limit: number;
}


