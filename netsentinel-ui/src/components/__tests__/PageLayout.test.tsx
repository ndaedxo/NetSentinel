import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect, jest } from '@jest/globals';

import PageLayout from '../PageLayout';
import { testA11y } from '../../test/test-utils';

// Mock the child components
jest.mock('../Header', () => {
  return function MockHeader({ onToggleSidebar, isSidebarCollapsed }: any) {
    return (
      <header data-testid="mock-header">
        <button
          data-testid="toggle-sidebar-btn"
          onClick={onToggleSidebar}
          aria-label="Toggle sidebar"
        >
          Toggle ({isSidebarCollapsed ? 'collapsed' : 'expanded'})
        </button>
      </header>
    );
  };
});

jest.mock('../SidebarNav', () => {
  return function MockSidebarNav({ collapsed }: any) {
    return (
      <aside data-testid="mock-sidebar" data-collapsed={collapsed}>
        <nav>Mock Sidebar ({collapsed ? 'collapsed' : 'expanded'})</nav>
      </aside>
    );
  };
});

describe('PageLayout', () => {
  it('renders children in main element', () => {
    render(
      <PageLayout>
        <h1>Test Content</h1>
        <p>Some description</p>
      </PageLayout>
    );

    const main = screen.getByRole('main');
    expect(main).toBeInTheDocument();
    expect(screen.getByText('Test Content')).toBeInTheDocument();
    expect(screen.getByText('Some description')).toBeInTheDocument();
  });

  it('applies default maxWidth class', () => {
    render(
      <PageLayout>
        <div>Content</div>
      </PageLayout>
    );

    const main = screen.getByRole('main');
    expect(main).toHaveClass('max-w-7xl');
  });

  it('applies custom maxWidth when provided', () => {
    render(
      <PageLayout maxWidth="max-w-4xl">
        <div>Content</div>
      </PageLayout>
    );

    const main = screen.getByRole('main');
    expect(main).toHaveClass('max-w-4xl');
  });

  it('applies default classes to main element', () => {
    render(
      <PageLayout>
        <div>Content</div>
      </PageLayout>
    );

    const main = screen.getByRole('main');
    expect(main).toHaveClass('max-w-7xl', 'mx-auto', 'px-4', 'py-6', 'md:px-6', 'md:py-8');
  });

  it('applies custom className to main element', () => {
    render(
      <PageLayout className="custom-class">
        <div>Content</div>
      </PageLayout>
    );

    const main = screen.getByRole('main');
    expect(main).toHaveClass('custom-class');
  });

  it('applies background gradient to container', () => {
    render(
      <PageLayout>
        <div>Content</div>
      </PageLayout>
    );

    const container = screen.getByTestId('mock-sidebar').parentElement;
    expect(container).toHaveClass(
      'bg-gradient-to-br',
      'from-slate-900',
      'via-slate-800',
      'to-slate-900'
    );
  });

  it('maintains proper layout structure', () => {
    render(
      <PageLayout>
        <section>
          <h1>Main Content</h1>
        </section>
      </PageLayout>
    );

    // Check that we have the mock sidebar and header
    expect(screen.getByTestId('mock-sidebar')).toBeInTheDocument();
    expect(screen.getByTestId('mock-header')).toBeInTheDocument();

    // Check that main contains the content
    const main = screen.getByRole('main');
    expect(main.querySelector('section')).toBeInTheDocument();
    expect(screen.getByText('Main Content')).toBeInTheDocument();
  });

  it('passes accessibility checks', async () => {
    const { container } = render(
      <PageLayout title="Test Page" subtitle="Test subtitle">
        <h1>Main Content</h1>
        <p>Some description text</p>
      </PageLayout>
    );

    await testA11y(<div>{container.innerHTML}</div>);
  });
});
