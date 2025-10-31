import React, { useState } from 'react';
import { GripVertical, Settings, X, RefreshCw, Activity, Shield, AlertTriangle, Users, Database, Network, TrendingUp, Clock, LucideIcon } from 'lucide-react';
import { useDashboard, useThreatData, useAlertData, useSystemHealthData } from '@/hooks';
import { ConfirmationModal } from '@/components';
import type { Widget, SystemHealthData } from '@/types/dashboard';
import type { AlertType } from '@/types/alerts';
import type { ThreatType } from '@/types/threats';

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

interface ChartConfig {
  chartType?: string;
  [key: string]: unknown;
}

export default function DashboardWidget({ widget, isEditing = false }: DashboardWidgetProps) {
  const { removeWidget, updateWidget } = useDashboard();
  const threats = useThreatData();
  const alerts = useAlertData();
  const systemHealth = useSystemHealthData();
  const [confirmRemove, setConfirmRemove] = useState(false);

  const handleRemoveClick = () => {
    setConfirmRemove(true);
  };

  const handleConfirmRemove = () => {
    removeWidget(widget.id);
    setConfirmRemove(false);
  };

  const handleCancelRemove = () => {
    setConfirmRemove(false);
  };

  const handleRefresh = () => {
    // Trigger data refresh - this would normally be handled by the widget's data fetching logic
    updateWidget(widget.id, { ...widget });
  };

  const renderWidgetContent = () => {
    switch (widget.type) {
      case 'stat-card':
        return <StatCard {...getStatCardProps(widget, threats, alerts)} />;
      case 'threat-timeline':
        return <ThreatTimeline {...getTimelineProps(widget, threats)} />;
      case 'alert-feed':
        return <AlertFeed {...getAlertFeedProps(widget, alerts)} />;
      case 'system-health':
        return <SystemHealth {...getSystemHealthProps(widget, systemHealth)} />;
      case 'threat-table':
        return <ThreatTable {...getThreatTableProps(widget, threats)} />;
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
      data-testid="dashboard-widget"
    >
      {/* Widget Header */}
      {(widget.config.showHeader !== false) && (
        <div className="flex items-center justify-between p-3 md:p-4 border-b border-slate-700">
          <h3 className="font-medium text-slate-200 truncate text-sm md:text-base">
            {widget.title}
          </h3>

          <div className="flex items-center space-x-1 md:space-x-2">
            <button
              onClick={handleRefresh}
              className="p-2 text-slate-400 hover:text-slate-300 transition-colors min-w-[32px] min-h-[32px] flex items-center justify-center"
              title="Refresh"
              aria-label="Refresh widget"
            >
              <RefreshCw className="w-4 h-4" />
            </button>

            {isEditing && (
              <>
                <button
                  className="p-2 text-slate-400 hover:text-slate-300 transition-colors cursor-grab active:cursor-grabbing min-w-[32px] min-h-[32px] flex items-center justify-center"
                  title="Drag to move"
                  aria-label="drag handle"
                >
                  <GripVertical className="w-4 h-4" />
                </button>

                <button
                  className="p-2 text-slate-400 hover:text-slate-300 transition-colors min-w-[32px] min-h-[32px] flex items-center justify-center"
                  title="Configure"
                  aria-label="settings"
                >
                  <Settings className="w-4 h-4" />
                </button>

                <button
                  onClick={handleRemoveClick}
                  className="p-2 text-slate-400 hover:text-red-400 transition-colors min-w-[32px] min-h-[32px] flex items-center justify-center"
                  title="Remove widget"
                  aria-label={`Remove widget: ${widget.title}`}
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

      <ConfirmationModal
        isOpen={confirmRemove}
        onClose={handleCancelRemove}
        onConfirm={handleConfirmRemove}
        title="Remove Widget"
        message={`Are you sure you want to remove the "${widget.title}" widget from your dashboard? This action cannot be undone.`}
        confirmText="Remove Widget"
        cancelText="Cancel"
        type="delete"
      />
    </div>
  );
}

// Custom chart component
function CustomChartWidget({ config }: { config: ChartConfig }) {
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
function getStatCardProps(widget: Widget, threats: ThreatType[] = [], alerts: AlertType[] = []) {
  const iconMap: Record<string, LucideIcon> = {
    Activity,
    Shield,
    AlertTriangle,
    Users,
    Database,
    Network,
    TrendingUp,
    Clock
  };

  const iconName = widget.data?.icon || 'Activity';
  const IconComponent = iconMap[iconName] || Activity;

  // Calculate value based on widget title if no data provided
  let value = widget.data?.value || 0;
  let color = widget.config.color || 'blue';

  if (value === 0) {
    switch (widget.title.toLowerCase()) {
      case 'total events':
        value = threats.length * Math.floor(Math.random() * 50 + 20);
        color = 'blue';
        break;
      case 'active threats':
        value = threats.filter(t => t.is_blocked === 0).length;
        color = 'red';
        break;
      case 'blocked threats':
      case 'blocked ips':
        value = threats.filter(t => t.is_blocked === 1).length;
        color = 'green';
        break;
      case 'total alerts':
        value = alerts.length;
        color = 'yellow';
        break;
      case 'critical alerts':
        value = alerts.filter(a => a.severity === 'critical').length;
        color = 'red';
        break;
      case 'new alerts':
        value = alerts.filter(a => a.status === 'new').length;
        color = 'blue';
        break;
      default:
        value = Math.floor(Math.random() * 100);
    }
  }

  return {
    title: widget.title,
    value,
    icon: IconComponent,
    trend: widget.data?.trend,
    color
  };
}

function getTimelineProps(widget: Widget, threats: ThreatType[] = []) {
  // Generate timeline data from threats if not provided
  let timelineData = widget.data?.timeline || [];

  if (timelineData.length === 0 && threats.length > 0) {
    // Generate timeline data in the format expected by ThreatTimeline component
    // Format: { hour: string, count: number, severity: string }
    const now = new Date();
    timelineData = [];

    for (let i = 23; i >= 0; i--) {
      const hourStart = new Date(now.getTime() - i * 60 * 60 * 1000);
      const hourEnd = new Date(hourStart.getTime() + 60 * 60 * 1000);

      const hourThreats = threats.filter(t => {
        const threatTime = new Date(t.created_at);
        return threatTime >= hourStart && threatTime < hourEnd;
      });

      // Group threats by severity for this hour
      const severityGroups = hourThreats.reduce((acc, threat) => {
        const severity = threat.severity || 'medium';
        acc[severity] = (acc[severity] || 0) + 1;
        return acc;
      }, {} as Record<string, number>);

      // Create entries for each severity
      Object.entries(severityGroups).forEach(([severity, count]) => {
        timelineData.push({
          hour: hourStart.getHours().toString().padStart(2, '0') + ':00',
          count,
          severity
        });
      });

      // If no threats this hour, add a zero entry for medium severity to show the hour
      if (hourThreats.length === 0) {
        timelineData.push({
          hour: hourStart.getHours().toString().padStart(2, '0') + ':00',
          count: 0,
          severity: 'medium'
        });
      }
    }
  }

  return {
    data: timelineData,
    compact: widget.config.compact,
    maxItems: widget.config.maxItems || 10
  };
}

function getAlertFeedProps(widget: Widget, alerts: AlertType[]) {
  return {
    alerts: widget.data?.alerts || alerts.slice(0, widget.config.maxItems || 5),
    compact: widget.config.compact,
    maxItems: widget.config.maxItems || 5
  };
}

function getSystemHealthProps(widget: Widget, systemHealth: SystemHealthData) {
  return {
    services: widget.data?.services || systemHealth.services,
    compact: widget.config.compact
  };
}

function getThreatTableProps(widget: Widget, threats: ThreatType[]) {
  return {
    threats: widget.data?.threats || threats.slice(0, widget.config.pageSize || 10),
    compact: widget.config.compact,
    pageSize: widget.config.pageSize || 10,
    showFilters: false
  };
}


function getCustomChartProps(widget: Widget) {
  return {
    config: widget.config
  };
}
