const { test, expect } = require('@playwright/test');

test('planner builds a report and supports follow-up questions', async ({ page }) => {
  await page.goto('/', { waitUntil: 'domcontentloaded' });

  await expect(page.locator('.logo')).toContainText('AgriBusiness OS AI');

  await page.getByRole('button', { name: 'Kerala' }).click({ force: true });
  await expect(page.locator('#user-input')).toHaveValue(/Kerala/);

  await page.locator('#user-input').fill(
    '5 acres black soil in Dharwad, Karnataka with borewell irrigation'
  );
  await page.locator('#send-btn').click();

  await expect(page.locator('#dashboard-view')).toBeVisible();
  await expect(page.locator('.report-section.markdown-body')).toContainText(
    'Mock Decision Report'
  );
  await expect(page.locator('.citation-badge').first()).toContainText('[1]');

  await page.locator('#followup-input').fill('What should I do next?');
  await page.locator('#followup-send-btn').click();

  await expect(page.locator('#followup-messages')).toContainText('What should I do next?');
  await expect(page.locator('#followup-messages')).toContainText('Follow-up answer');
  await expect(page.locator('#followup-messages')).toContainText('Recommendation');
});
