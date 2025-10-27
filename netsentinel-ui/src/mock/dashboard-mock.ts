import type { DashboardMetrics, SystemHealthService } from '@/types';

/**
 * Mock dashboard metrics
 */
export const mockDashboardMetrics: DashboardMetrics = {
  totalEvents: 1250,
  activeThreats: 23,
  blockedIps: 45,
  todayThreats: 67
};

/**
 * Mock system health services
 */
export const mockSystemHealthServices: SystemHealthService[] = [
  {
    name: "Threat Detection Engine",
    status: "running"
  },
  {
    name: "Network Monitor",
    status: "running"
  },
  {
    name: "Alert System",
    status: "degraded"
  },
  {
    name: "Database",
    status: "running"
  },
  {
    name: "API Gateway",
    status: "error"
  }
];

/**
 * Mock system health response
 */
export const mockSystemHealth = {
  services: mockSystemHealthServices
};
