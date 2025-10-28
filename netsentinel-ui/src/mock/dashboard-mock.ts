import type { DashboardMetrics, SystemHealthService } from '@/types';

/**
 * Mock dashboard metrics
 */
export const mockDashboardMetrics: DashboardMetrics = {
  totalEvents: 1250,
  activeThreats: 23,
  blockedIPs: 45,
  systemHealth: 98.5,
  responseTime: 45,
  uptime: 99.9
};

/**
 * Mock system health services
 */
export const mockSystemHealthServices: SystemHealthService[] = [
  {
    id: 'threat-detection',
    name: "Threat Detection Engine",
    status: "healthy",
    uptime: 99.8,
    response_time: 45,
    last_checked: new Date(),
    error_count: 0,
    description: 'AI-powered threat detection'
  },
  {
    name: "Network Monitor",
    id: 'network-monitor',
    status: "healthy",
    uptime: 99.5,
    response_time: 67,
    last_checked: new Date(),
    error_count: 1,
    description: 'Network traffic monitoring'
  },
  {
    id: 'alert-system',
    name: "Alert System",
    status: "warning",
    uptime: 95.2,
    response_time: 120,
    last_checked: new Date(),
    error_count: 5,
    description: 'Automated alert generation'
  },
  {
    id: 'database',
    name: "Database",
    status: "healthy",
    uptime: 99.9,
    response_time: 23,
    last_checked: new Date(),
    error_count: 0,
    description: 'Primary data storage'
  },
  {
    id: 'api-gateway',
    name: "API Gateway",
    status: "critical",
    uptime: 85.3,
    response_time: 0,
    last_checked: new Date(),
    error_count: 15,
    description: 'API request routing'
  }
];

/**
 * Mock system health response
 */
export const mockSystemHealth = {
  services: mockSystemHealthServices
};
