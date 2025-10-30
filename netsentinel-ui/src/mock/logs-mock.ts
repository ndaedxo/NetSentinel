// Mock logs data and streaming generator
import type { LogEntry } from '@/types';

const levels: LogEntry['level'][] = ['debug', 'info', 'warn', 'error'];
const sources: LogEntry['source'][] = ['api', 'auth', 'ml', 'network', 'alerts', 'ui'];

export function generateMockLogs(count: number = 200): LogEntry[] {
  const now = Date.now();
  return Array.from({ length: count }).map((_, i) => {
    const ts = new Date(now - i * 1000 * 10).toISOString();
    const level = levels[Math.floor(Math.random() * levels.length)];
    const source = sources[Math.floor(Math.random() * sources.length)];
    return {
      id: `log_${i}`,
      timestamp: ts,
      level,
      source,
      message: `${source.toUpperCase()}: Sample ${level} message ${i}`,
      context: { index: i },
    } as LogEntry;
  });
}

export const mockLogs: LogEntry[] = generateMockLogs(250);


