import { useState } from 'react';
import { Edit3, Plus, Settings } from 'lucide-react';
import { useDashboard } from '@/hooks/useDashboard';
import DashboardWidget from './DashboardWidget';
import DashboardCustomizer from './DashboardCustomizer';

interface CustomDashboardProps {
  className?: string;
}

export default function CustomDashboard({ className = '' }: CustomDashboardProps) {
  const { state, toggleEditMode } = useDashboard();
  const [showCustomizer, setShowCustomizer] = useState(false);

  const handleEditToggle = () => {
    toggleEditMode();
  };

  const handleOpenCustomizer = () => {
    setShowCustomizer(true);
  };

  const handleCloseCustomizer = () => {
    setShowCustomizer(false);
  };

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Dashboard Controls */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-200">
            {state.currentLayout.name}
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            {state.isEditing ? 'Editing mode - drag and resize widgets' : 'Dashboard overview'}
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={handleOpenCustomizer}
            className="flex items-center space-x-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-slate-300 rounded-lg transition-colors"
          >
            <Plus className="w-4 h-4" />
            <span>Add Widget</span>
          </button>

          <button
            onClick={handleEditToggle}
            className={`flex items-center space-x-2 px-4 py-2 rounded-lg transition-colors ${
              state.isEditing
                ? 'bg-blue-600 hover:bg-blue-700 text-white'
                : 'bg-slate-700 hover:bg-slate-600 text-slate-300'
            }`}
          >
            <Edit3 className="w-4 h-4" />
            <span>{state.isEditing ? 'Done Editing' : 'Edit Layout'}</span>
          </button>
        </div>
      </div>

      {/* Dashboard Grid */}
      <div
        className={`
          grid gap-6 auto-rows-fr
          ${state.isEditing ? 'min-h-screen' : ''}
        `}
        style={{
          gridTemplateColumns: 'repeat(3, 1fr)',
          gridTemplateRows: 'repeat(auto-fill, minmax(200px, 1fr))'
        }}
      >
        {state.currentLayout.widgets.map((widget) => (
          <DashboardWidget
            key={widget.id}
            widget={widget}
            isEditing={state.isEditing}
          />
        ))}
      </div>

      {/* Empty State */}
      {state.currentLayout.widgets.length === 0 && (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <div className="text-6xl mb-4">📊</div>
          <h3 className="text-xl font-semibold text-slate-200 mb-2">
            Your dashboard is empty
          </h3>
          <p className="text-slate-400 mb-6 max-w-md">
            Add widgets to customize your dashboard and monitor your security operations.
          </p>
          <button
            onClick={handleOpenCustomizer}
            className="flex items-center space-x-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
          >
            <Plus className="w-5 h-5" />
            <span>Add Your First Widget</span>
          </button>
        </div>
      )}

      {/* Dashboard Customizer Modal */}
      <DashboardCustomizer
        isOpen={showCustomizer}
        onClose={handleCloseCustomizer}
      />

      {/* Edit Mode Overlay */}
      {state.isEditing && (
        <div className="fixed inset-0 bg-black/20 backdrop-blur-sm z-40 pointer-events-none">
          <div className="absolute top-4 left-1/2 transform -translate-x-1/2 bg-blue-600 text-white px-4 py-2 rounded-lg shadow-lg">
            <div className="flex items-center space-x-2">
              <Settings className="w-4 h-4" />
              <span className="font-medium">Edit Mode Active</span>
              <span className="text-blue-200">•</span>
              <span className="text-sm">Drag widgets to rearrange</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
