import { mockLogs } from '@/mock';
import type { LogEntry } from '@/types';

export interface LogsQuery {
  level?: LogEntry['level'];
  source?: LogEntry['source'];
  search?: string;
  limit?: number;
}

export async function getLogs(query: LogsQuery = {}): Promise<LogEntry[]> {
  await new Promise(r => setTimeout(r, 200));
  const { level, source, search, limit = 200 } = query;
  let result = mockLogs;
  if (level) result = result.filter(l => l.level === level);
  if (source) result = result.filter(l => l.source === source);
  if (search) {
    const s = search.toLowerCase();
    result = result.filter(l => l.message.toLowerCase().includes(s));
  }
  return result.slice(0, limit);
}

export type LogsSubscriber = (entry: LogEntry) => void;

export function subscribeLogs(callback: LogsSubscriber): () => void {
  // Mock live tail: emit a log every 1.5s
  let i = 0;
  const timer = setInterval(() => {
    const entry = mockLogs[(i++) % mockLogs.length];
    callback({ ...entry, id: `live_${Date.now()}` });
  }, 1500);
  return () => clearInterval(timer);
}


