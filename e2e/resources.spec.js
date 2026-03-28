const { test, expect } = require('@playwright/test');

test('video library renders curated video cards', async ({ page }) => {
  await page.goto('/videos');

  await expect(page.locator('h1')).toContainText('Learn Agri-Business');
  await expect(page.locator('.video-card')).toHaveCount(5);
  await expect(page.locator('.video-card h3').first()).toContainText(
    '10 Lucrative Agricultural Business Ideas'
  );
});

test('startup cards expand and expose website links', async ({ page }) => {
  await page.goto('/startups');

  await expect(page.locator('h1')).toContainText('Agri Startup References');
  await page.locator('.startup-expand summary').first().click();
  await expect(page.locator('.startup-site-btn').first()).toBeVisible();
  await expect(page.locator('.startup-site-btn').first()).toHaveAttribute(
    'href',
    /https:\/\//
  );
});
