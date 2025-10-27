/**
 * Interface for dashboard metrics data
 */
export interface DashboardMetrics {
  totalEvents: number;
  activeThreats: number;
  blockedIps: number;
  todayThreats: number;
}

/**
 * Interface for system health service status
 */
export interface SystemHealthService {
  name: string;
  status: "running" | "degraded" | "error";
}
