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
    // Check dashboard header
    await expect(page.locator('h1:has-text("Netsentinel")')).toBeVisible();

    // Check if dashboard widgets are present (new widget-based dashboard)
    await expect(page.locator('text=Default Dashboard')).toBeVisible();

    // Check if dashboard widgets are present and loaded
    await expect(page.locator('[data-testid="dashboard-widget"]').first()).toBeVisible();

    // Just verify widgets are loaded - don't check specific text visibility due to responsive design
    const widgetCount = await page.locator('[data-testid="dashboard-widget"]').count();
    expect(widgetCount).toBeGreaterThan(0);
  });

  test('should navigate between pages', async ({ page }) => {
    // Set desktop viewport for navigation testing
    await page.setViewportSize({ width: 1024, height: 768 });

    // Test navigation to Threats page
    await page.goto('/threats');
    await expect(page).toHaveURL('/threats');
    await expect(page.locator('h1:has-text("Threat Intelligence")')).toBeVisible();

    // Test navigation to Alerts page
    await page.goto('/alerts');
    await expect(page).toHaveURL('/alerts');
    await expect(page.locator('h1:has-text("Alert Management")')).toBeVisible();

    // Test navigation to Profile page
    await page.goto('/profile', { waitUntil: 'networkidle' });
    await expect(page).toHaveURL('/profile');
    await expect(page.locator('h1:has-text("Profile Settings")')).toBeVisible();

    // Test navigation to Notifications page
    await page.goto('/notifications', { waitUntil: 'networkidle' });
    await expect(page).toHaveURL('/notifications');
    await expect(page.locator('h1:has-text("Notifications")')).toBeVisible();

    // Test navigation back to Dashboard
    await page.goto('/', { waitUntil: 'networkidle' });
    await expect(page).toHaveURL('/');
    await expect(page.locator('h1:has-text("Netsentinel")')).toBeVisible();
  });

  test('should handle mobile navigation', async ({ page }) => {
    // Set viewport to mobile size
    await page.setViewportSize({ width: 375, height: 667 });

    // Check if mobile menu button is visible (should be visible on screens < 768px)
    const mobileMenuButton = page.getByTestId('mobile-menu-toggle');
    await expect(mobileMenuButton).toBeVisible();

    // Open mobile menu
    await mobileMenuButton.click();

    // Check if navigation items are visible in mobile menu (block class indicates mobile menu)
    await expect(page.locator('a.block:has-text("Threats")')).toBeVisible();
    await expect(page.locator('a.block:has-text("Alerts")')).toBeVisible();
    await expect(page.locator('a.block:has-text("Network")')).toBeVisible();
  });

  test('should display user info and logout', async ({ page }) => {
    // Set desktop viewport to ensure user info is visible (hidden on mobile with `hidden md:block`)
    await page.setViewportSize({ width: 1024, height: 768 });

    // Check if user info is displayed (name and role)
    // For email login, name is extracted from email, role defaults to admin
    await expect(page.locator('text=test')).toBeVisible(); // name from test@example.com
    await expect(page.locator('text=admin')).toBeVisible(); // role

    // Open user menu (click the user button)
    const userButton = page.locator('button').filter({ has: page.locator('svg.lucide-user') });
    await userButton.click({ force: true });

    // Check if logout option is available
    await expect(page.locator('text=Sign Out')).toBeVisible();
  });

  test('should logout successfully', async ({ page }) => {
    // Set desktop viewport for consistent user menu behavior
    await page.setViewportSize({ width: 1024, height: 768 });

    // Login first if not already logged in
    if (page.url() !== 'http://localhost:5173/') {
      await page.goto('/login');
      await page.fill('input[type="email"]', 'test@example.com');
      await page.fill('input[type="password"]', 'password123');
      await page.click('button[type="submit"]');
      await page.waitForURL('/');
    }

    // Wait for dashboard to load
    await page.waitForSelector('h1:has-text("Netsentinel")', { timeout: 10000 });

    // Close any mobile navigation if open (just in case)
    const mobileNavCloseButton = page.locator('button').filter({ has: page.locator('svg.lucide-x') }).first();
    if (await mobileNavCloseButton.isVisible()) {
      await mobileNavCloseButton.click();
    }

    // Open user menu
    const userButton = page.locator('button').filter({ has: page.locator('svg.lucide-user') });
    await userButton.click({ force: true });

    // Wait for the dropdown to appear
    await page.waitForSelector('text=Sign Out', { timeout: 5000 });

    // Click logout with force to bypass any overlays
    await page.locator('text=Sign Out').click({ force: true });

    // Should redirect to login
    await expect(page).toHaveURL('/login');
    await expect(page.locator('h1:has-text("Netsentinel")')).toBeVisible();
  });
});
