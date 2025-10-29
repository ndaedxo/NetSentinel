import { useState } from 'react';
import {
  Save,
  RotateCcw,
  Grid,
  BarChart3,
  Activity,
  Shield,
  Network,
  FileText,
  TrendingUp,
  X
} from 'lucide-react';
import { useDashboard } from '@/hooks/useDashboard';
import type { WidgetType } from '@/types/dashboard';

interface DashboardCustomizerProps {
  isOpen: boolean;
  onClose: () => void;
}

const WIDGET_TYPES: Array<{
  type: WidgetType;
  name: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  category: string;
}> = [
  {
    type: 'stat-card',
    name: 'Metric Card',
    description: 'Display key metrics and statistics',
    icon: BarChart3,
    category: 'Metrics'
  },
  {
    type: 'threat-timeline',
    name: 'Threat Timeline',
    description: 'Visual timeline of security events',
    icon: Activity,
    category: 'Threats'
  },
  {
    type: 'alert-feed',
    name: 'Alert Feed',
    description: 'Real-time security alerts',
    icon: Shield,
    category: 'Alerts'
  },
  {
    type: 'system-health',
    name: 'System Health',
    description: 'Monitor system and service status',
    icon: Network,
    category: 'Infrastructure'
  },
  {
    type: 'threat-table',
    name: 'Threat Table',
    description: 'Detailed threat intelligence table',
    icon: FileText,
    category: 'Threats'
  },
  {
    type: 'network-graph',
    name: 'Network Graph',
    description: 'Network topology visualization',
    icon: Network,
    category: 'Network'
  },
  {
    type: 'custom-chart',
    name: 'Custom Chart',
    description: 'Configurable data visualizations',
    icon: TrendingUp,
    category: 'Analytics'
  }
];

export default function DashboardCustomizer({ isOpen, onClose }: DashboardCustomizerProps) {
  const { state, addWidget, saveLayout, resetToDefault, loadTemplate } = useDashboard();
  const [selectedCategory, setSelectedCategory] = useState<string>('All');
  const [layoutName, setLayoutName] = useState('');

  if (!isOpen) return null;

  const categories = ['All', ...Array.from(new Set(WIDGET_TYPES.map(w => w.category)))];

  const filteredWidgets = selectedCategory === 'All'
    ? WIDGET_TYPES
    : WIDGET_TYPES.filter(w => w.category === selectedCategory);

  const handleAddWidget = (type: WidgetType) => {
    // Find next available position
    const existingPositions = state.currentLayout.widgets.map(w => `${w.position.x},${w.position.y}`);
    let x = 0, y = 0;

    while (existingPositions.includes(`${x},${y}`)) {
      x++;
      if (x >= 3) { // Assuming 3 columns max
        x = 0;
        y++;
      }
    }

    addWidget(type, { x, y });
  };

  const handleSaveLayout = () => {
    if (layoutName.trim()) {
      saveLayout(layoutName.trim());
      setLayoutName('');
      // Could show success toast here
    }
  };

  const handleLoadTemplate = (templateId: string) => {
    loadTemplate(templateId);
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-700 rounded-lg shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden">
        <div className="flex h-full">
          {/* Sidebar */}
          <div className="w-80 bg-slate-800/50 border-r border-slate-700 p-6 overflow-y-auto">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold text-slate-200">Customize Dashboard</h2>
              <button
                onClick={onClose}
                className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
              >
                <X className="w-5 h-5 text-slate-400" />
              </button>
            </div>

            {/* Layout Actions */}
            <div className="space-y-4 mb-6">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Save Current Layout
                </label>
                <div className="flex space-x-2">
                  <input
                    type="text"
                    value={layoutName}
                    onChange={(e) => setLayoutName(e.target.value)}
                    placeholder="Layout name"
                    className="flex-1 px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-slate-200 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <button
                    onClick={handleSaveLayout}
                    disabled={!layoutName.trim()}
                    className="px-3 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-600 disabled:cursor-not-allowed text-white rounded-lg transition-colors flex items-center space-x-1"
                  >
                    <Save className="w-4 h-4" />
                    <span>Save</span>
                  </button>
                </div>
              </div>

              <div className="flex space-x-2">
                <button
                  onClick={resetToDefault}
                  className="flex-1 px-3 py-2 bg-slate-700 hover:bg-slate-600 text-slate-300 rounded-lg transition-colors flex items-center justify-center space-x-1"
                >
                  <RotateCcw className="w-4 h-4" />
                  <span>Reset</span>
                </button>
              </div>
            </div>

            {/* Templates */}
            <div className="mb-6">
              <h3 className="text-lg font-medium text-slate-200 mb-3">Templates</h3>
              <div className="space-y-2">
                {state.templates.map((template) => (
                  <button
                    key={template.id}
                    onClick={() => handleLoadTemplate(template.id)}
                    className="w-full text-left p-3 bg-slate-700/50 hover:bg-slate-700 rounded-lg transition-colors group"
                  >
                    <div className="font-medium text-slate-200 group-hover:text-white">
                      {template.name}
                    </div>
                    <div className="text-sm text-slate-400 group-hover:text-slate-300">
                      {template.description}
                    </div>
                    <div className="text-xs text-slate-500 mt-1">
                      {template.category}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Main Content */}
          <div className="flex-1 p-6 overflow-y-auto">
            {/* Category Filter */}
            <div className="mb-6">
              <div className="flex flex-wrap gap-2">
                {categories.map((category) => (
                  <button
                    key={category}
                    onClick={() => setSelectedCategory(category)}
                    className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
                      selectedCategory === category
                        ? 'bg-blue-500 text-white'
                        : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                    }`}
                  >
                    {category}
                  </button>
                ))}
              </div>
            </div>

            {/* Widget Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredWidgets.map((widgetType) => {
                const Icon = widgetType.icon;
                return (
                  <button
                    key={widgetType.type}
                    onClick={() => handleAddWidget(widgetType.type)}
                    className="p-4 bg-slate-800/50 hover:bg-slate-700 border border-slate-600 hover:border-slate-500 rounded-lg transition-all duration-200 group text-left"
                  >
                    <div className="flex items-start space-x-3">
                      <div className="p-2 bg-slate-700 group-hover:bg-slate-600 rounded-lg transition-colors">
                        <Icon className="w-5 h-5 text-slate-300 group-hover:text-white" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <h3 className="font-medium text-slate-200 group-hover:text-white truncate">
                          {widgetType.name}
                        </h3>
                        <p className="text-sm text-slate-400 group-hover:text-slate-300 mt-1">
                          {widgetType.description}
                        </p>
                        <div className="flex items-center mt-2 text-xs text-slate-500">
                          <Grid className="w-3 h-3 mr-1" />
                          {widgetType.category}
                        </div>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>

            {/* Current Widgets List */}
            <div className="mt-8">
              <h3 className="text-lg font-medium text-slate-200 mb-4">Current Widgets</h3>
              <div className="space-y-2">
                {state.currentLayout.widgets.map((widget) => (
                  <div
                    key={widget.id}
                    className="flex items-center justify-between p-3 bg-slate-800/50 border border-slate-700 rounded-lg"
                  >
                    <div>
                      <span className="font-medium text-slate-200">{widget.title}</span>
                      <span className="text-sm text-slate-400 ml-2">
                        ({widget.type} - {widget.size.width}x{widget.size.height})
                      </span>
                    </div>
                    <button
                      onClick={() => {/* Remove widget */}}
                      className="p-1 text-slate-400 hover:text-red-400 transition-colors"
                      title="Remove widget"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
