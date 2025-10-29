import { useState, useEffect, useRef } from 'react';
import {
  Activity,
  Cpu,
  HardDrive,
  Wifi,
  Clock,
  TrendingUp,
  AlertTriangle,
  CheckCircle,
  Monitor
} from 'lucide-react';
import { usePerformanceMonitor } from '@/hooks';
import {
  getPageLoadTime,
  getDomContentLoadedTime,
  getFirstPaintTime,
  getLargestContentfulPaint,
  getAverageApiResponseTime,
  getNetworkRequestCount,
  getFailedRequestCount,
  getUsedMemory,
  getTotalMemory,
  getMemoryUsagePercent,
  formatBytes
} from '@/utils';

interface PerformanceMetrics {
  // Page metrics
  pageLoadTime: number;
  domContentLoaded: number;
  firstPaint: number;
  largestContentfulPaint: number;

  // Network metrics
  apiResponseTime: number;
  networkRequests: number;
  failedRequests: number;

  // Memory metrics
  usedMemory: number;
  totalMemory: number;
  memoryUsagePercent: number;

  // React metrics
  componentRenderCount: number;
  averageRenderTime: number;

  // Timestamp
  timestamp: number;
}

interface PerformanceMonitorProps {
  isOpen: boolean;
  onClose: () => void;
  className?: string;
}

