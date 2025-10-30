import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, jest, beforeEach, afterEach } from '@jest/globals';
import { mockUtils } from '@/test/__mocks__/mock-config';

// Configure mocks for testing
beforeEach(() => {
  mockUtils.setup({
    realisticDelays: false, // Disable delays for faster tests
    randomErrors: false,    // Disable random errors by default
    seed: 42               // Consistent seed for reproducible tests
  });
});

afterEach(() => {
  mockUtils.reset();
});

// Mock hooks with dynamic data
jest.mock('@/hooks', () => ({
  useDashboard: jest.fn(() => ({
    removeWidget: jest.fn(),
    updateWidget: jest.fn()
  })),
  useThreatData: jest.fn(() => []),
  useAlertData: jest.fn(() => []),
  useSystemHealthData: jest.fn(() => ({ services: [] }))
}));

// Mock child components with dynamic behavior
/* eslint-disable @typescript-eslint/no-require-imports */
jest.mock('../StatCard', () => {
  const React = require('react');
  return ({ title, value }: { title: string; value: unknown }) => React.createElement('div', {
    'data-testid': 'stat-card',
    'data-title': title,
    'data-value': value
  }, `${title}: ${value}`);
});

jest.mock('../ThreatTimeline', () => {
  const React = require('react');
  return ({ data }: { data?: unknown[] }) => React.createElement('div', {
    'data-testid': 'threat-timeline',
    'data-points': data?.length || 0
  }, `Threat Timeline: ${data?.length || 0} points`);
});

jest.mock('../AlertFeed', () => {
  const React = require('react');
  return ({ alerts }: { alerts?: unknown[] }) => React.createElement('div', {
    'data-testid': 'alert-feed',
    'data-alerts': alerts?.length || 0
  }, `Alert Feed: ${alerts?.length || 0} alerts`);
});

jest.mock('../SystemHealth', () => {
  const React = require('react');
  return ({ services }: { services?: unknown[] }) => React.createElement('div', {
    'data-testid': 'system-health',
    'data-services': services?.length || 0
  }, `System Health: ${services?.length || 0} services`);
});

jest.mock('../ThreatTable', () => {
  const React = require('react');
  return ({ threats }: { threats?: unknown[] }) => React.createElement('div', {
    'data-testid': 'threat-table',
    'data-threats': threats?.length || 0
  }, `Threat Table: ${threats?.length || 0} threats`);
});
/* eslint-enable @typescript-eslint/no-require-imports */

// Import after mocks are set up
import DashboardWidget from '../DashboardWidget';
import { Widget } from '@/types/dashboard';

describe('DashboardWidget', () => {
  const mockWidget: Widget = {
    id: 'test-widget',
    type: 'stat-card',
    title: 'Test Widget',
    position: { x: 0, y: 0 },
    size: { width: 1, height: 1 },
    config: {}
  };

  it('renders widget container with title for unknown widget type', () => {
    const unknownWidget = { ...mockWidget, type: 'unknown' as unknown as Widget['type'] };

    render(<DashboardWidget widget={unknownWidget} />);

    expect(screen.getByText('Test Widget')).toBeInTheDocument();
    expect(screen.getByText('Unknown widget type')).toBeInTheDocument();
  });

  it('handles different widget configurations', () => {
    const configuredWidget = {
      ...mockWidget,
      config: { compact: true, color: 'blue' }
    };

    // This should not throw an error
    expect(() => {
      render(<DashboardWidget widget={configuredWidget} />);
    }).not.toThrow();
  });

  it('renders with isEditing prop', () => {
    const unknownWidget = { ...mockWidget, type: 'unknown' as unknown as Widget['type'] };

    // This should not throw an error
    expect(() => {
      render(<DashboardWidget widget={unknownWidget} isEditing={true} />);
    }).not.toThrow();

    expect(screen.getByText('Test Widget')).toBeInTheDocument();
  });

  describe('Dynamic Data Simulation', () => {
    it('handles dynamic widget configurations', async () => {
      const dynamicWidget = {
        ...mockWidget,
        title: 'Dynamic Threats',
        config: {
          value: Math.floor(Math.random() * 100),
          color: 'red',
          compact: true
        }
      };

      render(<DashboardWidget widget={dynamicWidget} />);

      await waitFor(() => {
        const statCard = screen.getByTestId('stat-card');
        expect(statCard).toBeInTheDocument();
        expect(statCard).toHaveAttribute('data-title', 'Dynamic Threats');
      });
    });

    it('simulates real-time data updates', async () => {
      const timelineWidget: Widget = {
        id: 'timeline-widget',
        type: 'threat-timeline',
        title: 'Threat Timeline',
        position: { x: 0, y: 0 },
        size: { width: 2, height: 1 },
        config: {}
      };

      render(<DashboardWidget widget={timelineWidget} />);

      await waitFor(() => {
        const timeline = screen.getByTestId('threat-timeline');
        expect(timeline).toBeInTheDocument();
        expect(timeline).toHaveAttribute('data-points');
      });
    });

    it('handles error scenarios gracefully', async () => {
      // Force an error for the next operation
      mockUtils.simulateErrors(1, 'network');

      const tableWidget: Widget = {
        id: 'table-widget',
        type: 'threat-table',
        title: 'Threat Table',
        position: { x: 0, y: 0 },
        size: { width: 2, height: 2 },
        config: {}
      };

      // Component should handle errors gracefully
      expect(() => {
        render(<DashboardWidget widget={tableWidget} />);
      }).not.toThrow();
    });

    it('adapts to different data volumes', async () => {
      const alertWidget: Widget = {
        id: 'alert-widget',
        type: 'alert-feed',
        title: 'Alert Feed',
        position: { x: 0, y: 0 },
        size: { width: 1, height: 2 },
        config: {}
      };

      render(<DashboardWidget widget={alertWidget} />);

      await waitFor(() => {
        const alertFeed = screen.getByTestId('alert-feed');
        expect(alertFeed).toBeInTheDocument();
        expect(alertFeed).toHaveAttribute('data-alerts');
      });
    });

    it('responds to configuration changes', async () => {
      const configurableWidget = {
        ...mockWidget,
        config: {
          showPercentage: true,
          threshold: 75,
          autoRefresh: false
        }
      };

      render(<DashboardWidget widget={configurableWidget} />);

      await waitFor(() => {
        const statCard = screen.getByTestId('stat-card');
        expect(statCard).toBeInTheDocument();
      });
    });
  });

  describe('Error Handling', () => {
    it('handles network errors gracefully', async () => {
      mockUtils.simulateErrors(1, 'network');

      const widget = { ...mockWidget };

      expect(() => {
        render(<DashboardWidget widget={widget} />);
      }).not.toThrow();
    });

    it('handles server errors gracefully', async () => {
      mockUtils.simulateErrors(1, 'server');

      const widget = { ...mockWidget };

      expect(() => {
        render(<DashboardWidget widget={widget} />);
      }).not.toThrow();
    });

    it('continues working after errors', async () => {
      // Force multiple errors
      mockUtils.simulateErrors(3, 'network');

      const widget = { ...mockWidget };

      // Should still render without crashing
      render(<DashboardWidget widget={widget} />);

      expect(screen.getByText('Test Widget')).toBeInTheDocument();
    });

    it('handles widget titles correctly', () => {
      const widget = { ...mockWidget, title: 'Custom Title' };
      render(<DashboardWidget widget={widget} />);

      expect(screen.getByText('Custom Title')).toBeInTheDocument();
    });
  });
});
