import { expect, test } from '@playwright/test';
import { join } from 'node:path';
import process from 'node:process';

const widths = [1440, 768, 390, 360];
const screenshotPath = (pageName, width) => join(process.cwd(), 'test-results', `${pageName}-${width}.png`);

async function authenticateAs(page, email, password) {
  const response = await page.request.post('http://127.0.0.1:8765/api/v1/auth/login/', {
    data: { email, password },
  });
  expect(response.status()).toBe(200);
  const payload = await response.json();
  await page.goto('/');
  await page.evaluate(({ user, token }) => {
    localStorage.setItem('token', token);
    localStorage.setItem('user', JSON.stringify(user));
  }, { user: payload.user, token: payload.tokens.access });
}

async function expectNoHorizontalOverflow(page, pageName, width) {
  const pageWidth = await page.evaluate(() => ({
    viewport: window.innerWidth,
    document: document.documentElement.scrollWidth,
    body: document.body.scrollWidth,
  }));
  expect(pageWidth.document, `${pageName} overflows at ${width}px: ${JSON.stringify(pageWidth)}`).toBeLessThanOrEqual(width);
  expect(pageWidth.body, `${pageName} body overflows at ${width}px: ${JSON.stringify(pageWidth)}`).toBeLessThanOrEqual(width);
}

test('homepage and customer, organizer and admin pages fit responsive viewports', async ({ page }) => {
  test.setTimeout(180_000);
  const pageHeight = 1000;

  for (const width of widths) {
    await page.setViewportSize({ width, height: pageHeight });
    await page.goto('/');
    await expect(page.getByRole('heading', { name: 'Find your next event' })).toBeVisible();
    await expectNoHorizontalOverflow(page, 'home', width);
    await page.screenshot({ path: screenshotPath('home', width), fullPage: true });
  }

  await authenticateAs(page, 'browser.customer@example.test', 'browser-test-password-123');
  for (const width of widths) {
    await page.setViewportSize({ width, height: pageHeight });
    await page.goto('/dashboard');
    await expect(page.getByRole('heading', { name: 'CUSTOMER dashboard' })).toBeVisible();
    await expectNoHorizontalOverflow(page, 'customer-dashboard', width);
    if (width === 1440 || width === 390) {
      await page.screenshot({ path: screenshotPath('customer-dashboard', width), fullPage: true });
    }
  }

  await authenticateAs(page, 'browser.organizer@example.test', 'browser-organizer-password-123');
  for (const width of widths) {
    await page.setViewportSize({ width, height: pageHeight });
    await page.goto('/organizer/events/new');
    await expect(page.getByRole('heading', { name: 'Create Event' })).toBeVisible();
    await expect(page.getByLabel('Category').locator('option', { hasText: 'Technology' })).toHaveCount(1);
    await expectNoHorizontalOverflow(page, 'organizer-create-event', width);
    if (width === 1440 || width === 390) {
      await page.screenshot({ path: screenshotPath('organizer-create-event', width), fullPage: true });
    }
  }

  await authenticateAs(page, 'browser.admin@example.test', 'browser-admin-password-123');
  for (const width of widths) {
    await page.setViewportSize({ width, height: pageHeight });
    await page.goto('/admin/notifications');
    await expect(page.getByRole('heading', { name: 'Send notification' })).toBeVisible();
    await expectNoHorizontalOverflow(page, 'admin-send-notification', width);
    if (width === 1440 || width === 390) {
      await page.screenshot({ path: screenshotPath('admin-send-notification', width), fullPage: true });
    }
  }
});
