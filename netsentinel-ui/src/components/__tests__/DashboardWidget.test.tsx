import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect, jest } from '@jest/globals';

// Mock hooks only - let child components fail gracefully
jest.mock('@/hooks', () => ({
  useDashboard: jest.fn(() => ({
    removeWidget: jest.fn(),
    updateWidget: jest.fn()
  })),
  useThreatData: jest.fn(() => []),
  useAlertData: jest.fn(() => []),
  useSystemHealthData: jest.fn(() => ({ services: [] }))
}));

// Mock child components to avoid dependency issues
jest.doMock('../StatCard', () => ({
  default: () => React.createElement('div', { 'data-testid': 'stat-card' }, 'Stat Card')
}));

jest.doMock('../ThreatTimeline', () => ({
  default: () => React.createElement('div', { 'data-testid': 'threat-timeline' }, 'Threat Timeline')
}));

jest.doMock('../AlertFeed', () => ({
  default: () => React.createElement('div', { 'data-testid': 'alert-feed' }, 'Alert Feed')
}));

jest.doMock('../SystemHealth', () => ({
  default: () => React.createElement('div', { 'data-testid': 'system-health' }, 'System Health')
}));

jest.doMock('../ThreatTable', () => ({
  default: () => React.createElement('div', { 'data-testid': 'threat-table' }, 'Threat Table')
}));

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
});
