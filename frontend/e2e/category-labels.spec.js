import { expect, test } from '@playwright/test';

const events = [
  { id: 1, title: 'Film preview', category_name: '[DEMO] FILM & MEDIA', event_date: '2027-01-15', city: 'Mumbai', venue: 'Cinema', ticket_price: '0.00', available_tickets: 20, poster: null },
  { id: 2, title: 'Community gathering', category_name: '[DEMO] COMMUNITY', event_date: '2027-01-16', city: 'Pune', venue: 'Park', ticket_price: '0.00', available_tickets: 30, poster: null },
];

test('homepage category labels are clean on desktop and mobile', async ({ page }) => {
  await page.route('**/api/v1/notifications/unread-count/', (route) => route.fulfill({ json: { unread_count: 0 } }));
  await page.route('**/api/v1/events/**', (route) => route.fulfill({
    json: { count: events.length, next: null, previous: null, results: events },
  }));

  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto('/');
    await expect(page.getByText('FILM & MEDIA', { exact: true }).first()).toBeVisible();
    await expect(page.getByText('COMMUNITY', { exact: true }).first()).toBeVisible();
    await expect(page.getByText('[DEMO] FILM & MEDIA')).toHaveCount(0);
    await expect(page.getByText('[DEMO] COMMUNITY')).toHaveCount(0);
  }
});
