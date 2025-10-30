import { useState } from 'react';
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
    <div className={`bg-slate-800/50 border border-slate-700 rounded-lg ${className}`} role="region" aria-labelledby="filter-builder-title">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-slate-700">
        <div className="flex items-center space-x-3">
          <Filter className="w-5 h-5 text-slate-400" aria-hidden="true" />
          <h3 id="filter-builder-title" className="font-medium text-slate-200">Filters</h3>
          {hasActiveFilters && (
            <span className="px-2 py-1 bg-blue-500/20 text-blue-300 text-xs rounded-full" aria-label="Active filters applied">
              Active
            </span>
          )}
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="p-2 hover:bg-slate-700 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500"
            aria-expanded={isExpanded}
            aria-controls="filter-builder-content"
            aria-label={isExpanded ? "Collapse filter builder" : "Expand filter builder"}
          >
            <ChevronDown className={`w-4 h-4 text-slate-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`} aria-hidden="true" />
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
        <div id="filter-builder-content" className="p-4 space-y-4">
          {/* Save Preset */}
          <fieldset className="flex items-center space-x-3">
            <legend className="sr-only">Save current filters as preset</legend>
            <label htmlFor="preset-name-input" className="sr-only">Preset name</label>
            <input
              id="preset-name-input"
              type="text"
              value={newPresetName}
              onChange={(e) => setNewPresetName(e.target.value)}
              placeholder="Preset name"
              className="flex-1 px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-slate-200 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
              aria-describedby="preset-save-help"
            />
            <button
              onClick={saveAsPreset}
              disabled={!newPresetName.trim()}
              className="flex items-center space-x-2 px-3 py-2 bg-green-600 hover:bg-green-700 disabled:bg-green-800 disabled:text-green-400 text-white rounded-lg transition-colors text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
              aria-describedby="preset-save-help"
            >
              <Save className="w-4 h-4" aria-hidden="true" />
              <span>Save</span>
            </button>
            <div id="preset-save-help" className="sr-only">
              Enter a name and click Save to create a filter preset
            </div>
          </fieldset>

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

  const conditionId = `condition-${condition.id}`;

  return (
    <div className="flex items-center space-x-3 p-3 bg-slate-700/50 rounded-lg" role="group" aria-labelledby={`${conditionId}-label`}>
      {showLogic && (
        <span className="text-slate-400 text-sm font-medium px-2" aria-label={`Logic operator: ${groupLogic}`}>
          {groupLogic}
        </span>
      )}

      {/* Field Selector */}
      <div className="flex items-center space-x-2 min-w-0 flex-1">
        {field && getFieldIcon(field.type)}
        <label htmlFor={`${conditionId}-field`} className="sr-only">Field to filter by</label>
        <select
          id={`${conditionId}-field`}
          value={condition.field}
          onChange={(e) => onUpdate(condition.id, {
            field: e.target.value,
            operator: 'equals',
            value: ''
          })}
          className="flex-1 px-3 py-2 bg-slate-600 border border-slate-500 rounded text-slate-200 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
          aria-describedby={`${conditionId}-field-help`}
        >
          {availableFields.map(field => (
            <option key={field.key} value={field.key}>
              {field.label}
            </option>
          ))}
        </select>
      </div>

      {/* Operator Selector */}
      <label htmlFor={`${conditionId}-operator`} className="sr-only">Filter operator</label>
      <select
        id={`${conditionId}-operator`}
        value={condition.operator}
        onChange={(e) => onUpdate(condition.id, { operator: e.target.value as FilterOperator })}
        className="px-3 py-2 bg-slate-600 border border-slate-500 rounded text-slate-200 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 min-w-32"
        aria-describedby={`${conditionId}-operator-help`}
      >
        {field?.operators.map(operator => (
          <option key={operator} value={operator}>
            {getOperatorLabel(operator)}
          </option>
        ))}
      </select>

      {/* Value Input */}
      <div className="flex-1 min-w-0">
        {renderValueInput(condition, field, onUpdate, conditionId)}
      </div>

      {/* Remove Button */}
      <button
        onClick={() => onRemove(condition.id)}
        className="p-2 text-slate-400 hover:text-red-400 transition-colors focus:outline-none focus:ring-2 focus:ring-red-500 rounded"
        aria-label="Remove this filter condition"
        title="Remove condition"
      >
        <X className="w-4 h-4" aria-hidden="true" />
      </button>

      <div id={`${conditionId}-label`} className="sr-only">
        Filter condition {condition.field} {condition.operator}
      </div>
      <div id={`${conditionId}-field-help`} className="sr-only">
        Select the field you want to filter by
      </div>
      <div id={`${conditionId}-operator-help`} className="sr-only">
        Choose how to compare the field value
      </div>
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
  onUpdate: (conditionId: string, updates: Partial<FilterCondition>) => void,
  conditionId?: string
) {
  if (!field) return null;

  const baseClasses = "w-full px-3 py-2 bg-slate-600 border border-slate-500 rounded text-slate-200 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500";

  switch (field.type) {
    case 'select':
      return (
        <>
          <label htmlFor={`${conditionId}-value`} className="sr-only">Filter value for {field.label}</label>
          <select
            id={`${conditionId}-value`}
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
        </>
      );

    case 'multiselect':
      // For simplicity, using a text input with comma-separated values
      return (
        <>
          <label htmlFor={`${conditionId}-value`} className="sr-only">Filter values for {field.label} (comma-separated)</label>
          <input
            id={`${conditionId}-value`}
            type="text"
            value={Array.isArray(condition.value) ? condition.value.join(', ') : condition.value || ''}
            onChange={(e) => onUpdate(condition.id, {
              value: e.target.value.split(',').map(s => s.trim()).filter(Boolean)
            })}
            placeholder="Value 1, Value 2, ..."
            className={baseClasses}
          />
        </>
      );

    case 'date':
      return (
        <>
          <label htmlFor={`${conditionId}-value`} className="sr-only">Filter date for {field.label}</label>
          <input
            id={`${conditionId}-value`}
            type="datetime-local"
            value={condition.value || ''}
            onChange={(e) => onUpdate(condition.id, { value: e.target.value })}
            className={baseClasses}
          />
        </>
      );

    case 'number':
      return (
        <>
          <label htmlFor={`${conditionId}-value`} className="sr-only">Filter number for {field.label}</label>
          <input
            id={`${conditionId}-value`}
            type="number"
            value={condition.value || ''}
            onChange={(e) => onUpdate(condition.id, { value: Number(e.target.value) || '' })}
            placeholder={field.placeholder || "Enter number"}
            className={baseClasses}
          />
        </>
      );

    case 'boolean':
      return (
        <>
          <label htmlFor={`${conditionId}-value`} className="sr-only">Filter boolean for {field.label}</label>
          <select
            id={`${conditionId}-value`}
            value={condition.value ?? ''}
            onChange={(e) => onUpdate(condition.id, { value: e.target.value === 'true' })}
            className={baseClasses}
          >
            <option value="">Select...</option>
            <option value="true">True</option>
            <option value="false">False</option>
          </select>
        </>
      );

    default:
      return (
        <>
          <label htmlFor={`${conditionId}-value`} className="sr-only">Filter value for {field.label}</label>
          <input
            id={`${conditionId}-value`}
            type="text"
            value={condition.value || ''}
            onChange={(e) => onUpdate(condition.id, { value: e.target.value })}
            placeholder={field.placeholder || "Enter value"}
            className={baseClasses}
          />
        </>
      );
  }
}
