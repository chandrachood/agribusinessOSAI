const { test, expect } = require('@playwright/test');

test('government schemes page submits and renders report', async ({ page }) => {
  await page.goto('/policies', { waitUntil: 'domcontentloaded' });

  await page.locator('input[name="location"]').fill('Mysuru, Karnataka');
  await page.locator('input[name="crops"]').fill('banana, maize');
  await page.locator('select[name="language"]').selectOption('hi');
  await page.getByRole('button', { name: 'Search Government Schemes' }).click();

  await expect(page.locator('.policy-result-card')).toContainText('Mock subsidy');
  await expect(page.locator('.policy-source-list')).toContainText('Mock Policy Portal');
  await expect(page.locator('.policy-result-card')).toContainText('Mysuru, Karnataka');
});
