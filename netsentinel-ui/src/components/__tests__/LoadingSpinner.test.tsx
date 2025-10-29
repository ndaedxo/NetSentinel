import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from '@jest/globals';
import LoadingSpinner from '../LoadingSpinner';

describe('LoadingSpinner', () => {
  it('renders with default message', () => {
    render(<LoadingSpinner />);

    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });

  it('renders with custom message', () => {
    render(<LoadingSpinner message="Please wait..." />);

    expect(screen.getByText('Please wait...')).toBeInTheDocument();
  });

  it('renders with medium size by default', () => {
    render(<LoadingSpinner />);

    const spinner = document.querySelector('.animate-spin');
    expect(spinner).toHaveClass('w-12', 'h-12');
  });

  it('renders with small size when specified', () => {
    render(<LoadingSpinner size="sm" />);

    const spinner = document.querySelector('.animate-spin');
    expect(spinner).toHaveClass('w-6', 'h-6');
  });

  it('renders with large size when specified', () => {
    render(<LoadingSpinner size="lg" />);

    const spinner = document.querySelector('.animate-spin');
    expect(spinner).toHaveClass('w-16', 'h-16');
  });

  it('applies custom className', () => {
    render(<LoadingSpinner className="custom-class" />);

    const container = document.querySelector('.min-h-screen');
    expect(container).toHaveClass('custom-class');
  });

  it('has correct structure and classes', () => {
    render(<LoadingSpinner />);

    const container = document.querySelector('.min-h-screen');
    expect(container).toHaveClass(
      'bg-gradient-to-br',
      'from-slate-900',
      'via-slate-800',
      'to-slate-900',
      'flex',
      'items-center',
      'justify-center'
    );

    const innerContainer = document.querySelector('.flex.flex-col');
    expect(innerContainer).toHaveClass('items-center', 'space-y-4');

    const spinner = document.querySelector('.animate-spin');
    expect(spinner).toHaveClass(
      'border-4',
      'border-blue-500',
      'border-t-transparent',
      'rounded-full'
    );

    const message = screen.getByText('Loading...');
    expect(message).toHaveClass('text-slate-400');
  });

  it('renders spinner with correct border styling', () => {
    render(<LoadingSpinner />);

    const spinner = document.querySelector('.animate-spin');
    expect(spinner).toHaveClass('border-blue-500', 'border-t-transparent');
  });

  it('centers content properly', () => {
    render(<LoadingSpinner />);

    const container = document.querySelector('.min-h-screen');
    expect(container).toHaveClass('flex', 'items-center', 'justify-center');

    const innerContainer = document.querySelector('.flex.flex-col');
    expect(innerContainer).toHaveClass('items-center');
  });
});
