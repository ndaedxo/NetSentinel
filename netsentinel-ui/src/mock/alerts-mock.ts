import type { AlertType } from '@/types';
import { alertGenerator } from '@/test/__mocks__/mock-generator';

/**
 * Generate dynamic mock alert data with realistic variety
 */
export const generateMockAlerts = (count: number = 10): AlertType[] => {
  return Array.from({ length: count }, (_, index) => {
    const alert = alertGenerator.generateAlert();
    return {
      ...alert,
      id: index + 1,
      status: index % 3 === 0 ? 'new' : index % 3 === 1 ? 'acknowledged' : 'resolved',
      is_acknowledged: index % 3 === 1 ? 1 : 0,
      threat_id: index + 1,
    };
  });
};

/**
 * Mock alert data - dynamically generated for realistic testing
 */
export const mockAlerts: AlertType[] = generateMockAlerts(15);

/**
 * Mock active alerts (unresolved alerts) - dynamically filtered
 */
export const mockActiveAlerts: AlertType[] = mockAlerts.filter(alert =>
  alert.status === 'new' || alert.status === 'acknowledged'
);

/**
 * Generate alerts with specific criteria
 */
export const generateAlertsBySeverity = (severity: 'low' | 'medium' | 'high' | 'critical', count: number = 5): AlertType[] => {
  return Array.from({ length: count }, (_, index) => {
    const alert = alertGenerator.generateAlert({ severity });
    return {
      ...alert,
      id: Date.now() + index,
      status: 'new',
      is_acknowledged: 0,
      threat_id: Date.now() + index,
    };
  });
};

/**
 * Generate alerts for specific time period
 */
export const generateRecentAlerts = (hoursAgo: number = 24, count: number = 8): AlertType[] => {
  const now = new Date();
  return Array.from({ length: count }, (_, index) => {
    const createdAt = new Date(now.getTime() - (index * hoursAgo * 60 * 60 * 1000 / count));
    const alert = alertGenerator.generateAlert();
    return {
      ...alert,
      id: Date.now() + index,
      status: Math.random() > 0.7 ? 'new' : 'acknowledged',
      is_acknowledged: Math.random() > 0.7 ? 0 : 1,
      threat_id: Date.now() + index,
      created_at: createdAt.toISOString(),
      updated_at: createdAt.toISOString(),
    };
  });
};
