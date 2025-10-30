// Global types for Netsentinel UI application

// Threat-related types
export * from './threats';

// Alert-related types
export * from './alerts';

// Network-related types
export * from './network';

// Incident-related types
export * from './incidents';

// Report-related types
export * from './reports';

// Honeypot-related types
export * from './honeypot';

// Dashboard-related types
export * from './dashboard';

// Filter-related types
export * from './filter';

// ML Model-related types
export * from './ml-models';

// System health types
export interface SystemHealthService {
  id: string;
  name: string;
  status: 'healthy' | 'warning' | 'critical' | 'unknown';
  uptime: number;
  response_time: number;
  last_checked: Date;
  error_count: number;
  description?: string;
}

// Dashboard metrics type
export interface DashboardMetrics {
  totalEvents: number;
  activeThreats: number;
  blockedIPs: number;
  systemHealth: number;
  responseTime: number;
  uptime: number;
}
