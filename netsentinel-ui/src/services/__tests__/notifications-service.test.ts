import { jest, describe, it, expect, beforeEach, afterEach } from '@jest/globals';
import {
  getUserNotifications,
  markNotificationAsRead,
  markAllNotificationsAsRead,
  deleteNotification,
  getNotificationPreferences,
  updateNotificationPreferences,
  getChannelConfig,
  updateChannelConfig
} from '../notifications-service';

/* eslint-disable @typescript-eslint/no-require-imports */

describe('Notifications Service', () => {
  describe('getUserNotifications', () => {
    it('returns notifications response with pagination', async () => {
      const result = await getUserNotifications(1, 10);

      expect(result).toHaveProperty('notifications');
      expect(result).toHaveProperty('total');
      expect(result).toHaveProperty('page', 1);
      expect(result).toHaveProperty('limit', 10);
      expect(Array.isArray(result.notifications)).toBe(true);
    });

    it('accepts custom page and limit parameters', async () => {
      const result = await getUserNotifications(2, 25);

      expect(result.page).toBe(2);
      expect(result.limit).toBe(25);
    });

    it('uses default pagination values', async () => {
      const result = await getUserNotifications();

      expect(result.page).toBe(1);
      expect(result.limit).toBe(50);
    });

    it('returns mock data structure', async () => {
      const result = await getUserNotifications();

      expect(result).toHaveProperty('total');
      expect(typeof result.total).toBe('number');
      expect(result.notifications.length).toBeGreaterThan(0);

      const notification = result.notifications[0];
      expect(notification).toHaveProperty('id');
      expect(notification).toHaveProperty('title');
      expect(notification).toHaveProperty('message');
      expect(notification).toHaveProperty('type');
      expect(notification).toHaveProperty('read');
      expect(notification).toHaveProperty('createdAt');
    });
  });

  describe('markNotificationAsRead', () => {
    it('returns success response', async () => {
      const result = await markNotificationAsRead('test-id');

      expect(result).toEqual({ success: true });
    });

    it('accepts any notification ID', async () => {
      const result1 = await markNotificationAsRead('notification-1');
      const result2 = await markNotificationAsRead('notification-2');

      expect(result1.success).toBe(true);
      expect(result2.success).toBe(true);
    });
  });

  describe('markAllNotificationsAsRead', () => {
    it('returns success response', async () => {
      const result = await markAllNotificationsAsRead();

      expect(result).toEqual({ success: true });
    });
  });

  describe('deleteNotification', () => {
    it('returns success response', async () => {
      const result = await deleteNotification('test-id');

      expect(result).toEqual({ success: true });
    });

    it('accepts any notification ID', async () => {
      const result1 = await deleteNotification('notification-1');
      const result2 = await deleteNotification('notification-2');

      expect(result1.success).toBe(true);
      expect(result2.success).toBe(true);
    });
  });

  describe('getNotificationPreferences', () => {
    it('returns default preferences', async () => {
      const result = await getNotificationPreferences();

      expect(result).toEqual({
        emailEnabled: true,
        smsEnabled: false,
        slackEnabled: false,
        severities: ['high', 'critical'],
      });
    });

    it('returns a copy, not the original object', async () => {
      const result1 = await getNotificationPreferences();
      const result2 = await getNotificationPreferences();

      expect(result1).not.toBe(result2); // Different references
      expect(result1).toEqual(result2); // Same content
    });
  });

  describe('updateNotificationPreferences', () => {
    let originalPrefs: any;

    beforeEach(async () => {
      // Store original state
      originalPrefs = await getNotificationPreferences();
    });

    afterEach(async () => {
      // Reset to original state by updating with original values
      await updateNotificationPreferences(originalPrefs);
    });

    it('updates preferences and returns new state', async () => {
      const updates = {
        emailEnabled: false,
        smsEnabled: true,
        severities: ['critical'] as const,
      };

      const result = await updateNotificationPreferences(updates);

      expect(result).toEqual({
        emailEnabled: false,
        smsEnabled: true,
        slackEnabled: false, // unchanged
        severities: ['critical'],
      });
    });

    it('handles partial updates', async () => {
      const result = await updateNotificationPreferences({ smsEnabled: true });

      expect(result.smsEnabled).toBe(true);
      expect(result.emailEnabled).toBe(true); // unchanged
      expect(result.slackEnabled).toBe(false); // unchanged
    });

    it('persists updates across calls', async () => {
      await updateNotificationPreferences({ smsEnabled: true });

      const result = await getNotificationPreferences();
      expect(result.smsEnabled).toBe(true);
    });

    it('handles empty updates', async () => {
      const before = await getNotificationPreferences();
      const result = await updateNotificationPreferences({});

      expect(result).toEqual(before);
    });
  });

  describe('getChannelConfig', () => {
    it('returns default channel configuration', async () => {
      const result = await getChannelConfig();

      expect(result).toEqual({
        email: { from: 'alerts@netsentinel.local' },
      });
    });

    it('returns a copy, not the original object', async () => {
      const result1 = await getChannelConfig();
      const result2 = await getChannelConfig();

      expect(result1).not.toBe(result2);
      expect(result1).toEqual(result2);
    });
  });

  describe('updateChannelConfig', () => {
    // Reset channels to default state before each test
    beforeEach(async () => {
      // Import and reset the module-level channels variable
      const notificationsService = require('../notifications-service');
      notificationsService.channels = {
        email: { from: 'alerts@netsentinel.local' },
      };
    });

    it('updates channel configuration', async () => {
      const updates = {
        email: { from: 'new-alerts@netsentinel.local' },
        slack: { webhookUrl: 'https://hooks.slack.com/test' },
      };

      const result = await updateChannelConfig(updates);

      expect(result).toEqual({
        email: { from: 'new-alerts@netsentinel.local' },
        slack: { webhookUrl: 'https://hooks.slack.com/test' },
      });
    });

    it('handles partial updates', async () => {
      const result = await updateChannelConfig({
        email: { from: 'updated@netsentinel.local' }
      });

      expect(result.email.from).toBe('updated@netsentinel.local');
      // The email should be updated
      expect(result.email).toBeDefined();
    });

    it('persists updates across calls', async () => {
      await updateChannelConfig({
        slack: { webhookUrl: 'https://hooks.slack.com/test' }
      });

      const result = await getChannelConfig();
      expect(result.slack?.webhookUrl).toBe('https://hooks.slack.com/test');
    });
  });

  describe('Integration', () => {
    it('preferences and channel config are independent', async () => {
      // Update preferences
      await updateNotificationPreferences({ smsEnabled: true });

      // Update channel config
      await updateChannelConfig({ email: { from: 'test@netsentinel.local' } });

      // Check both are updated independently
      const prefs = await getNotificationPreferences();
      const config = await getChannelConfig();

      expect(prefs.smsEnabled).toBe(true);
      expect(config.email.from).toBe('test@netsentinel.local');
    });

    it('multiple preference updates work correctly', async () => {
      await updateNotificationPreferences({ emailEnabled: false });
      await updateNotificationPreferences({ smsEnabled: true });
      await updateNotificationPreferences({ severities: ['low'] as const });

      const result = await getNotificationPreferences();

      expect(result).toEqual({
        emailEnabled: false,
        smsEnabled: true,
        slackEnabled: false,
        severities: ['low'],
      });
    });
  });

  describe('Async behavior', () => {
    it('all functions complete successfully', async () => {
      const promises = [
        getUserNotifications(),
        markNotificationAsRead('test'),
        markAllNotificationsAsRead(),
        deleteNotification('test'),
        getNotificationPreferences(),
        getChannelConfig(),
      ];

      const results = await Promise.all(promises);

      expect(results).toHaveLength(6);
      expect(results[0]).toHaveProperty('notifications');
      expect(results[1]).toEqual({ success: true });
      expect(results[2]).toEqual({ success: true });
      expect(results[3]).toEqual({ success: true });
      expect(results[4]).toHaveProperty('emailEnabled');
      expect(results[5]).toHaveProperty('email');
    });
  });

  describe('Error handling', () => {
    it('handles invalid notification IDs', async () => {
      const result = await markNotificationAsRead('');

      expect(result.success).toBe(true);
    });

    it('handles malformed preference updates', async () => {
      const result = await updateNotificationPreferences({} as any);

      expect(result).toHaveProperty('emailEnabled');
    });
  });
});
