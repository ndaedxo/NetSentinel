import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect, jest, beforeEach } from '@jest/globals';

import AlertFeed from '../AlertFeed';
import { testA11y } from '../../test/test-utils';
import { getThreatBorderColor } from '@/utils';

// Mock date-fns
jest.mock('date-fns', () => ({
  formatDistanceToNow: jest.fn(() => '2 hours ago'),
}));

// Mock utils
jest.mock('@/utils', () => ({
  getThreatBorderColor: jest.fn((severity) => {
    switch (severity) {
      case 'critical':
        return 'border-red-500';
      case 'high':
        return 'border-orange-500';
      case 'medium':
        return 'border-yellow-500';
      default:
        return 'border-blue-500';
    }
  }),
}));

describe('AlertFeed', () => {
  const mockAlerts = [
    {
      id: '1',
      title: 'Critical Security Alert',
      description: 'Unauthorized access detected',
      severity: 'critical',
      created_at: '2024-01-01T10:00:00Z',
    },
    {
      id: '2',
      title: 'Warning Alert',
      description: 'Suspicious activity detected',
      severity: 'medium',
      created_at: '2024-01-01T08:00:00Z',
    },
    {
      id: '3',
      title: 'Info Alert',
      severity: 'low',
      created_at: '2024-01-01T06:00:00Z',
    },
  ];

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders the alert feed header correctly', () => {
    render(<AlertFeed alerts={mockAlerts} />);

    expect(screen.getByText('Active Alerts')).toBeInTheDocument();
    expect(screen.getByText('3 Active')).toBeInTheDocument();
    expect(document.querySelector('.lucide-bell')).toBeInTheDocument(); // Bell icon
  });

  it('renders all alerts in the feed', () => {
    render(<AlertFeed alerts={mockAlerts} />);

    expect(screen.getByText('Critical Security Alert')).toBeInTheDocument();
    expect(screen.getByText('Warning Alert')).toBeInTheDocument();
    expect(screen.getByText('Info Alert')).toBeInTheDocument();
  });

  it('displays alert descriptions when available', () => {
    render(<AlertFeed alerts={mockAlerts} />);

    expect(screen.getByText('Unauthorized access detected')).toBeInTheDocument();
    expect(screen.getByText('Suspicious activity detected')).toBeInTheDocument();
  });

  it('renders timestamps for all alerts', () => {
    render(<AlertFeed alerts={mockAlerts} />);

    const timestamps = screen.getAllByText('2 hours ago');
    expect(timestamps).toHaveLength(3);
  });

  it('applies correct border colors based on severity', () => {
    render(<AlertFeed alerts={mockAlerts} />);

    expect(getThreatBorderColor).toHaveBeenCalledWith('critical');
    expect(getThreatBorderColor).toHaveBeenCalledWith('medium');
    expect(getThreatBorderColor).toHaveBeenCalledWith('low');
  });

  it('displays correct icons for different severity levels', () => {
    render(<AlertFeed alerts={mockAlerts} />);

    // Check that the header has a bell icon
    const headerBell = document.querySelector('.lucide-bell');
    expect(headerBell).toBeInTheDocument();

    // Check that alert items have the correct severity-based icons
    // Critical alert should have AlertTriangle (but looking at the component, only critical/high get AlertTriangle)
    // My test data has 'critical', 'medium', 'low' - so only critical should have AlertTriangle
    const alertTriangles = document.querySelectorAll('.text-red-400');
    expect(alertTriangles.length).toBeGreaterThan(0); // Critical alert should have red AlertTriangle

    // Medium/low alerts should have yellow Bell icons
    const alertBells = document.querySelectorAll('.text-yellow-400');
    expect(alertBells.length).toBeGreaterThan(0); // Medium/low alerts should have yellow bells
  });

  it('handles empty alerts array', () => {
    render(<AlertFeed alerts={[]} />);

    expect(screen.getByText('Active Alerts')).toBeInTheDocument();
    expect(screen.getByText('0 Active')).toBeInTheDocument();
    expect(screen.queryByText('Critical Security Alert')).not.toBeInTheDocument();
  });

  it('applies hover effects to alert items', () => {
    render(<AlertFeed alerts={mockAlerts.slice(0, 1)} />);

    const alertItem = screen.getByText('Critical Security Alert').closest('.transition-all');
    expect(alertItem).toHaveClass('hover:scale-[1.01]');
  });

  it('truncates long alert titles', () => {
    const longTitleAlert = [{
      id: '1',
      title: 'This is a very long alert title that should be truncated when displayed',
      severity: 'high',
      created_at: '2024-01-01T10:00:00Z',
    }];

    render(<AlertFeed alerts={longTitleAlert} />);

    const titleElement = screen.getByText('This is a very long alert title that should be truncated when displayed');
    expect(titleElement).toHaveClass('truncate');
  });

  it('renders alert descriptions with line clamping', () => {
    const longDescriptionAlert = [{
      id: '1',
      title: 'Test Alert',
      description: 'This is a very long description that should be clamped to two lines when displayed in the alert feed component',
      severity: 'medium',
      created_at: '2024-01-01T10:00:00Z',
    }];

    render(<AlertFeed alerts={longDescriptionAlert} />);

    const descriptionElement = screen.getByText('This is a very long description that should be clamped to two lines when displayed in the alert feed component');
    expect(descriptionElement).toHaveClass('line-clamp-2');
  });

  it('handles alerts without descriptions', () => {
    const alertWithoutDescription = [{
      id: '1',
      title: 'Alert Without Description',
      severity: 'low',
      created_at: '2024-01-01T10:00:00Z',
    }];

    render(<AlertFeed alerts={alertWithoutDescription} />);

    expect(screen.getByText('Alert Without Description')).toBeInTheDocument();

    // Should not have a description paragraph
    const descriptionElements = document.querySelectorAll('p.text-xs.text-slate-400');
    expect(descriptionElements).toHaveLength(0);
  });

  it('applies correct styling classes', () => {
    render(<AlertFeed alerts={mockAlerts.slice(0, 1)} />);

    const card = screen.getByText('Active Alerts').closest('.card-dark');
    expect(card).toBeInTheDocument();
    expect(card).toHaveClass('p-6');

    const alertContainer = screen.getByText('Critical Security Alert').closest('.space-y-3');
    expect(alertContainer).toBeInTheDocument();
    expect(alertContainer).toHaveClass('max-h-96', 'overflow-y-auto');
  });

  it('passes accessibility checks', async () => {
    const { container } = render(<AlertFeed alerts={mockAlerts} />);

    await testA11y(<div>{container.innerHTML}</div>);
  });

  it('handles malformed alert data gracefully', () => {
    const malformedAlerts = [
      { id: '1', title: 'Test', severity: 'high' }, // missing created_at
      { id: '2', title: '', severity: 'medium', created_at: '2024-01-01T10:00:00Z' }, // empty title
    ];

    // Should not crash
    expect(() => render(<AlertFeed alerts={malformedAlerts} />)).not.toThrow();
    expect(screen.getByText('Active Alerts')).toBeInTheDocument();
  });

  it('renders alerts in correct order', () => {
    render(<AlertFeed alerts={mockAlerts} />);

    const alerts = screen.getAllByRole('heading', { level: 3 });
    expect(alerts).toHaveLength(3);
    expect(alerts[0]).toHaveTextContent('Critical Security Alert');
    expect(alerts[1]).toHaveTextContent('Warning Alert');
    expect(alerts[2]).toHaveTextContent('Info Alert');
  });
});
