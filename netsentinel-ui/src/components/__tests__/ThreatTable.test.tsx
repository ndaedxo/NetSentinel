import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, jest, beforeEach } from '@jest/globals';

import ThreatTable from '../ThreatTable';
import { testA11y } from '../../test/test-utils';

/* eslint-disable @typescript-eslint/no-require-imports */

// Mock dependencies
jest.mock('date-fns', () => ({
  formatDistanceToNow: jest.fn(() => '2 hours ago'),
}));

jest.mock('@/utils', () => ({
  getThreatColorClasses: jest.fn((severity) => {
    switch (severity) {
      case 'critical':
        return 'bg-red-500/20 text-red-300 border-red-500/30';
      case 'high':
        return 'bg-orange-500/20 text-orange-300 border-orange-500/30';
      case 'medium':
        return 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30';
      default:
        return 'bg-blue-500/20 text-blue-300 border-blue-500/30';
    }
  }),
  export: {
    THREAT_EXPORT_COLUMNS: [
      { key: 'ip_address', label: 'IP Address' },
      { key: 'threat_type', label: 'Threat Type' },
      { key: 'severity', label: 'Severity' },
      { key: 'threat_score', label: 'Score' },
      { key: 'created_at', label: 'Time' },
    ],
  },
}));

jest.mock('@/hooks/useFilters', () => ({
  useFilters: jest.fn(),
}));

jest.mock('../FilterBuilder', () => {
  return function MockFilterBuilder({ onFilterChange, onApplyFilters, onClearFilters }: any) {
    return (
      <div data-testid="mock-filter-builder">
        <button onClick={onApplyFilters} data-testid="apply-filters">Apply</button>
        <button onClick={onClearFilters} data-testid="clear-filters">Clear</button>
      </div>
    );
  };
});

jest.mock('../ExportButton', () => {
  return function MockExportButton({ data }: any) {
    return (
      <button data-testid="mock-export-button">
        Export ({data.length} items)
      </button>
    );
  };
});

