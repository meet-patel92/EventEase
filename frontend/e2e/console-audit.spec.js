import { expect, test } from '@playwright/test';

const apiBase = 'http://127.0.0.1:5174/api/v1';

async function signInAs(page, email, password) {
  const response = await page.request.post(`${apiBase}/auth/login/`, { data: { email, password } });
  expect(response.status()).toBe(200);
  const { user, tokens } = await response.json();
  await page.goto('/');
  await page.evaluate(({ profile, accessToken }) => {
    localStorage.setItem('user', JSON.stringify(profile));
    localStorage.setItem('token', accessToken);
  }, { profile: user, accessToken: tokens.access });
}

test('role dashboards and key navigation routes load without browser console errors', async ({ page }) => {
  const consoleErrors = [];
  const uncaughtErrors = [];
  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push(message.text());
  });
  page.on('pageerror', (error) => uncaughtErrors.push(error.message));

  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Find your next event' })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Home' })).toHaveAttribute('href', '/');

  await signInAs(page, 'browser.customer@example.test', 'browser-test-password-123');
  await page.goto('/dashboard');
  await expect(page.getByRole('heading', { name: 'CUSTOMER dashboard' })).toBeVisible();
  for (const [route, heading] of [
    ['/events/1', 'Browser QA Event'], ['/bookings', 'Bookings'], ['/payments', 'Payment history'],
    ['/tickets', 'My Tickets'], ['/reviews', 'Event reviews'], ['/notifications', 'Notifications'],
  ]) {
    await page.goto(route);
    await expect(page.getByRole('heading', { name: heading })).toBeVisible();
  }

  await signInAs(page, 'browser.organizer@example.test', 'browser-organizer-password-123');
  await page.goto('/dashboard');
  await expect(page.getByRole('heading', { name: 'ORGANIZER dashboard' })).toBeVisible();
  for (const [route, heading] of [
    ['/organizer/events', 'My Events'], ['/organizer/events/new', 'Create Event'], ['/ticket-scanner', 'Ticket check-in'],
  ]) {
    await page.goto(route);
    await expect(page.getByRole('heading', { name: heading })).toBeVisible();
  }

  await signInAs(page, 'browser.admin@example.test', 'browser-admin-password-123');
  await page.goto('/dashboard');
  await expect(page.getByRole('heading', { name: 'ADMIN dashboard' })).toBeVisible();
  for (const [route, heading] of [['/admin/events', 'Event Management'], ['/ticket-scanner', 'Ticket check-in']]) {
    await page.goto(route);
    await expect(page.getByRole('heading', { name: heading })).toBeVisible();
  }
  expect(consoleErrors).toEqual([]);
  expect(uncaughtErrors).toEqual([]);
});
