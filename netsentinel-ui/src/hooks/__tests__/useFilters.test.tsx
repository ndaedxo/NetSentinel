import { describe, it, expect, beforeEach } from '@jest/globals';
import { renderHook, act } from '@testing-library/react';
import { useFilters } from '../useFilters';

interface TestItem {
  id: number;
  name: string;
  category: string;
  score: number;
}

const mockData: TestItem[] = [
  { id: 1, name: 'Item 1', category: 'A', score: 85 },
  { id: 2, name: 'Item 2', category: 'B', score: 92 },
  { id: 3, name: 'Item 3', category: 'A', score: 78 },
  { id: 4, name: 'Item 4', category: 'C', score: 95 },
];

describe('useFilters', () => {
  let hookResult: {
    filteredData: TestItem[];
    updateFilterState: (state: unknown) => void;
  };

  beforeEach(() => {
    const { result } = renderHook(() => useFilters<TestItem>(mockData));
    hookResult = result;
  });

  it('returns initial data when no filters are applied', () => {
    expect(hookResult.current.filteredData).toEqual(mockData);
  });

  it('filters data by equals condition', () => {
    act(() => {
      hookResult.current.updateFilterState({
        rootGroup: {
          id: 'root',
          logic: 'AND',
          conditions: [
            {
              id: '1',
              field: 'category',
              operator: 'equals',
              value: 'A'
            }
          ],
          groups: []
        },
        availableFields: [],
        isAdvanced: false,
        templates: []
      });
    });

    expect(hookResult.current.filteredData).toHaveLength(2);
    expect(hookResult.current.filteredData.every((item: TestItem) => item.category === 'A')).toBe(true);
  });

  it('filters data by contains condition', () => {
    act(() => {
      hookResult.current.updateFilterState({
        rootGroup: {
          id: 'root',
          logic: 'AND',
          conditions: [
            {
              id: '1',
              field: 'name',
              operator: 'contains',
              value: 'Item 1'
            }
          ],
          groups: []
        },
        availableFields: [],
        isAdvanced: false,
        templates: []
      });
    });

    expect(hookResult.current.filteredData).toHaveLength(1);
    expect(hookResult.current.filteredData[0].name).toBe('Item 1');
  });

  it('filters data by greater_than condition', () => {
    act(() => {
      hookResult.current.updateFilterState({
        rootGroup: {
          id: 'root',
          logic: 'AND',
          conditions: [
            {
              id: '1',
              field: 'score',
              operator: 'greater_than',
              value: 90
            }
          ],
          groups: []
        },
        availableFields: [],
        isAdvanced: false,
        templates: []
      });
    });

    expect(hookResult.current.filteredData).toHaveLength(2);
    expect(hookResult.current.filteredData.every((item: TestItem) => item.score > 90)).toBe(true);
  });

  it('filters data with OR logic', () => {
    act(() => {
      hookResult.current.updateFilterState({
        rootGroup: {
          id: 'root',
          logic: 'OR',
          conditions: [
            {
              id: '1',
              field: 'category',
              operator: 'equals',
              value: 'A'
            },
            {
              id: '2',
              field: 'score',
              operator: 'greater_than',
              value: 93
            }
          ],
          groups: []
        },
        availableFields: [],
        isAdvanced: false,
        templates: []
      });
    });

    expect(hookResult.current.filteredData).toHaveLength(3); // 2 with category A + 1 with score > 93
  });

  it('supports nested field access', () => {
    const nestedData = [
      { id: 1, user: { name: 'John', age: 25 } },
      { id: 2, user: { name: 'Jane', age: 30 } },
    ];

    const { result } = renderHook(() => useFilters(nestedData));

    act(() => {
      result.current.updateFilterState({
        rootGroup: {
          id: 'root',
          logic: 'AND',
          conditions: [
            {
              id: '1',
              field: 'user.age',
              operator: 'greater_than',
              value: 26
            }
          ],
          groups: []
        },
        availableFields: [],
        isAdvanced: false,
        templates: []
      });
    });

    expect(result.current.filteredData).toHaveLength(1);
    expect(result.current.filteredData[0].user.name).toBe('Jane');
  });

  it('handles empty filter conditions', () => {
    act(() => {
      hookResult.current.updateFilterState({
        rootGroup: {
          id: 'root',
          logic: 'AND',
          conditions: [],
          groups: []
        },
        availableFields: [],
        isAdvanced: false,
        templates: []
      });
    });

    expect(hookResult.current.filteredData).toEqual(mockData);
  });
});
