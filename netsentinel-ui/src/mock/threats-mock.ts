import type { ThreatType } from '@/types';

interface ThreatTimelineData {
  timestamp: string;
  threat_count: number;
  blocked_count: number;
}

/**
 * Mock threat data
 */
export const mockThreats: ThreatType[] = [
  {
    id: 1,
    ip_address: "192.168.1.100",
    country_code: "US",
    threat_score: 85,
    severity: "high",
    threat_type: "Port Scan",
    description: "Detected suspicious port scanning activity",
    honeypot_service: "SSH Honeypot",
    is_blocked: 1,
    created_at: "2025-10-27T10:30:00Z",
    updated_at: "2025-10-27T10:30:00Z"
  },
  {
    id: 2,
    ip_address: "10.0.0.50",
    country_code: "CN",
    threat_score: 92,
    severity: "critical",
    threat_type: "Brute Force",
    description: "Multiple failed authentication attempts",
    honeypot_service: "FTP Honeypot",
    is_blocked: 0,
    created_at: "2025-10-27T09:15:00Z",
    updated_at: "2025-10-27T09:15:00Z"
  },
  {
    id: 3,
    ip_address: "172.16.0.25",
    country_code: "RU",
    threat_score: 67,
    severity: "medium",
    threat_type: "Malware Download",
    description: "Attempted to download malicious payload",
    honeypot_service: "HTTP Honeypot",
    is_blocked: 1,
    created_at: "2025-10-27T08:45:00Z",
    updated_at: "2025-10-27T08:45:00Z"
  }
];

/**
 * Mock recent threats (subset of all threats)
 */
export const mockRecentThreats: ThreatType[] = mockThreats.slice(0, 2);

/**
 * Mock threat timeline data
 */
export const mockThreatTimeline: ThreatTimelineData[] = [
  {
    timestamp: "2025-10-27T10:30:00Z",
    threat_count: 15,
    blocked_count: 12
  },
  {
    timestamp: "2025-10-27T09:30:00Z",
    threat_count: 8,
    blocked_count: 6
  },
  {
    timestamp: "2025-10-27T08:30:00Z",
    threat_count: 22,
    blocked_count: 18
  }
];
