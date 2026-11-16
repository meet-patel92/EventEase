import { expect, test } from '@playwright/test';

test('admin sends an event notification to its booked customers in-app', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('token', 'mock-access-token');
    localStorage.setItem('user', JSON.stringify({ id: 1, username: 'admin', role: 'ADMIN' }));
  });
  await page.route('**/api/v1/notifications/unread-count/', (route) => route.fulfill({ json: { unread_count: 0 } }));
  await page.route('**/api/v1/notifications/send-options/', (route) => route.fulfill({ json: {
    customers: [{ id: 7, email: 'customer@example.test', name: 'Event Customer' }],
    events: [{ id: 42, title: 'City Jazz Evening', event_date: '2027-06-15', status: 'APPROVED', recipient_count: 1 }],
  } }));

  let submittedPayload;
  await page.route('**/api/v1/notifications/send/', async (route) => {
    submittedPayload = route.request().postDataJSON();
    await route.fulfill({ status: 201, json: {
      recipient_count: 1,
      status: 'PENDING',
      delivery: 'IN_APP_ONLY',
      message: 'Notification saved to 1 customer inbox(es). No external email, SMS, or push message was sent.',
    } });
  });

  await page.goto('/admin/notifications');
  await expect(page.getByRole('heading', { name: 'Send notification' })).toBeVisible();
  await page.getByLabel('Notification title').fill('Venue update');
  await page.getByLabel('Notification type').selectOption('SMS');
  await page.getByLabel('Message').fill('Please use the north entrance.');
  await page.getByLabel('Recipients').selectOption('EVENT_CUSTOMERS');
  await page.locator('select[name="event"]').selectOption('42');
  await page.getByRole('button', { name: 'Send notification' }).click();

  await expect(page.getByRole('status')).toContainText('saved to 1 customer inbox');
  expect(submittedPayload).toEqual({
    title: 'Venue update',
    message: 'Please use the north entrance.',
    type: 'SMS',
    recipient_scope: 'EVENT_CUSTOMERS',
    event: 42,
  });
});
