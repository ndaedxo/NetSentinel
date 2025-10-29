import { useState, useMemo, useCallback } from 'react';
import type {
  FilterState,
  FilterGroup,
  FilterCondition,
  FilterField,
  FilterPreset
} from '@/types/filter';

// Filter evaluation functions
function evaluateCondition<T = unknown>(condition: FilterCondition, item: T): boolean {
  const { field, operator, value, value2 } = condition;
  const itemValue = getNestedValue(item, field);

  switch (operator) {
    case 'equals':
      return itemValue === value;
    case 'not_equals':
      return itemValue !== value;
    case 'contains':
      return String(itemValue).toLowerCase().includes(String(value).toLowerCase());
    case 'not_contains':
      return !String(itemValue).toLowerCase().includes(String(value).toLowerCase());
    case 'starts_with':
      return String(itemValue).toLowerCase().startsWith(String(value).toLowerCase());
    case 'ends_with':
      return String(itemValue).toLowerCase().endsWith(String(value).toLowerCase());
    case 'greater_than':
      return Number(itemValue) > Number(value);
    case 'less_than':
      return Number(itemValue) < Number(value);
    case 'greater_equal':
      return Number(itemValue) >= Number(value);
    case 'less_equal':
      return Number(itemValue) <= Number(value);
    case 'between':
      return Number(itemValue) >= Number(value) && Number(itemValue) <= Number(value2);
    case 'in':
      return Array.isArray(value) ? value.includes(itemValue) : false;
    case 'not_in':
      return Array.isArray(value) ? !value.includes(itemValue) : true;
    case 'is_null':
      return itemValue === null || itemValue === undefined || itemValue === '';
    case 'is_not_null':
      return itemValue !== null && itemValue !== undefined && itemValue !== '';
    default:
      return true;
  }
}

function evaluateGroup<T = unknown>(group: FilterGroup, item: T): boolean {
  const { logic, conditions, groups } = group;

  const conditionResults = conditions.map(condition => evaluateCondition(condition, item));
  const groupResults = groups.map(subGroup => evaluateGroup(subGroup, item));

  const allResults = [...conditionResults, ...groupResults];

  if (logic === 'AND') {
    return allResults.every(result => result);
  } else {
    return allResults.some(result => result);
  }
}

function getNestedValue<T = unknown>(obj: T, path: string): unknown {
  return path.split('.').reduce((current, key) => current?.[key], obj);
}

export function useFilters<T>(
  initialData: T[],
  availableFields: FilterField[],
  initialPresets: FilterPreset[] = []
) {
  const [filterState, setFilterState] = useState<FilterState>({
    rootGroup: {
      id: 'root',
      logic: 'AND',
      conditions: [],
      groups: []
    },
    availableFields,
    presets: initialPresets,
    isAdvanced: false
  });

  // Filter the data based on current filter state
  const filteredData = useMemo(() => {
    const { rootGroup } = filterState;

    // If no filters are active, return all data
    const hasFilters = rootGroup.conditions.length > 0 ||
                      rootGroup.groups.some(g => g.conditions.length > 0 || g.groups.length > 0);

    if (!hasFilters) {
      return initialData;
    }

    return initialData.filter(item => evaluateGroup(rootGroup, item));
  }, [initialData, filterState]);

  const updateFilterState = useCallback((newState: FilterState) => {
    setFilterState(newState);
  }, []);

  const applyFilters = useCallback(() => {
    // This is called when filters are applied
    // The filteredData will automatically update due to the useMemo dependency
  }, []);

  const clearFilters = useCallback(() => {
    setFilterState(prev => ({
      ...prev,
      rootGroup: {
        id: 'root',
        logic: 'AND',
        conditions: [],
        groups: []
      },
      activePreset: undefined
    }));
  }, []);

  const savePreset = useCallback((name: string, category?: string) => {
    const newPreset: FilterPreset = {
      id: `preset-${Date.now()}`,
      name,
      category,
      filters: filterState.rootGroup
    };

    setFilterState(prev => ({
      ...prev,
      presets: [...prev.presets, newPreset]
    }));

    return newPreset;
  }, [filterState.rootGroup]);

  const loadPreset = useCallback((preset: FilterPreset) => {
    setFilterState(prev => ({
      ...prev,
      rootGroup: preset.filters,
      activePreset: preset
    }));
  }, []);

  const deletePreset = useCallback((presetId: string) => {
    setFilterState(prev => ({
      ...prev,
      presets: prev.presets.filter(p => p.id !== presetId),
      activePreset: prev.activePreset?.id === presetId ? undefined : prev.activePreset
    }));
  }, []);

  return {
    filterState,
    filteredData,
    updateFilterState,
    applyFilters,
    clearFilters,
    savePreset,
    loadPreset,
    deletePreset
  };
}

// Utility function to create filter presets
export function createFilterPreset(
  name: string,
  conditions: Omit<FilterCondition, 'id'>[],
  logic: FilterLogic = 'AND',
  category?: string
): FilterPreset {
  return {
    id: `preset-${Date.now()}`,
    name,
    category,
    filters: {
      id: 'root',
      logic,
      conditions: conditions.map((cond, index) => ({
        ...cond,
        id: `condition-${index}`
      })),
      groups: []
    }
  };
}

// Utility function to get active filter count
export function getActiveFilterCount(filterState: FilterState): number {
  const countConditions = (group: FilterGroup): number => {
    return group.conditions.length + group.groups.reduce((acc, g) => acc + countConditions(g), 0);
  };

  return countConditions(filterState.rootGroup);
}

// Utility function to get filter summary
export function getFilterSummary(filterState: FilterState): string {
  const count = getActiveFilterCount(filterState);
  if (count === 0) return 'No filters applied';
  if (count === 1) return '1 filter applied';
  return `${count} filters applied`;
}
