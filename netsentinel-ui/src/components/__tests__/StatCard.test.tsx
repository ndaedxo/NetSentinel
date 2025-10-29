import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from '@jest/globals';
import StatCard from '../StatCard';
import { Activity } from 'lucide-react';

describe('StatCard', () => {
  const defaultProps = {
    title: 'Test Metric',
    value: '1,234',
    icon: Activity,
  };

  it('renders title and value correctly', () => {
    render(<StatCard {...defaultProps} />);

    expect(screen.getByText('Test Metric')).toBeInTheDocument();
    expect(screen.getByText('1,234')).toBeInTheDocument();
  });

  it('renders icon correctly', () => {
    render(<StatCard {...defaultProps} />);

    const icon = document.querySelector('svg');
    expect(icon).toBeInTheDocument();
    expect(icon).toHaveClass('w-6', 'h-6');
  });

  it('formats number values with commas', () => {
    render(<StatCard {...defaultProps} value={1234} />);

    expect(screen.getByText('1,234')).toBeInTheDocument();
  });

  it('renders positive trend correctly', () => {
    const propsWithTrend = {
      ...defaultProps,
      trend: { value: '+5.2%', isPositive: true }
    };

    render(<StatCard {...propsWithTrend} />);

    expect(screen.getByText('↑ +5.2%')).toBeInTheDocument();
    expect(screen.getByText('↑ +5.2%')).toHaveClass('text-green-400');
  });

  it('renders negative trend correctly', () => {
    const propsWithTrend = {
      ...defaultProps,
      trend: { value: '-2.1%', isPositive: false }
    };

    render(<StatCard {...propsWithTrend} />);

    expect(screen.getByText('↓ -2.1%')).toBeInTheDocument();
    expect(screen.getByText('↓ -2.1%')).toHaveClass('text-red-400');
  });

  it('applies blue color classes by default', () => {
    render(<StatCard {...defaultProps} />);

    const card = screen.getByText('Test Metric').closest('.card-dark');
    expect(card).toHaveClass('from-blue-500/20', 'to-blue-600/10', 'border-blue-500/30', 'glow-blue');
  });

  it('applies red color classes when specified', () => {
    render(<StatCard {...defaultProps} color="red" />);

    const card = screen.getByText('Test Metric').closest('.card-dark');
    expect(card).toHaveClass('from-red-500/20', 'to-red-600/10', 'border-red-500/30', 'glow-red');
  });

  it('applies green color classes when specified', () => {
    render(<StatCard {...defaultProps} color="green" />);

    const card = screen.getByText('Test Metric').closest('.card-dark');
    expect(card).toHaveClass('from-green-500/20', 'to-green-600/10', 'border-green-500/30', 'glow-green');
  });

  it('applies yellow color classes when specified', () => {
    render(<StatCard {...defaultProps} color="yellow" />);

    const card = screen.getByText('Test Metric').closest('.card-dark');
    expect(card).toHaveClass('from-yellow-500/20', 'to-yellow-600/10', 'border-yellow-500/30', 'glow-yellow');
  });

  it('applies correct icon color for blue theme', () => {
    render(<StatCard {...defaultProps} color="blue" />);

    const iconContainer = document.querySelector('.bg-slate-900\\/50');
    expect(iconContainer).toHaveClass('text-blue-400');
  });

  it('applies correct icon color for red theme', () => {
    render(<StatCard {...defaultProps} color="red" />);

    const iconContainer = document.querySelector('.bg-slate-900\\/50');
    expect(iconContainer).toHaveClass('text-red-400');
  });

  it('applies correct icon color for green theme', () => {
    render(<StatCard {...defaultProps} color="green" />);

    const iconContainer = document.querySelector('.bg-slate-900\\/50');
    expect(iconContainer).toHaveClass('text-green-400');
  });

  it('applies correct icon color for yellow theme', () => {
    render(<StatCard {...defaultProps} color="yellow" />);

    const iconContainer = document.querySelector('.bg-slate-900\\/50');
    expect(iconContainer).toHaveClass('text-yellow-400');
  });

  it('does not render trend when not provided', () => {
    render(<StatCard {...defaultProps} />);

    expect(screen.queryByText(/↑|↓/)).not.toBeInTheDocument();
  });

  it('has correct card structure', () => {
    render(<StatCard {...defaultProps} />);

    const card = screen.getByText('Test Metric').closest('.card-dark');
    expect(card).toBeInTheDocument();
    expect(card).toHaveClass('p-6', 'bg-gradient-to-br', 'border', 'transition-all', 'duration-300', 'hover:scale-[1.02]');
  });
});