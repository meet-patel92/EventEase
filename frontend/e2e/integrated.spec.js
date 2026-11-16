import { expect, test } from '@playwright/test';

test('browser integrates with isolated Django for login, reviews, notifications and unpaid booking', async ({ page }) => {
  await page.goto('/login');
  await page.getByLabel('Email').fill('browser.customer@example.test');
  await page.getByLabel('Password').fill('browser-test-password-123');
  const loginResponsePromise = page.waitForResponse((response) => response.url().includes('/api/v1/auth/login/'));
  await page.getByRole('button', { name: 'Sign in' }).click();
  const loginResponse = await loginResponsePromise;
  expect(loginResponse.status()).toBe(200);
  await expect(page).toHaveURL(/\/$/);

  await expect(page.getByRole('heading', { name: 'Browser QA Event' })).toBeVisible();
  await page.locator('.event-card').filter({ hasText: 'Browser QA Event' }).getByRole('link', { name: 'View event' }).click();
  await expect(page.getByText('No reviews yet. Be the first to share your experience.')).toBeVisible();
  await page.getByLabel('Rating').selectOption('5');
  await page.getByLabel('Comment').fill('Browser integration review.');
  await page.getByRole('button', { name: 'Submit review' }).click();
  await expect(page.getByRole('status').filter({ hasText: 'Your review was saved.' })).toBeVisible();
  await expect(page.locator('.review-card').getByText('Browser integration review.', { exact: true })).toBeVisible();

  const notificationsLink = page.getByRole('link', { name: /Notifications/ });
  await expect(notificationsLink).toContainText('1');
  await notificationsLink.click();
  await expect(page.getByText('Browser QA notification')).toBeVisible();
  await expect(page.getByText('SENT')).toBeVisible();
  await page.getByRole('button', { name: 'Mark as read' }).click();
  await expect(page.locator('.notification-card.read')).toContainText('Read');
  await expect(page.getByRole('link', { name: 'Notifications', exact: true })).toBeVisible();

  await page.getByRole('link', { name: 'Home' }).click();
  await page.locator('.event-card').filter({ hasText: 'Browser QA Event' }).getByRole('link', { name: 'View event' }).click();
  await page.getByLabel('Quantity').fill('2');
  await page.getByRole('button', { name: 'Reserve tickets' }).click();
  await expect(page).toHaveURL(/\/bookings\/\d+$/);
  await expect(page.getByRole('heading', { name: 'Browser QA Event' })).toBeVisible();
  await expect(page.getByText('PENDING')).toBeVisible();

  const token = await page.evaluate(() => localStorage.getItem('token'));
  const bookingsUrl = new URL('/api/v1/bookings/', page.url()).toString();
  const bookingsResponse = await page.request.get(bookingsUrl, {
    headers: { Authorization: `Bearer ${token}` },
  });
  expect(bookingsResponse.ok()).toBeTruthy();
  const bookings = await bookingsResponse.json();
  expect(bookings.results.some((booking) => booking.event_title === 'Browser QA Event' && booking.status === 'PENDING')).toBeTruthy();

  await page.goto('/dashboard');
  await expect(page.getByRole('heading', { name: 'CUSTOMER dashboard' })).toBeVisible();
  await expect(page.getByRole('navigation', { name: 'Dashboard shortcuts' }).getByRole('link', { name: 'Bookings' })).toBeVisible();
});
