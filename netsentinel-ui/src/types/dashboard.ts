export interface WidgetData {
  value?: number | string;
  icon?: string;
  trend?: {
    value: string;
    isPositive: boolean;
  };
  timeline?: Array<{
    hour: string;
    count: number;
    severity: string;
  }>;
  alerts?: Array<{
    id: number;
    severity: 'low' | 'medium' | 'high' | 'critical';
    status: 'new' | 'acknowledged' | 'resolved';
    description: string | null;
    created_at: string;
    updated_at: string;
    title: string;
    threat_id: number | null;
    is_acknowledged: number;
  }>;
  services?: SystemHealthService[];
  threats?: Array<{
    id: number;
    ip_address: string;
    country_code: string | null;
    threat_score: number;
    severity: 'low' | 'medium' | 'high' | 'critical';
    threat_type: string;
    description: string | null;
    honeypot_service: string | null;
    is_blocked: number;
    created_at: string;
    updated_at: string;
  }>;
  [key: string]: unknown;
}

export interface Widget {
  id: string;
  type: WidgetType;
  title: string;
  position: WidgetPosition;
  size: WidgetSize;
  config: WidgetConfig;
  data?: WidgetData;
}

export type WidgetType =
  | 'stat-card'
  | 'threat-timeline'
  | 'alert-feed'
  | 'system-health'
  | 'threat-table'
  | 'network-graph'
  | 'custom-chart';

export interface WidgetPosition {
  x: number;
  y: number;
}

export interface WidgetSize {
  width: number;
  height: number;
}

export interface WidgetConfig {
  refreshInterval?: number;
  showHeader?: boolean;
  compact?: boolean;
  color?: 'blue' | 'red' | 'green' | 'yellow';
  maxItems?: number;
  pageSize?: number;
  [key: string]: unknown;
}

export interface DashboardLayout {
  id: string;
  name: string;
  widgets: Widget[];
  isDefault?: boolean;
  createdAt: Date;
  updatedAt: Date;
}

export interface DashboardTemplate {
  id: string;
  name: string;
  description: string;
  category: string;
  widgets: Omit<Widget, 'id' | 'position'>[];
  thumbnail?: string;
}

export interface DashboardState {
  currentLayout: DashboardLayout;
  availableWidgets: WidgetType[];
  isEditing: boolean;
  templates: DashboardTemplate[];
}

export interface SystemHealthData {
  services: SystemHealthService[];
}

export interface SystemHealthService {
  id: string;
  name: string;
  status: 'healthy' | 'warning' | 'critical' | 'unknown';
  uptime: number;
  response_time: number;
  last_checked: Date;
  error_count: number;
  description: string;
}