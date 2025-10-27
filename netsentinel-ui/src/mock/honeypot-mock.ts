import type { HoneypotServiceType } from '@/types';

/**
 * Mock honeypot service data
 */
export const mockHoneypots: HoneypotServiceType[] = [
  {
    id: 1,
    name: "SSH Honeypot",
    port: 22,
    protocol: "TCP",
    is_active: 1,
    connection_count: 145,
    last_connection_at: "2025-10-27T10:25:00Z",
    created_at: "2025-01-15T08:00:00Z",
    updated_at: "2025-10-27T10:25:00Z"
  },
  {
    id: 2,
    name: "FTP Honeypot",
    port: 21,
    protocol: "TCP",
    is_active: 1,
    connection_count: 67,
    last_connection_at: "2025-10-27T09:45:00Z",
    created_at: "2025-01-15T08:15:00Z",
    updated_at: "2025-10-27T09:45:00Z"
  },
  {
    id: 3,
    name: "HTTP Honeypot",
    port: 80,
    protocol: "TCP",
    is_active: 0,
    connection_count: 234,
    last_connection_at: "2025-10-26T16:30:00Z",
    created_at: "2025-01-15T08:30:00Z",
    updated_at: "2025-10-26T16:30:00Z"
  },
  {
    id: 4,
    name: "Telnet Honeypot",
    port: 23,
    protocol: "TCP",
    is_active: 1,
    connection_count: 89,
    last_connection_at: "2025-10-27T08:15:00Z",
    created_at: "2025-01-15T08:45:00Z",
    updated_at: "2025-10-27T08:15:00Z"
  }
];
