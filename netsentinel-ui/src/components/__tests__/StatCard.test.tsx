import React from 'react';
import { render, screen } from '@testing-library/react';
import { Activity } from 'lucide-react';
import StatCard from '../StatCard';

describe('StatCard', () => {
  const defaultProps = {
    title: 'Total Events',
    value: 1234,
    icon: Activity,
  };

  it('renders the title correctly', () => {
    render(<StatCard {...defaultProps} />);
    expect(screen.getByText('Total Events')).toBeInTheDocument();
  });

  it('renders the formatted value correctly', () => {
    render(<StatCard {...defaultProps} />);
    expect(screen.getByText('1,234')).toBeInTheDocument();
  });

  it('renders the icon', () => {
    render(<StatCard {...defaultProps} />);
    const icon = document.querySelector('svg');
    expect(icon).toBeInTheDocument();
  });

  it('renders positive trend indicator', () => {
    const propsWithTrend = {
      ...defaultProps,
      trend: { value: '12%', isPositive: true }
    };
    render(<StatCard {...propsWithTrend} />);
    expect(screen.getByText('↑ 12%')).toBeInTheDocument();
    expect(screen.getByText('↑ 12%')).toHaveClass('text-green-400');
  });

  it('renders negative trend indicator', () => {
    const propsWithTrend = {
      ...defaultProps,
      trend: { value: '5%', isPositive: false }
    };
    render(<StatCard {...propsWithTrend} />);
    expect(screen.getByText('↓ 5%')).toBeInTheDocument();
    expect(screen.getByText('↓ 5%')).toHaveClass('text-red-400');
  });

  it('applies blue color theme by default', () => {
    render(<StatCard {...defaultProps} />);
    const card = screen.getByText('Total Events').closest('.card-dark');
    expect(card).toHaveClass('from-blue-500/20');
    expect(card).toHaveClass('border-blue-500/30');
  });

  it('applies red color theme', () => {
    render(<StatCard {...defaultProps} color="red" />);
    const card = screen.getByText('Total Events').closest('.card-dark');
    expect(card).toHaveClass('from-red-500/20');
    expect(card).toHaveClass('border-red-500/30');
  });

  it('formats number values correctly', () => {
    render(<StatCard {...defaultProps} value={5678} />);
    expect(screen.getByText('5,678')).toBeInTheDocument();
  });

  it('handles zero values', () => {
    render(<StatCard {...defaultProps} value={0} />);
    expect(screen.getByText('0')).toBeInTheDocument();
  });
});
