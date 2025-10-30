import React from 'react';
import { render } from '@testing-library/react';
import { describe, it, expect } from '@jest/globals';

import PageLayout from '../PageLayout';

describe('PageLayout', () => {
  it.skip('renders children in main element', () => {
    render(
      <PageLayout>
        <h1>Test Content</h1>
        <p>Some description</p>
      </PageLayout>
    );

    const main = document.querySelector('main');
    expect(main).toBeInTheDocument();
    expect(main).toHaveTextContent('Test Content');
    expect(main).toHaveTextContent('Some description');
  });

  it.skip('applies default maxWidth class', () => {
    render(
      <PageLayout>
        <div>Content</div>
      </PageLayout>
    );

    const main = document.querySelector('main');
    expect(main).toHaveClass('max-w-7xl');
  });

  it.skip('applies custom maxWidth when provided', () => {
    render(
      <PageLayout maxWidth="max-w-4xl">
        <div>Content</div>
      </PageLayout>
    );

    const main = document.querySelector('main');
    expect(main).toHaveClass('max-w-4xl');
  });

  it.skip('applies default classes to main element', () => {
    render(
      <PageLayout>
        <div>Content</div>
      </PageLayout>
    );

    const main = document.querySelector('main');
    expect(main).toHaveClass('max-w-7xl', 'mx-auto', 'px-6', 'py-8');
  });

  it.skip('applies custom className to main element', () => {
    render(
      <PageLayout className="custom-class">
        <div>Content</div>
      </PageLayout>
    );

    const main = document.querySelector('main');
    expect(main).toHaveClass('custom-class');
  });

  it.skip('applies background gradient to container', () => {
    render(
      <PageLayout>
        <div>Content</div>
      </PageLayout>
    );

    const container = document.querySelector('.min-h-screen');
    expect(container).toHaveClass(
      'bg-gradient-to-br',
      'from-slate-900',
      'via-slate-800',
      'to-slate-900'
    );
  });

  it.skip('maintains proper layout structure', () => {
    render(
      <PageLayout>
        <section>
          <h1>Main Content</h1>
        </section>
      </PageLayout>
    );

    const container = document.querySelector('.min-h-screen');
    expect(container?.children).toHaveLength(2); // Header and main (both mocked and real)

    const main = document.querySelector('main');
    expect(main?.querySelector('section')).toBeInTheDocument();
  });
});