describe('ThreatTable', () => {
  const mockThreats = [
    {
      id: '1',
      ip_address: '192.168.1.100',
      threat_type: 'Malware',
      severity: 'critical',
      threat_score: 95,
      created_at: '2024-01-01T10:00:00Z',
      country_code: 'US',
    },
    {
      id: '2',
      ip_address: '10.0.0.50',
      threat_type: 'DDoS',
      severity: 'high',
      threat_score: 78,
      created_at: '2024-01-01T08:00:00Z',
      country_code: null,
    },
    {
      id: '3',
      ip_address: '172.16.0.25',
      threat_type: 'Suspicious Activity',
      severity: 'medium',
      threat_score: 45,
      created_at: '2024-01-01T06:00:00Z',
    },
  ];

  const mockUseFilters = {
    filterState: {
      rootGroup: { conditions: [], groups: [] },
      availableFields: [],
      presets: [],
      isAdvanced: false,
    },
    filteredData: mockThreats,
    updateFilterState: jest.fn(),
    applyFilters: jest.fn(),
    clearFilters: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
    (require('@/hooks/useFilters').useFilters as jest.Mock).mockReturnValue(mockUseFilters);
  });

  it('renders the threat table header correctly', () => {
    render(<ThreatTable threats={mockThreats} />);

    expect(screen.getByText('Recent Threats')).toBeInTheDocument();
    expect(document.querySelector('.lucide-shield')).toBeInTheDocument(); // Shield icon
    expect(screen.getByTestId('mock-export-button')).toBeInTheDocument();
  });

  it('renders table headers correctly', () => {
    render(<ThreatTable threats={mockThreats} />);

    expect(screen.getByText('IP Address')).toBeInTheDocument();
    expect(screen.getByText('Threat Type')).toBeInTheDocument();
    expect(screen.getByText('Severity')).toBeInTheDocument();
    expect(screen.getByText('Score')).toBeInTheDocument();
    expect(screen.getByText('Time')).toBeInTheDocument();
  });

  it('renders all threats in the table', () => {
    render(<ThreatTable threats={mockThreats} />);

    expect(screen.getByText('192.168.1.100')).toBeInTheDocument();
    expect(screen.getByText('10.0.0.50')).toBeInTheDocument();
    expect(screen.getByText('172.16.0.25')).toBeInTheDocument();

    expect(screen.getByText('Malware')).toBeInTheDocument();
    expect(screen.getByText('DDoS')).toBeInTheDocument();
    expect(screen.getByText('Suspicious Activity')).toBeInTheDocument();

    expect(screen.getByText('95')).toBeInTheDocument();
    expect(screen.getByText('78')).toBeInTheDocument();
    expect(screen.getByText('45')).toBeInTheDocument();
  });

  it('displays severity badges with correct styling', () => {
    render(<ThreatTable threats={mockThreats} />);

    const { getThreatColorClasses } = require('@/utils');

    expect(getThreatColorClasses).toHaveBeenCalledWith('critical');
    expect(getThreatColorClasses).toHaveBeenCalledWith('high');
    expect(getThreatColorClasses).toHaveBeenCalledWith('medium');

    expect(screen.getByText('critical')).toBeInTheDocument();
    expect(screen.getByText('high')).toBeInTheDocument();
    expect(screen.getByText('medium')).toBeInTheDocument();
  });

  it('shows country flags for threats with country codes', () => {
    render(<ThreatTable threats={mockThreats} />);

    // Should have one MapPin icon for the threat with country_code
    const mapPins = document.querySelectorAll('.lucide-map-pin');
    expect(mapPins).toHaveLength(1);
  });

  it('displays timestamps for all threats', () => {
    render(<ThreatTable threats={mockThreats} />);

    const timestamps = screen.getAllByText('2 hours ago');
    expect(timestamps).toHaveLength(3);
  });

  it('shows filter button when showFilters is true (default)', () => {
    render(<ThreatTable threats={mockThreats} />);

    expect(screen.getByText('Filters')).toBeInTheDocument();
  });

  it('hides filter button when showFilters is false', () => {
    render(<ThreatTable threats={mockThreats} showFilters={false} />);

    expect(screen.queryByText('Filters')).not.toBeInTheDocument();
  });

  it('toggles filter builder visibility when filter button is clicked', () => {
    render(<ThreatTable threats={mockThreats} />);

    expect(screen.queryByTestId('mock-filter-builder')).not.toBeInTheDocument();

    fireEvent.click(screen.getByText('Filters'));
    expect(screen.getByTestId('mock-filter-builder')).toBeInTheDocument();

    fireEvent.click(screen.getByText('Filters'));
    expect(screen.queryByTestId('mock-filter-builder')).not.toBeInTheDocument();
  });

  it('shows filter count when data is filtered', () => {
    const filteredMock = {
      ...mockUseFilters,
      filteredData: mockThreats.slice(0, 2), // Only 2 of 3 threats
    };
    (require('@/hooks/useFilters').useFilters as jest.Mock).mockReturnValue(filteredMock);

    render(<ThreatTable threats={mockThreats} />);

    expect(screen.getByText('2 of 3')).toBeInTheDocument();
  });

  it('does not show filter count when all data is shown', () => {
    render(<ThreatTable threats={mockThreats} />);

    expect(screen.queryByText(/\d+ of \d+/)).not.toBeInTheDocument();
  });

  it('highlights filter button when filters are active', () => {
    const activeFilterMock = {
      ...mockUseFilters,
      filterState: {
        ...mockUseFilters.filterState,
        rootGroup: { conditions: [{ field: 'severity', operator: 'equals', value: 'high' }], groups: [] },
      },
    };
    (require('@/hooks/useFilters').useFilters as jest.Mock).mockReturnValue(activeFilterMock);

    render(<ThreatTable threats={mockThreats} />);

    const filterButton = screen.getByText('Filters').closest('button');
    expect(filterButton).toHaveClass('bg-blue-600', 'text-white');
  });

  it('highlights filter button when filter builder is open', () => {
    render(<ThreatTable threats={mockThreats} />);

    fireEvent.click(screen.getByText('Filters'));

    const filterButton = screen.getByText('Filters').closest('button');
    expect(filterButton).toHaveClass('bg-blue-600', 'text-white');
  });

  it('passes correct data to ExportButton', () => {
    render(<ThreatTable threats={mockThreats} />);

    const exportButton = screen.getByTestId('mock-export-button');
    expect(exportButton).toHaveTextContent('Export (3 items)');
  });

  it('handles empty threats array', () => {
    const emptyMock = {
      ...mockUseFilters,
      filteredData: [],
    };
    (require('@/hooks/useFilters').useFilters as jest.Mock).mockReturnValue(emptyMock);

    render(<ThreatTable threats={[]} />);

    expect(screen.getByText('Recent Threats')).toBeInTheDocument();
    expect(screen.queryByText('192.168.1.100')).not.toBeInTheDocument();
  });

  it('applies hover effects to table rows', () => {
    render(<ThreatTable threats={mockThreats.slice(0, 1)} />);

    const tableRow = screen.getByText('192.168.1.100').closest('tr');
    expect(tableRow).toHaveClass('hover:bg-slate-800/30', 'transition-colors');
  });

  it('applies correct table styling', () => {
    render(<ThreatTable threats={mockThreats} />);

    const table = document.querySelector('table');
    expect(table).toHaveClass('w-full');

    const thead = document.querySelector('thead');
    expect(thead).toBeInTheDocument();

    const tbody = document.querySelector('tbody');
    expect(tbody).toHaveClass('divide-y', 'divide-slate-700/30');
  });

  it('passes accessibility checks', async () => {
    const { container } = render(<ThreatTable threats={mockThreats} />);

    await testA11y(<div>{container.innerHTML}</div>);
  });

  it('handles filter interactions correctly', () => {
    render(<ThreatTable threats={mockThreats} />);

    fireEvent.click(screen.getByText('Filters'));
    expect(screen.getByTestId('mock-filter-builder')).toBeInTheDocument();

    fireEvent.click(screen.getByTestId('apply-filters'));
    expect(mockUseFilters.applyFilters).toHaveBeenCalled();

    fireEvent.click(screen.getByTestId('clear-filters'));
    expect(mockUseFilters.clearFilters).toHaveBeenCalled();
  });

  it('renders threats in correct table structure', () => {
    render(<ThreatTable threats={mockThreats} />);

    // Check table structure
    const table = document.querySelector('table');
    expect(table).toBeInTheDocument();

    const headers = document.querySelectorAll('th');
    expect(headers).toHaveLength(5); // 5 columns

    const rows = document.querySelectorAll('tbody tr');
    expect(rows).toHaveLength(3); // 3 threats

    const cells = document.querySelectorAll('tbody td');
    expect(cells).toHaveLength(15); // 5 cells per row * 3 rows
  });

  it('displays IP addresses with monospace font', () => {
    render(<ThreatTable threats={mockThreats.slice(0, 1)} />);

    const ipElement = screen.getByText('192.168.1.100');
    expect(ipElement).toHaveClass('font-mono', 'text-slate-300');
  });

  it('handles threats without country codes', () => {
    render(<ThreatTable threats={mockThreats.slice(1, 2)} />); // Threat without country_code

    const ipElement = screen.getByText('10.0.0.50');
    const mapPins = ipElement.parentElement?.querySelectorAll('.lucide-map-pin');
    expect(mapPins?.length).toBe(0);
  });

  it('passes correct props to useFilters hook', () => {
    const { useFilters } = require('@/hooks/useFilters');

    render(<ThreatTable threats={mockThreats} />);

    expect(useFilters).toHaveBeenCalledWith(
      mockThreats,
      expect.any(Array), // THREAT_FILTER_FIELDS
      expect.any(Array)  // defaultPresets
    );
  });

  it('creates correct default filter presets', () => {
    const { useFilters } = require('@/hooks/useFilters');

    render(<ThreatTable threats={mockThreats} />);

    const callArgs = useFilters.mock.calls[0];
    const presets = callArgs[2]; // Third argument is defaultPresets

    expect(presets).toHaveLength(3);
    expect(presets[0].name).toBe('High Severity Threats');
    expect(presets[1].name).toBe('Recent Threats');
    expect(presets[2].name).toBe('Critical & High');
  });
});
