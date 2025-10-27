import { test, expect } from '@playwright/test';

test.describe('Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    // Login first
    await page.goto('/login');
    await page.fill('input[type="email"]', 'test@example.com');
    await page.fill('input[type="password"]', 'password123');
    await page.click('button[type="submit"]');
    await page.waitForURL('/');
  });

  test('should load dashboard with metrics', async ({ page }) => {
    // Check dashboard header and active navigation
    await expect(page.locator('text=Netsentinel')).toBeVisible();
    await expect(page.locator('[data-discover="true"]').filter({ hasText: 'Dashboard' })).toHaveClass(/bg-blue-500/);

    // Check if metrics cards are present
    await expect(page.locator('text=Total Events')).toBeVisible();
    await expect(page.locator('text=Active Threats')).toBeVisible();
    await expect(page.locator('text=Blocked IPs')).toBeVisible();

    // Check if threat timeline is present
    await expect(page.locator('text=Threat Timeline')).toBeVisible();

    // Check if system health section is present
    await expect(page.locator('text=System Health')).toBeVisible();

    // Check if alerts feed is present
    await expect(page.locator('text=Active Alerts')).toBeVisible();
  });

  test('should navigate between pages', async ({ page }) => {
    // Test navigation to Threats page
    await page.click('[data-discover="true"]:has-text("Threats")');
    await expect(page).toHaveURL('/threats');
    await expect(page.locator('[data-discover="true"]').filter({ hasText: 'Threats' })).toHaveClass(/bg-blue-500/);

    // Test navigation to Alerts page
    await page.click('[data-discover="true"]:has-text("Alerts")');
    await expect(page).toHaveURL('/alerts');
    await expect(page.locator('[data-discover="true"]').filter({ hasText: 'Alerts' })).toHaveClass(/bg-blue-500/);

    // Test navigation back to Dashboard
    await page.click('[data-discover="true"]:has-text("Dashboard")');
    await expect(page).toHaveURL('/');
    await expect(page.locator('[data-discover="true"]').filter({ hasText: 'Dashboard' })).toHaveClass(/bg-blue-500/);
  });

  test('should handle mobile navigation', async ({ page }) => {
    // Set viewport to mobile size
    await page.setViewportSize({ width: 375, height: 667 });

    // Check if mobile menu button is visible (should be visible on screens < 768px)
    const mobileMenuButton = page.locator('button').filter({ has: page.locator('svg.lucide-menu') });
    await expect(mobileMenuButton).toBeVisible();

    // Open mobile menu
    await mobileMenuButton.click();

    // Check if navigation items are visible in mobile menu
    await expect(page.locator('text=Threats')).toBeVisible();
    await expect(page.locator('text=Alerts')).toBeVisible();
    await expect(page.locator('text=Network')).toBeVisible();
  });

  test('should display user info and logout', async ({ page }) => {
    // Check if user info is displayed (name and role)
    // For email login, name is extracted from email, role defaults to admin
    await expect(page.locator('text=test')).toBeVisible(); // name from test@example.com
    await expect(page.locator('text=admin')).toBeVisible(); // role

    // Open user menu (click the user button)
    const userButton = page.locator('button').filter({ has: page.locator('svg.lucide-user') });
    await userButton.click();

    // Check if logout option is available
    await expect(page.locator('text=Sign Out')).toBeVisible();
  });

  test('should logout successfully', async ({ page }) => {
    // Open user menu
    const userButton = page.locator('button').filter({ has: page.locator('svg.lucide-user') });
    await userButton.click();

    // Click logout
    await page.click('text=Sign Out');

    // Should redirect to login
    await expect(page).toHaveURL('/login');
    await expect(page.locator('text=Netsentinel')).toBeVisible();
  });
});
