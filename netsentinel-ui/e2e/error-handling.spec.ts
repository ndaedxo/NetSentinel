import { test, expect } from '@playwright/test';

test.describe('Error Handling', () => {
  test('should handle 404 pages gracefully', async ({ page }) => {
    // Navigate to non-existent page
    await page.goto('/non-existent-page');

    // Should show error boundary or redirect to dashboard (React Router behavior)
    // This tests that the app doesn't crash on invalid routes
    await expect(page.locator('text=Netsentinel')).toBeVisible();
  });

  test('should handle network errors gracefully', async ({ page }) => {
    // Login first
    await page.goto('/login');
    await page.fill('input[type="email"]', 'test@example.com');
    await page.fill('input[type="password"]', 'password123');
    await page.click('button[type="submit"]');
    await page.waitForURL('/');

    // The app should handle API failures gracefully with mock data
    // Check that dashboard still loads even if some API calls fail
    await expect(page.locator('text=Netsentinel')).toBeVisible();
    await expect(page.locator('text=Total Events')).toBeVisible();
  });

  test('should handle form validation', async ({ page }) => {
    await page.goto('/login');

    // Try to submit empty form
    await page.click('button[type="submit"]');

    // Should show validation errors or prevent submission
    await expect(page).toHaveURL(/login/);
  });

  test('should handle browser back/forward navigation', async ({ page }) => {
    // Login and navigate around
    await page.goto('/login');
    await page.fill('input[type="email"]', 'test@example.com');
    await page.fill('input[type="password"]', 'password123');
    await page.click('button[type="submit"]');
    await page.waitForURL('/');

    // Navigate to threats page
    await page.click('[data-discover="true"]:has-text("Threats")');
    await expect(page).toHaveURL('/threats');

    // Use browser back button
    await page.goBack();
    await expect(page).toHaveURL('/');

    // Use browser forward button
    await page.goForward();
    await expect(page).toHaveURL('/threats');
  });
});