export default function PerformanceMonitor({
  isOpen,
  onClose
}: PerformanceMonitorProps) {
  const [metrics, setMetrics] = useState<PerformanceMetrics | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const { getAverageRenderTime, getRenderCount } = usePerformanceMonitor();

  useEffect(() => {
    if (isOpen) {
      startMonitoring();
    } else {
      stopMonitoring();
    }

    return () => stopMonitoring();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen]);

  const startMonitoring = () => {
    setIsRecording(true);

    // Collect initial metrics
    updateMetrics();

    // Set up periodic updates
    intervalRef.current = setInterval(updateMetrics, 2000);
  };

  const stopMonitoring = () => {
    setIsRecording(false);
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  };

  const updateMetrics = () => {
    const newMetrics: PerformanceMetrics = {
      // Page performance metrics
      pageLoadTime: getPageLoadTime(),
      domContentLoaded: getDomContentLoadedTime(),
      firstPaint: getFirstPaintTime(),
      largestContentfulPaint: getLargestContentfulPaint(),

      // Network metrics (simplified)
      apiResponseTime: getAverageApiResponseTime(),
      networkRequests: getNetworkRequestCount(),
      failedRequests: getFailedRequestCount(),

      // Memory metrics
      usedMemory: getUsedMemory(),
      totalMemory: getTotalMemory(),
      memoryUsagePercent: getMemoryUsagePercent(),

      // React metrics
      componentRenderCount: getRenderCount(),
      averageRenderTime: getAverageRenderTime(),

      timestamp: Date.now()
    };

    setMetrics(newMetrics);
  };


  if (!isOpen || !metrics) return null;

  const getHealthStatus = (value: number, thresholds: { warning: number; critical: number }) => {
    if (value >= thresholds.critical) return 'critical';
    if (value >= thresholds.warning) return 'warning';
    return 'good';
  };


  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-700 rounded-lg shadow-2xl max-w-6xl w-full max-h-[90vh] overflow-hidden">
        <div className="flex h-full">
          {/* Sidebar */}
          <div className="w-80 bg-slate-800/50 border-r border-slate-700 p-6 overflow-y-auto">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold text-slate-200">Performance Monitor</h2>
              <div className="flex items-center space-x-2">
                <div className={`w-2 h-2 rounded-full ${isRecording ? 'bg-green-400 animate-pulse' : 'bg-slate-500'}`} />
                <span className="text-sm text-slate-400">
                  {isRecording ? 'Recording' : 'Stopped'}
                </span>
                <button
                  onClick={onClose}
                  className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
                >
                  ×
                </button>
              </div>
            </div>

            {/* Quick Stats */}
            <div className="space-y-4">
              <div className="p-4 bg-slate-700/50 rounded-lg">
                <div className="flex items-center space-x-3 mb-2">
                  <Clock className="w-5 h-5 text-blue-400" />
                  <span className="font-medium text-slate-200">Page Load</span>
                </div>
                <div className="text-2xl font-bold text-white">
                  {metrics.pageLoadTime.toFixed(1)}s
                </div>
                <div className="text-sm text-slate-400">
                  DOM: {metrics.domContentLoaded.toFixed(1)}s
                </div>
              </div>

              <div className="p-4 bg-slate-700/50 rounded-lg">
                <div className="flex items-center space-x-3 mb-2">
                  <Cpu className="w-5 h-5 text-purple-400" />
                  <span className="font-medium text-slate-200">Memory Usage</span>
                </div>
                <div className="text-2xl font-bold text-white">
                  {metrics.memoryUsagePercent.toFixed(1)}%
                </div>
                <div className="text-sm text-slate-400">
                  {formatBytes(metrics.usedMemory)} / {formatBytes(metrics.totalMemory)}
                </div>
              </div>

              <div className="p-4 bg-slate-700/50 rounded-lg">
                <div className="flex items-center space-x-3 mb-2">
                  <Wifi className="w-5 h-5 text-green-400" />
                  <span className="font-medium text-slate-200">Network</span>
                </div>
                <div className="text-2xl font-bold text-white">
                  {metrics.apiResponseTime.toFixed(0)}ms
                </div>
                <div className="text-sm text-slate-400">
                  {metrics.networkRequests} requests
                </div>
              </div>
            </div>
          </div>

          {/* Main Content */}
          <div className="flex-1 p-6 overflow-y-auto">
            <div className="space-y-6">
              {/* Performance Metrics Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {/* Page Performance */}
                <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4">
                  <div className="flex items-center space-x-2 mb-3">
                    <Monitor className="w-5 h-5 text-blue-400" />
                    <h3 className="font-medium text-slate-200">Page Performance</h3>
                  </div>
                  <div className="space-y-2">
                    <MetricItem
                      label="Page Load"
                      value={`${metrics.pageLoadTime.toFixed(1)}s`}
                      status={getHealthStatus(metrics.pageLoadTime, { warning: 3, critical: 5 })}
                    />
                    <MetricItem
                      label="DOM Ready"
                      value={`${metrics.domContentLoaded.toFixed(1)}s`}
                      status={getHealthStatus(metrics.domContentLoaded, { warning: 2, critical: 4 })}
                    />
                    <MetricItem
                      label="First Paint"
                      value={`${metrics.firstPaint.toFixed(1)}ms`}
                      status={getHealthStatus(metrics.firstPaint / 1000, { warning: 2, critical: 4 })}
                    />
                    <MetricItem
                      label="LCP"
                      value={`${metrics.largestContentfulPaint.toFixed(1)}ms`}
                      status={getHealthStatus(metrics.largestContentfulPaint / 1000, { warning: 2.5, critical: 4 })}
                    />
                  </div>
                </div>

                {/* Memory Usage */}
                <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4">
                  <div className="flex items-center space-x-2 mb-3">
                    <HardDrive className="w-5 h-5 text-purple-400" />
                    <h3 className="font-medium text-slate-200">Memory Usage</h3>
                  </div>
                  <div className="space-y-2">
                    <MetricItem
                      label="Used Memory"
                      value={formatBytes(metrics.usedMemory)}
                      status={getHealthStatus(metrics.memoryUsagePercent, { warning: 70, critical: 90 })}
                    />
                    <MetricItem
                      label="Total Memory"
                      value={formatBytes(metrics.totalMemory)}
                      status="neutral"
                    />
                    <MetricItem
                      label="Usage %"
                      value={`${metrics.memoryUsagePercent.toFixed(1)}%`}
                      status={getHealthStatus(metrics.memoryUsagePercent, { warning: 70, critical: 90 })}
                    />
                  </div>
                </div>

                {/* Network Performance */}
                <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4">
                  <div className="flex items-center space-x-2 mb-3">
                    <Wifi className="w-5 h-5 text-green-400" />
                    <h3 className="font-medium text-slate-200">Network</h3>
                  </div>
                  <div className="space-y-2">
                    <MetricItem
                      label="Avg Response"
                      value={`${metrics.apiResponseTime.toFixed(0)}ms`}
                      status={getHealthStatus(metrics.apiResponseTime, { warning: 1000, critical: 3000 })}
                    />
                    <MetricItem
                      label="Total Requests"
                      value={metrics.networkRequests.toString()}
                      status="neutral"
                    />
                    <MetricItem
                      label="Failed Requests"
                      value={metrics.failedRequests.toString()}
                      status={metrics.failedRequests > 0 ? 'warning' : 'good'}
                    />
                  </div>
                </div>

                {/* React Performance */}
                <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4">
                  <div className="flex items-center space-x-2 mb-3">
                    <Activity className="w-5 h-5 text-orange-400" />
                    <h3 className="font-medium text-slate-200">React Performance</h3>
                  </div>
                  <div className="space-y-2">
                    <MetricItem
                      label="Render Count"
                      value={metrics.componentRenderCount.toString()}
                      status="neutral"
                    />
                    <MetricItem
                      label="Avg Render Time"
                      value={`${metrics.averageRenderTime.toFixed(2)}ms`}
                      status={getHealthStatus(metrics.averageRenderTime, { warning: 16.67, critical: 33.33 })}
                    />
                  </div>
                </div>

                {/* System Health */}
                <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4">
                  <div className="flex items-center space-x-2 mb-3">
                    <TrendingUp className="w-5 h-5 text-cyan-400" />
                    <h3 className="font-medium text-slate-200">System Health</h3>
                  </div>
                  <div className="space-y-2">
                    <MetricItem
                      label="CPU Usage"
                      value="N/A"
                      status="neutral"
                    />
                    <MetricItem
                      label="Disk I/O"
                      value="N/A"
                      status="neutral"
                    />
                    <MetricItem
                      label="Network I/O"
                      value="N/A"
                      status="neutral"
                    />
                  </div>
                </div>
              </div>

              {/* Recommendations */}
              <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4">
                <h3 className="font-medium text-slate-200 mb-3">Performance Recommendations</h3>
                <div className="space-y-2 text-sm text-slate-400">
                  {metrics.pageLoadTime > 3 && (
                    <div className="flex items-center space-x-2">
                      <AlertTriangle className="w-4 h-4 text-yellow-400" />
                      <span>Consider optimizing page load time</span>
                    </div>
                  )}
                  {metrics.memoryUsagePercent > 80 && (
                    <div className="flex items-center space-x-2">
                      <AlertTriangle className="w-4 h-4 text-yellow-400" />
                      <span>High memory usage detected</span>
                    </div>
                  )}
                  {metrics.apiResponseTime > 1000 && (
                    <div className="flex items-center space-x-2">
                      <AlertTriangle className="w-4 h-4 text-yellow-400" />
                      <span>Slow API responses detected</span>
                    </div>
                  )}
                  {metrics.averageRenderTime > 16.67 && (
                    <div className="flex items-center space-x-2">
                      <AlertTriangle className="w-4 h-4 text-yellow-400" />
                      <span>Consider optimizing React renders</span>
                    </div>
                  )}
                  {metrics.failedRequests > 0 && (
                    <div className="flex items-center space-x-2">
                      <AlertTriangle className="w-4 h-4 text-red-400" />
                      <span>Network errors detected</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// Metric Item Component
interface MetricItemProps {
  label: string;
  value: string;
  status: 'good' | 'warning' | 'critical' | 'neutral';
}

function MetricItem({ label, value, status }: MetricItemProps) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-slate-400 text-sm">{label}</span>
      <div className="flex items-center space-x-2">
        {status !== 'neutral' && (
          status === 'critical' ? <AlertTriangle className="w-4 h-4 text-red-400" /> :
          status === 'warning' ? <AlertTriangle className="w-4 h-4 text-yellow-400" /> :
          <CheckCircle className="w-4 h-4 text-green-400" />
        )}
        <span className={`font-medium ${
          status === 'critical' ? 'text-red-400' :
          status === 'warning' ? 'text-yellow-400' :
          'text-slate-200'
        }`}>
          {value}
        </span>
      </div>
    </div>
  );
}

