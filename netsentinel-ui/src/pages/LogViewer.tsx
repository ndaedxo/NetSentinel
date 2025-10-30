import { useCallback, useEffect, useMemo, useState } from 'react';
import { PageLayout } from '@/components';
import { getLogs, subscribeLogs } from '@/services';
import type { LogEntry } from '@/types';

export default function LogViewer() {
  const [level, setLevel] = useState<string>('');
  const [source, setSource] = useState<string>('');
  const [search, setSearch] = useState('');
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [live, setLive] = useState(false);
  const [useUtc, setUseUtc] = useState(false);

  const levels = useMemo(() => ['', 'debug','info','warn','error'], []);
  const sources = useMemo(() => ['', 'api','auth','ml','network','alerts','ui'], []);

  const resetFilters = () => {
    setLevel('');
    setSource('');
    setSearch('');
  };

  const load = useCallback(async () => {
    const data = await getLogs({
      level: (level || undefined) as LogEntry['level'] | undefined,
      source: (source || undefined) as LogEntry['source'] | undefined,
      search: search || undefined,
      limit: 300,
    });
    setLogs(data);
  }, [level, source, search]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    if (!live) return;
    const unsub = subscribeLogs((entry) => setLogs(prev => [...prev.slice(-299), entry]));
    return () => unsub();
  }, [live]);

  return (
    <PageLayout
      title={
        <div className="flex items-center gap-2">
          Log Viewer
          {live && (
            <div className="flex items-center gap-1">
              <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
              <span className="text-green-400 text-sm">Live</span>
            </div>
          )}
        </div>
      }
      subtitle="Search and live-tail application logs"
    >
      <div className="space-y-4">
        <div className="flex flex-wrap gap-2 items-center">
          <label htmlFor="log-level-filter" className="sr-only">Filter by log level</label>
          <select
            id="log-level-filter"
            className="bg-slate-800 border border-slate-700 rounded px-2 py-1 text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
            value={level}
            onChange={(e) => setLevel(e.target.value)}
          >
            {levels.map(l => <option key={l} value={l}>{l || 'All Levels'}</option>)}
          </select>

          <label htmlFor="log-source-filter" className="sr-only">Filter by log source</label>
          <select
            id="log-source-filter"
            className="bg-slate-800 border border-slate-700 rounded px-2 py-1 text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
            value={source}
            onChange={(e) => setSource(e.target.value)}
          >
            {sources.map(s => <option key={s} value={s}>{s || 'All Sources'}</option>)}
          </select>

          <label htmlFor="log-search-input" className="sr-only">Search logs</label>
          <input
            id="log-search-input"
            placeholder="search..."
            className="w-64 bg-slate-800 border border-slate-700 rounded px-2 py-1 text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />

          <button
            className="px-3 py-1 rounded bg-slate-800 border border-slate-700 hover:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
            onClick={load}
          >
            Run
          </button>

          <button
            className="px-3 py-1 rounded bg-slate-800 border border-slate-700 hover:bg-slate-700 text-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500"
            onClick={resetFilters}
          >
            Reset
          </button>

          <label className="flex items-center gap-2 text-slate-300 text-sm">
            <input
              type="checkbox"
              checked={useUtc}
              onChange={(e) => setUseUtc(e.target.checked)}
              className="focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            UTC
          </label>

          <label className="ml-auto flex items-center gap-2 text-slate-300 text-sm">
            <input
              type="checkbox"
              checked={live}
              onChange={(e) => setLive(e.target.checked)}
              className="focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            Live tail
          </label>
        </div>
        <div className="bg-slate-950/60 border border-slate-800 rounded min-h-[400px] max-h-[600px] overflow-auto">
          {logs.length === 0 ? (
            <div className="flex items-center justify-center h-full text-slate-400">
              <div className="text-center">
                <p className="text-lg mb-2">No logs found</p>
                <p className="text-sm">Try adjusting your filters or check back later.</p>
              </div>
            </div>
          ) : (
            <table className="min-w-full text-xs" role="table" aria-label="Application logs">
              <thead className="sticky top-0 bg-slate-900 text-slate-300">
                <tr className="text-left" role="row">
                  <th className="px-2 py-2 w-48" scope="col" role="columnheader">Time</th>
                  <th className="px-2 py-2 w-20" scope="col" role="columnheader">Level</th>
                  <th className="px-2 py-2 w-28" scope="col" role="columnheader">Source</th>
                  <th className="px-2 py-2" scope="col" role="columnheader">Message</th>
                </tr>
              </thead>
              <tbody className="text-slate-300">
                {logs.map(l => (
                  <tr key={l.id} className="border-t border-slate-800/80" role="row">
                    <td className="px-2 py-1 whitespace-nowrap text-slate-400">
                    {useUtc
                      ? new Date(l.timestamp).toISOString().replace('T', ' ').slice(0, -5)
                      : new Date(l.timestamp).toLocaleString()
                    }
                  </td>
                    <td className="px-2 py-1"><span className={
                      l.level === 'error' ? 'text-red-400' : l.level === 'warn' ? 'text-yellow-300' : l.level === 'info' ? 'text-blue-300' : 'text-slate-400'
                    }>{l.level}</span></td>
                    <td className="px-2 py-1 text-slate-400">{l.source}</td>
                    <td className="px-2 py-1 font-mono break-all">{l.message}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </PageLayout>
  );
}


