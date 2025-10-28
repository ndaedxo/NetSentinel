import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import type {
  Widget,
  DashboardLayout,
  DashboardTemplate,
  DashboardState,
  WidgetType,
  WidgetPosition,
  WidgetSize,
  WidgetConfig
} from '@/types/dashboard';

// Dashboard templates
const DEFAULT_TEMPLATES: DashboardTemplate[] = [
  {
    id: 'security-overview',
    name: 'Security Overview',
    description: 'Comprehensive security metrics and alerts dashboard',
    category: 'Security',
    widgets: [
      {
        type: 'stat-card',
        title: 'Total Events',
        size: { width: 1, height: 1 },
        config: { refreshInterval: 5000 }
      },
      {
        type: 'stat-card',
        title: 'Active Threats',
        size: { width: 1, height: 1 },
        config: { refreshInterval: 10000 }
      },
      {
        type: 'threat-timeline',
        title: 'Threat Timeline',
        size: { width: 2, height: 2 },
        config: { refreshInterval: 30000 }
      },
      {
        type: 'alert-feed',
        title: 'Recent Alerts',
        size: { width: 1, height: 2 },
        config: { refreshInterval: 10000, compact: true }
      }
    ]
  },
  {
    id: 'threat-analysis',
    name: 'Threat Analysis',
    description: 'Detailed threat intelligence and analysis',
    category: 'Threats',
    widgets: [
      {
        type: 'threat-table',
        title: 'Threat Intelligence',
        size: { width: 3, height: 3 },
        config: { refreshInterval: 30000 }
      },
      {
        type: 'custom-chart',
        title: 'Threat Trends',
        size: { width: 2, height: 2 },
        config: { chartType: 'line', refreshInterval: 60000 }
      }
    ]
  },
  {
    id: 'system-health',
    name: 'System Health',
    description: 'Monitor system and network health',
    category: 'Infrastructure',
    widgets: [
      {
        type: 'system-health',
        title: 'System Status',
        size: { width: 2, height: 2 },
        config: { refreshInterval: 15000 }
      },
      {
        type: 'network-graph',
        title: 'Network Topology',
        size: { width: 2, height: 2 },
        config: { refreshInterval: 60000 }
      }
    ]
  }
];

// Default dashboard layout
const createDefaultLayout = (): DashboardLayout => ({
  id: 'default',
  name: 'Default Dashboard',
  isDefault: true,
  createdAt: new Date(),
  updatedAt: new Date(),
  widgets: [
    {
      id: 'total-events',
      type: 'stat-card',
      title: 'Total Events',
      position: { x: 0, y: 0 },
      size: { width: 1, height: 1 },
      config: { refreshInterval: 5000 }
    },
    {
      id: 'active-threats',
      type: 'stat-card',
      title: 'Active Threats',
      position: { x: 1, y: 0 },
      size: { width: 1, height: 1 },
      config: { refreshInterval: 10000 }
    },
    {
      id: 'blocked-ips',
      type: 'stat-card',
      title: 'Blocked IPs',
      position: { x: 2, y: 0 },
      size: { width: 1, height: 1 },
      config: { refreshInterval: 15000 }
    },
    {
      id: 'threat-timeline',
      type: 'threat-timeline',
      title: 'Threat Timeline',
      position: { x: 0, y: 1 },
      size: { width: 2, height: 2 },
      config: { refreshInterval: 30000 }
    },
    {
      id: 'alert-feed',
      type: 'alert-feed',
      title: 'Active Alerts',
      position: { x: 2, y: 1 },
      size: { width: 1, height: 2 },
      config: { refreshInterval: 10000 }
    },
    {
      id: 'system-health',
      type: 'system-health',
      title: 'System Health',
      position: { x: 0, y: 3 },
      size: { width: 3, height: 1 },
      config: { refreshInterval: 15000 }
    }
  ]
});

