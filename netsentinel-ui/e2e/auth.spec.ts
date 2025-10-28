import { test, expect } from '@playwright/test';

test.describe('Authentication', () => {
  test('should login with valid credentials', async ({ page }) => {
    // Navigate to login page
    await page.goto('/login');

    // Check if we're on the login page
    await expect(page).toHaveTitle(/Netsentinel/);
    await expect(page.locator('h1')).toContainText('Netsentinel');

    // Fill in login form
    await page.fill('input[type="email"]', 'test@example.com');
    await page.fill('input[type="password"]', 'password123');

    // Click login button
    await page.click('button[type="submit"]');

    // Should redirect to dashboard
    await expect(page).toHaveURL('/');
    // Check for dashboard content (header shows "Netsentinel", navigation shows "Dashboard" as active)
    await expect(page.locator('h1:has-text("Netsentinel")')).toBeVisible();
    await expect(page.locator('[data-discover="true"]').filter({ hasText: 'Dashboard' })).toHaveClass(/bg-blue-500/);
  });

  test('should show error for invalid credentials', async ({ page }) => {
    await page.goto('/login');

    // Try to login without credentials
    await page.click('button[type="submit"]');

    // Should stay on login page (form validation)
    await expect(page).toHaveURL(/login/);
  });

  test('should allow OAuth login flow', async ({ page }) => {
    await page.goto('/login');

    // Click OAuth button
    await page.click('text=Continue with Google OAuth');

    // Should redirect to OAuth callback
    await expect(page).toHaveURL(/auth\/callback/);

    // Should then redirect to dashboard
    await page.waitForURL('/');
    // Check for dashboard content
    await expect(page.locator('h1:has-text("Netsentinel")')).toBeVisible();
    await expect(page.locator('[data-discover="true"]').filter({ hasText: 'Dashboard' })).toHaveClass(/bg-blue-500/);
  });
});
