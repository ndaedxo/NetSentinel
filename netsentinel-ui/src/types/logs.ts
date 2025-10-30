export interface LogEntry {
  id: string;
  timestamp: string;
  level: 'debug' | 'info' | 'warn' | 'error';
  source: 'api' | 'auth' | 'ml' | 'network' | 'alerts' | 'ui';
  message: string;
  context?: Record<string, unknown>;
}


