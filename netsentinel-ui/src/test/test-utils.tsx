import { ReactElement, ReactNode } from 'react';
import { render, RenderOptions } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';
import { MemoryRouter } from 'react-router';
import { AuthProvider } from '@/hooks/mock-auth';
import { ToastProvider } from '@/hooks/useToast';

// Add jest-axe matchers
expect.extend(toHaveNoViolations);

interface ProvidersProps {
  children: ReactNode;
}

function AllProviders({ children }: ProvidersProps) {
  return (
    <MemoryRouter>
      <AuthProvider>
        <ToastProvider>
          {children}
        </ToastProvider>
      </AuthProvider>
    </MemoryRouter>
  );
}

function renderWithProviders(ui: ReactElement, options?: Omit<RenderOptions, 'wrapper'>) {
  return render(ui, { wrapper: AllProviders, ...options });
}

// Accessibility testing utilities
export const testA11y = async (ui: ReactElement) => {
  const { container } = renderWithProviders(ui);
  const results = await axe(container);
  expect(results).toHaveNoViolations();
};

export const testA11yWithContainer = async (container: HTMLElement) => {
  const results = await axe(container);
  expect(results).toHaveNoViolations();
};

export * from '@testing-library/react';
export { renderWithProviders as render };


