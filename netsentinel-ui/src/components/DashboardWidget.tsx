import React from 'react';
import { GripVertical, Settings, X, RefreshCw } from 'lucide-react';
import { useDashboard } from '@/hooks/useDashboard';
import type { Widget } from '@/types/dashboard';
import { mockThreats } from '@/mock/threats-mock';
import { mockAlerts } from '@/mock/alerts-mock';
import { mockSystemHealth } from '@/mock/dashboard-mock';

// Import existing components
import StatCard from './StatCard';
import ThreatTimeline from './ThreatTimeline';
import AlertFeed from './AlertFeed';
import SystemHealth from './SystemHealth';
import ThreatTable from './ThreatTable';
// import NetworkAnalysis from './NetworkAnalysis'; // Component not implemented yet

interface DashboardWidgetProps {
  widget: Widget;
  isEditing?: boolean;
}

export default function DashboardWidget({ widget, isEditing = false }: DashboardWidgetProps) {
  const { removeWidget, updateWidget } = useDashboard();

  const handleRemove = () => {
    removeWidget(widget.id);
  };

  const handleRefresh = () => {
    // Trigger data refresh - this would normally be handled by the widget's data fetching logic
    updateWidget(widget.id, { ...widget });
  };

  const renderWidgetContent = () => {
    switch (widget.type) {
      case 'stat-card':
        return <StatCard {...getStatCardProps(widget)} />;
      case 'threat-timeline':
        return <ThreatTimeline {...getTimelineProps(widget)} />;
      case 'alert-feed':
        return <AlertFeed {...getAlertFeedProps(widget)} />;
      case 'system-health':
        return <SystemHealth {...getSystemHealthProps(widget)} />;
      case 'threat-table':
        return <ThreatTable {...getThreatTableProps(widget)} />;
      case 'network-graph':
        return <CustomChartWidget {...getCustomChartProps(widget)} />; // Placeholder for network graph
      case 'custom-chart':
        return <CustomChartWidget {...getCustomChartProps(widget)} />;
      default:
        return (
          <div className="flex items-center justify-center h-full text-slate-400">
            <div className="text-center">
              <div className="text-2xl mb-2">📊</div>
              <div>Unknown widget type</div>
            </div>
          </div>
        );
    }
  };

  return (
    <div
      className={`
        relative bg-slate-800/50 border border-slate-700 rounded-lg overflow-hidden
        ${isEditing ? 'ring-2 ring-blue-500/50' : ''}
        transition-all duration-200 hover:shadow-lg
      `}
      style={{
        gridColumn: `span ${widget.size.width}`,
        gridRow: `span ${widget.size.height}`,
      }}
    >
      {/* Widget Header */}
      {(widget.config.showHeader !== false) && (
        <div className="flex items-center justify-between p-3 border-b border-slate-700">
          <h3 className="font-medium text-slate-200 truncate">
            {widget.title}
          </h3>

          <div className="flex items-center space-x-1">
            <button
              onClick={handleRefresh}
              className="p-1 text-slate-400 hover:text-slate-300 transition-colors"
              title="Refresh"
            >
              <RefreshCw className="w-4 h-4" />
            </button>

            {isEditing && (
              <>
                <button
                  className="p-1 text-slate-400 hover:text-slate-300 transition-colors cursor-grab active:cursor-grabbing"
                  title="Drag to move"
                >
                  <GripVertical className="w-4 h-4" />
                </button>

                <button
                  className="p-1 text-slate-400 hover:text-slate-300 transition-colors"
                  title="Configure"
                >
                  <Settings className="w-4 h-4" />
                </button>

                <button
                  onClick={handleRemove}
                  className="p-1 text-slate-400 hover:text-red-400 transition-colors"
                  title="Remove widget"
                >
                  <X className="w-4 h-4" />
                </button>
              </>
            )}
          </div>
        </div>
      )}

      {/* Widget Content */}
      <div className={`p-4 ${widget.config.compact ? 'p-2' : ''}`}>
        {renderWidgetContent()}
      </div>
    </div>
  );
}

// Custom chart component
function CustomChartWidget({ config }: { config: any }) {
  // This would be a more sophisticated chart component
  return (
    <div className="flex items-center justify-center h-32 text-slate-400">
      <div className="text-center">
        <div className="text-3xl mb-2">📈</div>
        <div>{config.chartType || 'bar'} chart</div>
        <div className="text-xs mt-1">Custom chart widget</div>
      </div>
    </div>
  );
}

// Helper functions to convert widget config to component props
function getStatCardProps(widget: Widget) {
  return {
    title: widget.title,
    value: widget.data?.value || 0,
    icon: widget.data?.icon || 'Activity',
    trend: widget.data?.trend,
    color: widget.config.color || 'blue'
  };
}

function getTimelineProps(widget: Widget) {
  return {
    data: widget.data?.timeline || [],
    compact: widget.config.compact,
    maxItems: widget.config.maxItems || 10
  };
}

function getAlertFeedProps(widget: Widget) {
  return {
    alerts: widget.data?.alerts || mockAlerts.slice(0, widget.config.maxItems || 5),
    compact: widget.config.compact,
    maxItems: widget.config.maxItems || 5
  };
}

function getSystemHealthProps(widget: Widget) {
  return {
    services: widget.data?.services || mockSystemHealth.services,
    compact: widget.config.compact
  };
}

function getThreatTableProps(widget: Widget) {
  return {
    threats: widget.data?.threats || mockThreats.slice(0, widget.config.pageSize || 10),
    compact: widget.config.compact,
    pageSize: widget.config.pageSize || 10,
    showFilters: false
  };
}

function getNetworkProps(widget: Widget) {
  return {
    compact: widget.config.compact
  };
}

function getCustomChartProps(widget: Widget) {
  return {
    config: widget.config
  };
}