interface DashboardContextType {
  state: DashboardState;
  addWidget: (type: WidgetType, position?: WidgetPosition) => void;
  removeWidget: (widgetId: string) => void;
  updateWidget: (widgetId: string, updates: Partial<Widget>) => void;
  moveWidget: (widgetId: string, position: WidgetPosition) => void;
  resizeWidget: (widgetId: string, size: WidgetSize) => void;
  saveLayout: (name: string) => void;
  loadLayout: (layoutId: string) => void;
  loadTemplate: (templateId: string) => void;
  toggleEditMode: () => void;
  resetToDefault: () => void;
}

const DashboardContext = createContext<DashboardContextType | undefined>(undefined);

const STORAGE_KEY = 'netsentinel-dashboard-layouts';

export function DashboardProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<DashboardState>(() => ({
    currentLayout: createDefaultLayout(),
    availableWidgets: [
      'stat-card',
      'threat-timeline',
      'alert-feed',
      'system-health',
      'threat-table',
      'network-graph',
      'custom-chart'
    ],
    isEditing: false,
    templates: DEFAULT_TEMPLATES
  }));

  // Load saved layouts from localStorage
  useEffect(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const layouts = JSON.parse(saved);
        // Find the last used layout or use default
        const lastLayout = layouts.find((l: DashboardLayout) => l.id === 'current') || layouts[0];
        if (lastLayout) {
          setState(prev => ({
            ...prev,
            currentLayout: {
              ...lastLayout,
              createdAt: new Date(lastLayout.createdAt),
              updatedAt: new Date(lastLayout.updatedAt)
            }
          }));
        }
      }
    } catch (error) {
      console.error('Failed to load dashboard layouts:', error);
    }
  }, []);

  // Save current layout to localStorage
  const saveLayoutToStorage = (layout: DashboardLayout) => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      const layouts = saved ? JSON.parse(saved) : [];
      const existingIndex = layouts.findIndex((l: DashboardLayout) => l.id === layout.id);

      if (existingIndex >= 0) {
        layouts[existingIndex] = layout;
      } else {
        layouts.push(layout);
      }

      localStorage.setItem(STORAGE_KEY, JSON.stringify(layouts));
    } catch (error) {
      console.error('Failed to save dashboard layout:', error);
    }
  };

  const addWidget = (type: WidgetType, position: WidgetPosition = { x: 0, y: 0 }) => {
    const newWidget: Widget = {
      id: `${type}-${Date.now()}`,
      type,
      title: getWidgetDefaultTitle(type),
      position,
      size: getWidgetDefaultSize(type),
      config: getWidgetDefaultConfig(type)
    };

    setState(prev => {
      const updatedLayout = {
        ...prev.currentLayout,
        widgets: [...prev.currentLayout.widgets, newWidget],
        updatedAt: new Date()
      };
      saveLayoutToStorage(updatedLayout);
      return {
        ...prev,
        currentLayout: updatedLayout
      };
    });
  };

  const removeWidget = (widgetId: string) => {
    setState(prev => {
      const updatedLayout = {
        ...prev.currentLayout,
        widgets: prev.currentLayout.widgets.filter(w => w.id !== widgetId),
        updatedAt: new Date()
      };
      saveLayoutToStorage(updatedLayout);
      return {
        ...prev,
        currentLayout: updatedLayout
      };
    });
  };

  const updateWidget = (widgetId: string, updates: Partial<Widget>) => {
    setState(prev => {
      const updatedLayout = {
        ...prev.currentLayout,
        widgets: prev.currentLayout.widgets.map(w =>
          w.id === widgetId ? { ...w, ...updates } : w
        ),
        updatedAt: new Date()
      };
      saveLayoutToStorage(updatedLayout);
      return {
        ...prev,
        currentLayout: updatedLayout
      };
    });
  };

  const moveWidget = (widgetId: string, position: WidgetPosition) => {
    updateWidget(widgetId, { position });
  };

  const resizeWidget = (widgetId: string, size: WidgetSize) => {
    updateWidget(widgetId, { size });
  };

  const saveLayout = (name: string) => {
    const newLayout: DashboardLayout = {
      ...state.currentLayout,
      id: `layout-${Date.now()}`,
      name,
      isDefault: false,
      updatedAt: new Date()
    };

    saveLayoutToStorage(newLayout);
    // Could show a toast notification here
  };

  const loadLayout = (layoutId: string) => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const layouts = JSON.parse(saved);
        const layout = layouts.find((l: DashboardLayout) => l.id === layoutId);
        if (layout) {
          setState(prev => ({
            ...prev,
            currentLayout: {
              ...layout,
              createdAt: new Date(layout.createdAt),
              updatedAt: new Date(layout.updatedAt)
            }
          }));
        }
      }
    } catch (error) {
      console.error('Failed to load layout:', error);
    }
  };

  const loadTemplate = (templateId: string) => {
    const template = state.templates.find(t => t.id === templateId);
    if (template) {
      const layoutFromTemplate: DashboardLayout = {
        id: `template-${templateId}-${Date.now()}`,
        name: template.name,
        widgets: template.widgets.map((widget, index) => ({
          ...widget,
          id: `${widget.type}-${Date.now()}-${index}`,
          position: { x: (index % 3), y: Math.floor(index / 3) }
        })),
        isDefault: false,
        createdAt: new Date(),
        updatedAt: new Date()
      };

      setState(prev => ({
        ...prev,
        currentLayout: layoutFromTemplate
      }));
    }
  };

  const toggleEditMode = () => {
    setState(prev => ({ ...prev, isEditing: !prev.isEditing }));
  };

  const resetToDefault = () => {
    setState(prev => ({
      ...prev,
      currentLayout: createDefaultLayout()
    }));
  };

  const contextValue: DashboardContextType = {
    state,
    addWidget,
    removeWidget,
    updateWidget,
    moveWidget,
    resizeWidget,
    saveLayout,
    loadLayout,
    loadTemplate,
    toggleEditMode,
    resetToDefault
  };

  return (
    <DashboardContext.Provider value={contextValue}>
      {children}
    </DashboardContext.Provider>
  );
}

