export type CorrelationGroupType = 'AND' | 'OR';

export interface RuleCondition {
  field: string;
  op: string;
  value: string;
}

export interface CorrelationGroup {
  type: CorrelationGroupType;
  conditions: RuleCondition[];
}

export interface CorrelationDSL {
  type: 'correlation_rule';
  groups: CorrelationGroup[];
}


