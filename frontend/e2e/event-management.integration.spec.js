import { expect, test } from '@playwright/test';

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

async function createEvent(page, title) {
  await page.goto('/organizer/events/new');
  await page.getByLabel('Event title').fill(title);
  await page.getByLabel('Category').selectOption({ label: 'Browser QA Category' });
  await expect(page.getByLabel('Category').locator('option:checked')).toHaveText('Browser QA Category');
  await page.getByLabel('Description').fill(`Submission description for ${title}.`);
  await page.getByLabel('Venue').fill('Integration Test Hall');
  await page.getByLabel('City').fill('Test City');
  await page.getByLabel('Event date').fill('2027-08-20');
  await page.getByLabel('Start time').fill('14:00');
  await page.getByLabel('End time').fill('18:00');
  await page.getByLabel('Ticket price').fill('25.00');
  await page.getByLabel('Total tickets').fill('12');
  await page.getByLabel('Available tickets').fill('12');
  await page.getByRole('button', { name: 'Submit event' }).click();
  await expect(page).toHaveURL(/\/organizer\/events$/);
  await expect(page.getByText(`${title} was submitted for approval.`)).toBeVisible();
}

test('organizer create/edit and admin approval/rejection work against isolated Django APIs', async ({ page }) => {
  await authenticateAs(page, 'browser.organizer@example.test', 'browser-organizer-password-123');
  await page.goto('/organizer/events');
  await expect(page.getByText('Browser QA Event')).toBeVisible();
  await createEvent(page, 'Browser Managed Approval Event');
  await createEvent(page, 'Browser Managed Rejection Event');
  await expect(page.getByText('PENDING', { exact: true })).toHaveCount(2);

  await authenticateAs(page, 'browser.admin@example.test', 'browser-admin-password-123');
  await page.goto('/admin/events');
  await expect(page.getByRole('heading', { name: 'Browser Managed Approval Event' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Browser Managed Rejection Event' })).toBeVisible();
  const approvalCard = page.locator('.management-card').filter({ hasText: 'Browser Managed Approval Event' });
  await approvalCard.getByText('View event details').click();
  await expect(approvalCard.getByText('Submission description for Browser Managed Approval Event.')).toBeVisible();
  await expect(approvalCard.locator('.management-detail-grid')).toContainText('Browser QA Category');
  await approvalCard.getByRole('button', { name: 'Approve' }).click();
  await page.getByRole('dialog').getByRole('button', { name: 'Confirm' }).click();
  await expect(page.getByText('Browser Managed Approval Event was approved.')).toBeVisible();

  const rejectionCard = page.locator('.management-card').filter({ hasText: 'Browser Managed Rejection Event' });
  await rejectionCard.getByLabel('Rejection reason for Browser Managed Rejection Event').fill('Please add accessibility information.');
  await rejectionCard.getByRole('button', { name: 'Reject' }).click();
  await page.getByRole('dialog').getByRole('button', { name: 'Confirm' }).click();
  await expect(page.getByText('Browser Managed Rejection Event was rejected.')).toBeVisible();
  await expect(page.getByText('There are no pending events to review.')).toBeVisible();

  await page.goto('/dashboard');
  await expect(page.getByRole('heading', { name: 'ADMIN dashboard' })).toBeVisible();
  await expect(page.getByText('Total users')).toBeVisible();
  await expect(page.getByText('Verified revenue (INR)')).toBeVisible();

  await authenticateAs(page, 'browser.organizer@example.test', 'browser-organizer-password-123');
  await page.goto('/organizer/events');
  await expect(page.locator('.event-status-badge.approved')).toHaveCount(2);
  await expect(page.locator('.event-status-badge.rejected')).toHaveCount(1);
  await expect(page.getByText('Please add accessibility information.')).toBeVisible();
  const approvedCard = page.locator('.management-card').filter({ hasText: 'Browser Managed Approval Event' });
  await approvedCard.getByRole('link', { name: 'Edit event' }).click();
  await expect(page.getByLabel('Event title')).toHaveValue('Browser Managed Approval Event');
  await expect(page.getByLabel('Category').locator('option:checked')).toHaveText('Browser QA Category');
  await page.getByLabel('City').fill('Updated Test City');
  await page.getByRole('button', { name: 'Save changes' }).click();
  await expect(page).toHaveURL(/\/organizer\/events$/);
  await expect(page.getByText('Event details saved.')).toBeVisible();
  await expect(page.locator('.event-status-badge.approved')).toHaveCount(2);
  await page.goto('/dashboard');
  await expect(page.getByRole('heading', { name: 'ORGANIZER dashboard' })).toBeVisible();
  await expect(page.getByText('Pending events')).toBeVisible();
});