export function useDashboard() {
  const context = useContext(DashboardContext);
  if (context === undefined) {
    throw new Error('useDashboard must be used within a DashboardProvider');
  }
  return context;
}

// Helper functions
function getWidgetDefaultTitle(type: WidgetType): string {
  const titles: Record<WidgetType, string> = {
    'stat-card': 'New Metric',
    'threat-timeline': 'Threat Timeline',
    'alert-feed': 'Alerts',
    'system-health': 'System Health',
    'threat-table': 'Threats',
    'network-graph': 'Network Graph',
    'custom-chart': 'Chart'
  };
  return titles[type] || 'Widget';
}

function getWidgetDefaultSize(type: WidgetType): WidgetSize {
  const sizes: Record<WidgetType, WidgetSize> = {
    'stat-card': { width: 1, height: 1 },
    'threat-timeline': { width: 2, height: 2 },
    'alert-feed': { width: 1, height: 2 },
    'system-health': { width: 2, height: 1 },
    'threat-table': { width: 3, height: 3 },
    'network-graph': { width: 2, height: 2 },
    'custom-chart': { width: 2, height: 2 }
  };
  return sizes[type] || { width: 1, height: 1 };
}

function getWidgetDefaultConfig(type: WidgetType): WidgetConfig {
  const configs: Record<WidgetType, WidgetConfig> = {
    'stat-card': { refreshInterval: 5000, showHeader: true },
    'threat-timeline': { refreshInterval: 30000, showHeader: true },
    'alert-feed': { refreshInterval: 10000, showHeader: true, compact: false },
    'system-health': { refreshInterval: 15000, showHeader: true },
    'threat-table': { refreshInterval: 30000, showHeader: true },
    'network-graph': { refreshInterval: 60000, showHeader: true },
    'custom-chart': { refreshInterval: 30000, showHeader: true, chartType: 'bar' }
  };
  return configs[type] || { showHeader: true };
}
