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

  it('handles null and undefined values gracefully', () => {
    const dataWithNulls = [
      { id: 1, name: 'Item 1', category: null, score: 85 },
      { id: 2, name: 'Item 2', category: undefined, score: 92 },
      { id: 3, name: null, category: 'A', score: 78 },
      { id: 4, name: 'Item 4', category: 'C', score: null },
    ];

    const { result } = renderHook(() => useFilters(dataWithNulls));

    act(() => {
      result.current.updateFilterState({
        rootGroup: {
          id: 'root',
          logic: 'AND',
          conditions: [
            {
              id: '1',
              field: 'category',
              operator: 'equals',
              value: null
            }
          ],
          groups: []
        },
        availableFields: [],
        isAdvanced: false,
        templates: []
      });
    });

    expect(result.current.filteredData).toHaveLength(1); // Only item with null category matches (undefined !== null)
  });

  it('handles type coercion errors gracefully', () => {
    const mixedData = [
      { id: 1, name: 'Item 1', score: '85' }, // string score
      { id: 2, name: 'Item 2', score: 92 },   // number score
      { id: 3, name: 'Item 3', score: null }, // null score
    ];

    const { result } = renderHook(() => useFilters(mixedData));

    act(() => {
      result.current.updateFilterState({
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

    expect(result.current.filteredData).toHaveLength(1); // Only item 2 should match
    expect(result.current.filteredData[0].id).toBe(2);
  });

  it('handles malformed filter conditions', () => {
    act(() => {
      hookResult.current.updateFilterState({
        rootGroup: {
          id: 'root',
          logic: 'AND',
          conditions: [
            {
              id: '1',
              field: '', // empty field
              operator: 'equals',
              value: 'test'
            }
          ],
          groups: []
        },
        availableFields: [],
        isAdvanced: false,
        templates: []
      });
    });

    // Should not crash and filter out items where object !== 'test'
    expect(hookResult.current.filteredData).toHaveLength(0);
  });

  it('handles invalid operators gracefully', () => {
    act(() => {
      hookResult.current.updateFilterState({
        rootGroup: {
          id: 'root',
          logic: 'AND',
          conditions: [
            {
              id: '1',
              field: 'name',
              operator: 'invalid_operator' as any, // invalid operator
              value: 'test'
            }
          ],
          groups: []
        },
        availableFields: [],
        isAdvanced: false,
        templates: []
      });
    });

    // Should return all data for unknown operators (default case returns true)
    expect(hookResult.current.filteredData).toEqual(mockData);
  });

  it('handles non-existent nested fields', () => {
    const { result } = renderHook(() => useFilters(mockData));

    act(() => {
      result.current.updateFilterState({
        rootGroup: {
          id: 'root',
          logic: 'AND',
          conditions: [
            {
              id: '1',
              field: 'non.existent.field',
              operator: 'equals',
              value: 'test'
            }
          ],
          groups: []
        },
        availableFields: [],
        isAdvanced: false,
        templates: []
      });
    });

    // Should not crash and return no matches (undefined !== 'test')
    expect(result.current.filteredData).toHaveLength(0);
  });

  it('handles array operations on non-arrays', () => {
    const { result } = renderHook(() => useFilters(mockData));

    act(() => {
      result.current.updateFilterState({
        rootGroup: {
          id: 'root',
          logic: 'AND',
          conditions: [
            {
              id: '1',
              field: 'name',
              operator: 'in',
              value: 'not_an_array' // string instead of array
            }
          ],
          groups: []
        },
        availableFields: [],
        isAdvanced: false,
        templates: []
      });
    });

    // Should return no matches for 'in' with non-array value
    expect(result.current.filteredData).toHaveLength(0);
  });

  it('handles complex nested filtering with mixed data types', () => {
    const complexData = [
      { id: 1, user: { profile: { age: 25, active: true } }, tags: ['admin', 'user'] },
      { id: 2, user: { profile: { age: 30, active: false } }, tags: ['user'] },
      { id: 3, user: null, tags: [] },
    ];

    const { result } = renderHook(() => useFilters(complexData));

    act(() => {
      result.current.updateFilterState({
        rootGroup: {
          id: 'root',
          logic: 'AND',
          conditions: [
            {
              id: '1',
              field: 'user.profile.age',
              operator: 'greater_than',
              value: 26
            },
            {
              id: '2',
              field: 'user.profile.active',
              operator: 'equals',
              value: false
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
    expect(result.current.filteredData[0].id).toBe(2);
  });
});
