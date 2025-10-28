export interface Widget {
  id: string;
  type: WidgetType;
  title: string;
  position: WidgetPosition;
  size: WidgetSize;
  config: WidgetConfig;
  data?: any;
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
  [key: string]: any;
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