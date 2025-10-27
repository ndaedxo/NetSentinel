import type { AlertType } from '@/types';

/**
 * Mock alert data
 */
export const mockAlerts: AlertType[] = [
  {
    id: 1,
    title: "High Threat Score Detected",
    severity: "high",
    status: "new",
    description: "Threat with score 85 detected from IP 192.168.1.100",
    threat_id: 1,
    is_acknowledged: 0,
    created_at: "2025-10-27T10:30:00Z",
    updated_at: "2025-10-27T10:30:00Z"
  },
  {
    id: 2,
    title: "Critical Brute Force Attack",
    severity: "critical",
    status: "acknowledged",
    description: "Multiple authentication failures detected",
    threat_id: 2,
    is_acknowledged: 1,
    created_at: "2025-10-27T09:15:00Z",
    updated_at: "2025-10-27T09:20:00Z"
  },
  {
    id: 3,
    title: "Malware Activity Detected",
    severity: "medium",
    status: "resolved",
    description: "Suspicious file download attempt blocked",
    threat_id: 3,
    is_acknowledged: 1,
    created_at: "2025-10-27T08:45:00Z",
    updated_at: "2025-10-27T09:00:00Z"
  }
];

/**
 * Mock active alerts (unresolved alerts)
 */
export const mockActiveAlerts: AlertType[] = mockAlerts.filter(alert =>
  alert.status === 'new' || alert.status === 'acknowledged'
);
