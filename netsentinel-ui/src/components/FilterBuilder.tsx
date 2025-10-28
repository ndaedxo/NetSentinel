import React, { useState, useEffect } from 'react';
import {
  Plus,
  X,
  Filter,
  ChevronDown,
  Save,
  RotateCcw,
  Settings,
  Search,
  Calendar,
  Hash,
  Type,
  CheckSquare
} from 'lucide-react';
import type {
  FilterState,
  FilterGroup,
  FilterCondition,
  FilterField,
  FilterOperator,
  FilterLogic,
  FilterPreset
} from '@/types/filter';

interface FilterBuilderProps {
  filterState: FilterState;
  onFilterChange: (newState: FilterState) => void;
  onApplyFilters: () => void;
  onClearFilters: () => void;
  className?: string;
}

export default function FilterBuilder({
  filterState,
  onFilterChange,
  onApplyFilters,
  onClearFilters,
  className = ''
}: FilterBuilderProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [newPresetName, setNewPresetName] = useState('');

  const toggleAdvanced = () => {
    onFilterChange({
      ...filterState,
      isAdvanced: !filterState.isAdvanced
    });
  };

  const addCondition = (groupId: string) => {
    const addToGroup = (group: FilterGroup): FilterGroup => {
      if (group.id === groupId) {
        const newCondition: FilterCondition = {
          id: `condition-${Date.now()}`,
          field: filterState.availableFields[0]?.key || '',
          operator: 'equals',
          value: ''
        };
        return {
          ...group,
          conditions: [...group.conditions, newCondition]
        };
      }
      return {
        ...group,
        groups: group.groups.map(addToGroup)
      };
    };

    onFilterChange({
      ...filterState,
      rootGroup: addToGroup(filterState.rootGroup)
    });
  };

  const addGroup = (parentGroupId: string) => {
    const addToGroup = (group: FilterGroup): FilterGroup => {
      if (group.id === parentGroupId) {
        const newGroup: FilterGroup = {
          id: `group-${Date.now()}`,
          logic: 'AND',
          conditions: [],
          groups: []
        };
        return {
          ...group,
          groups: [...group.groups, newGroup]
        };
      }
      return {
        ...group,
        groups: group.groups.map(addToGroup)
      };
    };

    onFilterChange({
      ...filterState,
      rootGroup: addToGroup(filterState.rootGroup)
    });
  };

  const updateCondition = (conditionId: string, updates: Partial<FilterCondition>) => {
    const updateInGroup = (group: FilterGroup): FilterGroup => ({
      ...group,
      conditions: group.conditions.map(cond =>
        cond.id === conditionId ? { ...cond, ...updates } : cond
      ),
      groups: group.groups.map(updateInGroup)
    });

    onFilterChange({
      ...filterState,
      rootGroup: updateInGroup(filterState.rootGroup)
    });
  };

  const removeCondition = (conditionId: string) => {
    const removeFromGroup = (group: FilterGroup): FilterGroup => ({
      ...group,
      conditions: group.conditions.filter(cond => cond.id !== conditionId),
      groups: group.groups.map(removeFromGroup)
    });

    onFilterChange({
      ...filterState,
      rootGroup: removeFromGroup(filterState.rootGroup)
    });
  };

  const updateGroupLogic = (groupId: string, logic: FilterLogic) => {
    const updateInGroup = (group: FilterGroup): FilterGroup => {
      if (group.id === groupId) {
        return { ...group, logic };
      }
      return {
        ...group,
        groups: group.groups.map(updateInGroup)
      };
    };

    onFilterChange({
      ...filterState,
      rootGroup: updateInGroup(filterState.rootGroup)
    });
  };

  const saveAsPreset = () => {
    if (!newPresetName.trim()) return;

    const newPreset: FilterPreset = {
      id: `preset-${Date.now()}`,
      name: newPresetName.trim(),
      filters: filterState.rootGroup,
      category: 'Custom'
    };

    onFilterChange({
      ...filterState,
      presets: [...filterState.presets, newPreset]
    });

    setNewPresetName('');
  };

  const loadPreset = (preset: FilterPreset) => {
    onFilterChange({
      ...filterState,
      rootGroup: preset.filters,
      activePreset: preset
    });
  };

  const clearFilters = () => {
    const emptyGroup: FilterGroup = {
      id: 'root',
      logic: 'AND',
      conditions: [],
      groups: []
    };

    onFilterChange({
      ...filterState,
      rootGroup: emptyGroup,
      activePreset: undefined
    });

    onClearFilters();
  };

  const hasActiveFilters = filterState.rootGroup.conditions.length > 0 ||
                          filterState.rootGroup.groups.some(g => g.conditions.length > 0 || g.groups.length > 0);

  return (
    <div className={`bg-slate-800/50 border border-slate-700 rounded-lg ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-slate-700">
        <div className="flex items-center space-x-3">
          <Filter className="w-5 h-5 text-slate-400" />
          <h3 className="font-medium text-slate-200">Filters</h3>
          {hasActiveFilters && (
            <span className="px-2 py-1 bg-blue-500/20 text-blue-300 text-xs rounded-full">
              Active
            </span>
          )}
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
          >
            <ChevronDown className={`w-4 h-4 text-slate-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`} />
          </button>
        </div>
      </div>

      {/* Filter Controls */}
      <div className="p-4 border-b border-slate-700">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div className="flex items-center space-x-3">
            {/* Preset Selector */}
            <select
              value={filterState.activePreset?.id || ''}
              onChange={(e) => {
                const preset = filterState.presets.find(p => p.id === e.target.value);
                if (preset) loadPreset(preset);
              }}
              className="px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Custom Filters</option>
              {filterState.presets.map(preset => (
                <option key={preset.id} value={preset.id}>
                  {preset.name}
                </option>
              ))}
            </select>

            {/* Advanced Toggle */}
            <button
              onClick={toggleAdvanced}
              className={`flex items-center space-x-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                filterState.isAdvanced
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
              }`}
            >
              <Settings className="w-4 h-4" />
              <span>Advanced</span>
            </button>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={clearFilters}
              disabled={!hasActiveFilters}
              className="flex items-center space-x-2 px-3 py-2 bg-slate-700 hover:bg-slate-600 disabled:bg-slate-800 disabled:text-slate-500 text-slate-300 rounded-lg transition-colors text-sm"
            >
              <RotateCcw className="w-4 h-4" />
              <span>Clear</span>
            </button>

            <button
              onClick={onApplyFilters}
              className="flex items-center space-x-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors text-sm font-medium"
            >
              <Search className="w-4 h-4" />
              <span>Apply Filters</span>
            </button>
          </div>
        </div>
      </div>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="p-4 space-y-4">
          {/* Save Preset */}
          <div className="flex items-center space-x-3">
            <input
              type="text"
              value={newPresetName}
              onChange={(e) => setNewPresetName(e.target.value)}
              placeholder="Preset name"
              className="flex-1 px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-slate-200 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
            />
            <button
              onClick={saveAsPreset}
              disabled={!newPresetName.trim()}
              className="flex items-center space-x-2 px-3 py-2 bg-green-600 hover:bg-green-700 disabled:bg-green-800 disabled:text-green-400 text-white rounded-lg transition-colors text-sm"
            >
              <Save className="w-4 h-4" />
              <span>Save</span>
            </button>
          </div>

          {/* Filter Builder */}
          <FilterGroupComponent
            group={filterState.rootGroup}
            availableFields={filterState.availableFields}
            onAddCondition={addCondition}
            onAddGroup={addGroup}
            onUpdateCondition={updateCondition}
            onRemoveCondition={removeCondition}
            onUpdateLogic={updateGroupLogic}
            isRoot={true}
          />
        </div>
      )}
    </div>
  );
}

// Filter Group Component
interface FilterGroupProps {
  group: FilterGroup;
  availableFields: FilterField[];
  onAddCondition: (groupId: string) => void;
  onAddGroup: (groupId: string) => void;
  onUpdateCondition: (conditionId: string, updates: Partial<FilterCondition>) => void;
  onRemoveCondition: (conditionId: string) => void;
  onUpdateLogic: (groupId: string, logic: FilterLogic) => void;
  isRoot?: boolean;
}

function FilterGroupComponent({
  group,
  availableFields,
  onAddCondition,
  onAddGroup,
  onUpdateCondition,
  onRemoveCondition,
  onUpdateLogic,
  isRoot = false
}: FilterGroupProps) {
  return (
    <div className={`${!isRoot ? 'ml-6 border-l-2 border-slate-600 pl-4' : ''}`}>
      {!isRoot && (
        <div className="flex items-center space-x-3 mb-3">
          <select
            value={group.logic}
            onChange={(e) => onUpdateLogic(group.id, e.target.value as FilterLogic)}
            className="px-2 py-1 bg-slate-700 border border-slate-600 rounded text-slate-200 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="AND">AND</option>
            <option value="OR">OR</option>
          </select>
          <span className="text-slate-400 text-sm">conditions</span>
        </div>
      )}

      <div className="space-y-3">
        {/* Conditions */}
        {group.conditions.map((condition, index) => (
          <FilterConditionComponent
            key={condition.id}
            condition={condition}
            availableFields={availableFields}
            onUpdate={onUpdateCondition}
            onRemove={onRemoveCondition}
            showLogic={index > 0}
            groupLogic={group.logic}
          />
        ))}

        {/* Nested Groups */}
        {group.groups.map((nestedGroup) => (
          <FilterGroupComponent
            key={nestedGroup.id}
            group={nestedGroup}
            availableFields={availableFields}
            onAddCondition={onAddCondition}
            onAddGroup={onAddGroup}
            onUpdateCondition={onUpdateCondition}
            onRemoveCondition={onRemoveCondition}
            onUpdateLogic={onUpdateLogic}
          />
        ))}

        {/* Add Buttons */}
        <div className="flex items-center space-x-2 pt-2">
          <button
            onClick={() => onAddCondition(group.id)}
            className="flex items-center space-x-2 px-3 py-2 bg-slate-700 hover:bg-slate-600 text-slate-300 rounded-lg transition-colors text-sm"
          >
            <Plus className="w-4 h-4" />
            <span>Add Condition</span>
          </button>

          <button
            onClick={() => onAddGroup(group.id)}
            className="flex items-center space-x-2 px-3 py-2 bg-slate-700 hover:bg-slate-600 text-slate-300 rounded-lg transition-colors text-sm"
          >
            <Plus className="w-4 h-4" />
            <span>Add Group</span>
          </button>
        </div>
      </div>
    </div>
  );
}

// Filter Condition Component
interface FilterConditionProps {
  condition: FilterCondition;
  availableFields: FilterField[];
  onUpdate: (conditionId: string, updates: Partial<FilterCondition>) => void;
  onRemove: (conditionId: string) => void;
  showLogic?: boolean;
  groupLogic?: FilterLogic;
}

function FilterConditionComponent({
  condition,
  availableFields,
  onUpdate,
  onRemove,
  showLogic = false,
  groupLogic = 'AND'
}: FilterConditionProps) {
  const field = availableFields.find(f => f.key === condition.field);

  const getFieldIcon = (type: string) => {
    switch (type) {
      case 'string': return <Type className="w-4 h-4" />;
      case 'number': return <Hash className="w-4 h-4" />;
      case 'date': return <Calendar className="w-4 h-4" />;
      case 'boolean': return <CheckSquare className="w-4 h-4" />;
      default: return <Type className="w-4 h-4" />;
    }
  };

  return (
    <div className="flex items-center space-x-3 p-3 bg-slate-700/50 rounded-lg">
      {showLogic && (
        <span className="text-slate-400 text-sm font-medium px-2">
          {groupLogic}
        </span>
      )}

      {/* Field Selector */}
      <div className="flex items-center space-x-2 min-w-0 flex-1">
        {field && getFieldIcon(field.type)}
        <select
          value={condition.field}
          onChange={(e) => onUpdate(condition.id, {
            field: e.target.value,
            operator: 'equals',
            value: ''
          })}
          className="flex-1 px-3 py-2 bg-slate-600 border border-slate-500 rounded text-slate-200 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          {availableFields.map(field => (
            <option key={field.key} value={field.key}>
              {field.label}
            </option>
          ))}
        </select>
      </div>

      {/* Operator Selector */}
      <select
        value={condition.operator}
        onChange={(e) => onUpdate(condition.id, { operator: e.target.value as FilterOperator })}
        className="px-3 py-2 bg-slate-600 border border-slate-500 rounded text-slate-200 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 min-w-32"
      >
        {field?.operators.map(operator => (
          <option key={operator} value={operator}>
            {getOperatorLabel(operator)}
          </option>
        ))}
      </select>

      {/* Value Input */}
      <div className="flex-1 min-w-0">
        {renderValueInput(condition, field, onUpdate)}
      </div>

      {/* Remove Button */}
      <button
        onClick={() => onRemove(condition.id)}
        className="p-2 text-slate-400 hover:text-red-400 transition-colors"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
}

// Helper functions
function getOperatorLabel(operator: FilterOperator): string {
  const labels: Record<FilterOperator, string> = {
    equals: 'Equals',
    not_equals: 'Not Equals',
    contains: 'Contains',
    not_contains: 'Not Contains',
    starts_with: 'Starts With',
    ends_with: 'Ends With',
    greater_than: 'Greater Than',
    less_than: 'Less Than',
    greater_equal: 'Greater Equal',
    less_equal: 'Less Equal',
    between: 'Between',
    in: 'In',
    not_in: 'Not In',
    is_null: 'Is Null',
    is_not_null: 'Is Not Null'
  };
  return labels[operator] || operator;
}

function renderValueInput(
  condition: FilterCondition,
  field: FilterField | undefined,
  onUpdate: (conditionId: string, updates: Partial<FilterCondition>) => void
) {
  if (!field) return null;

  const baseClasses = "w-full px-3 py-2 bg-slate-600 border border-slate-500 rounded text-slate-200 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500";

  switch (field.type) {
    case 'select':
      return (
        <select
          value={condition.value || ''}
          onChange={(e) => onUpdate(condition.id, { value: e.target.value })}
          className={baseClasses}
        >
          <option value="">Select...</option>
          {field.options?.map(option => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      );

    case 'multiselect':
      // For simplicity, using a text input with comma-separated values
      return (
        <input
          type="text"
          value={Array.isArray(condition.value) ? condition.value.join(', ') : condition.value || ''}
          onChange={(e) => onUpdate(condition.id, {
            value: e.target.value.split(',').map(s => s.trim()).filter(Boolean)
          })}
          placeholder="Value 1, Value 2, ..."
          className={baseClasses}
        />
      );

    case 'date':
      return (
        <input
          type="datetime-local"
          value={condition.value || ''}
          onChange={(e) => onUpdate(condition.id, { value: e.target.value })}
          className={baseClasses}
        />
      );

    case 'number':
      return (
        <input
          type="number"
          value={condition.value || ''}
          onChange={(e) => onUpdate(condition.id, { value: Number(e.target.value) || '' })}
          placeholder={field.placeholder || "Enter number"}
          className={baseClasses}
        />
      );

    case 'boolean':
      return (
        <select
          value={condition.value ?? ''}
          onChange={(e) => onUpdate(condition.id, { value: e.target.value === 'true' })}
          className={baseClasses}
        >
          <option value="">Select...</option>
          <option value="true">True</option>
          <option value="false">False</option>
        </select>
      );

    default:
      return (
        <input
          type="text"
          value={condition.value || ''}
          onChange={(e) => onUpdate(condition.id, { value: e.target.value })}
          placeholder={field.placeholder || "Enter value"}
          className={baseClasses}
        />
      );
  }
}
