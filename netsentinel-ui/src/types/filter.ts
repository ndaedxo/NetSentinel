export type FilterOperator =
  | 'equals'
  | 'not_equals'
  | 'contains'
  | 'not_contains'
  | 'starts_with'
  | 'ends_with'
  | 'greater_than'
  | 'less_than'
  | 'greater_equal'
  | 'less_equal'
  | 'between'
  | 'in'
  | 'not_in'
  | 'is_null'
  | 'is_not_null';

export type FilterLogic = 'AND' | 'OR';

export interface FilterCondition {
  id: string;
  field: string;
  operator: FilterOperator;
  value: any;
  value2?: any; // For between operator
}

export interface FilterGroup {
  id: string;
  logic: FilterLogic;
  conditions: FilterCondition[];
  groups: FilterGroup[];
}

export interface FilterPreset {
  id: string;
  name: string;
  description?: string;
  filters: FilterGroup;
  category?: string;
  isDefault?: boolean;
}

export interface FilterField {
  key: string;
  label: string;
  type: 'string' | 'number' | 'date' | 'boolean' | 'select' | 'multiselect';
  operators: FilterOperator[];
  options?: Array<{ value: any; label: string }>; // For select/multiselect
  placeholder?: string;
}

export interface FilterState {
  rootGroup: FilterGroup;
  activePreset?: FilterPreset;
  presets: FilterPreset[];
  availableFields: FilterField[];
  isAdvanced: boolean;
}

// Threat-specific filter fields
export const THREAT_FILTER_FIELDS: FilterField[] = [
  {
    key: 'severity',
    label: 'Severity',
    type: 'select',
    operators: ['equals', 'not_equals', 'in', 'not_in'],
    options: [
      { value: 'critical', label: 'Critical' },
      { value: 'high', label: 'High' },
      { value: 'medium', label: 'Medium' },
      { value: 'low', label: 'Low' },
      { value: 'info', label: 'Info' }
    ]
  },
  {
    key: 'status',
    label: 'Status',
    type: 'select',
    operators: ['equals', 'not_equals', 'in', 'not_in'],
    options: [
      { value: 'active', label: 'Active' },
      { value: 'resolved', label: 'Resolved' },
      { value: 'investigating', label: 'Investigating' },
      { value: 'dismissed', label: 'Dismissed' }
    ]
  },
  {
    key: 'source_ip',
    label: 'Source IP',
    type: 'string',
    operators: ['equals', 'not_equals', 'contains', 'starts_with', 'ends_with']
  },
  {
    key: 'destination_ip',
    label: 'Destination IP',
    type: 'string',
    operators: ['equals', 'not_equals', 'contains', 'starts_with', 'ends_with']
  },
  {
    key: 'timestamp',
    label: 'Timestamp',
    type: 'date',
    operators: ['greater_than', 'less_than', 'between']
  },
  {
    key: 'threat_type',
    label: 'Threat Type',
    type: 'select',
    operators: ['equals', 'not_equals', 'in', 'not_in'],
    options: [
      { value: 'malware', label: 'Malware' },
      { value: 'phishing', label: 'Phishing' },
      { value: 'ddos', label: 'DDoS' },
      { value: 'intrusion', label: 'Intrusion' },
      { value: 'anomaly', label: 'Anomaly' }
    ]
  },
  {
    key: 'confidence',
    label: 'Confidence',
    type: 'number',
    operators: ['equals', 'not_equals', 'greater_than', 'less_than', 'between']
  }
];

// Alert-specific filter fields
export const ALERT_FILTER_FIELDS: FilterField[] = [
  {
    key: 'severity',
    label: 'Severity',
    type: 'select',
    operators: ['equals', 'not_equals', 'in', 'not_in'],
    options: [
      { value: 'critical', label: 'Critical' },
      { value: 'high', label: 'High' },
      { value: 'medium', label: 'Medium' },
      { value: 'low', label: 'Low' }
    ]
  },
  {
    key: 'status',
    label: 'Status',
    type: 'select',
    operators: ['equals', 'not_equals', 'in', 'not_in'],
    options: [
      { value: 'new', label: 'New' },
      { value: 'acknowledged', label: 'Acknowledged' },
      { value: 'resolved', label: 'Resolved' }
    ]
  },
  {
    key: 'source',
    label: 'Source',
    type: 'string',
    operators: ['equals', 'not_equals', 'contains', 'starts_with', 'ends_with']
  },
  {
    key: 'timestamp',
    label: 'Timestamp',
    type: 'date',
    operators: ['greater_than', 'less_than', 'between']
  },
  {
    key: 'category',
    label: 'Category',
    type: 'select',
    operators: ['equals', 'not_equals', 'in', 'not_in'],
    options: [
      { value: 'security', label: 'Security' },
      { value: 'performance', label: 'Performance' },
      { value: 'availability', label: 'Availability' },
      { value: 'compliance', label: 'Compliance' }
    ]
  }
];

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
