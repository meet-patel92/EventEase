import { expect, test } from '@playwright/test';
import { Buffer } from 'node:buffer';

const api = '**/api/v1/**';
const event = (id, status = 'PENDING') => ({
  id,
  organizer: 7,
  organizer_email: 'organizer@example.test',
  category: 3,
  category_name: 'Music',
  title: `Management Event ${id}`,
  description: 'Event details for management review.',
  venue: 'City Hall',
  address: '1 Test Avenue',
  city: 'Test City',
  event_date: '2027-08-20',
  start_time: '14:00:00',
  end_time: '18:00:00',
  registration_deadline: null,
  ticket_price: '20.00',
  total_tickets: 30,
  available_tickets: 30,
  status,
  rejection_reason: status === 'REJECTED' ? 'Please add venue access details.' : null,
});

async function asRole(page, role) {
  await page.addInitScript((userRole) => {
    localStorage.setItem('token', 'mock-access-token');
    localStorage.setItem('user', JSON.stringify({ id: 7, email: `${userRole.toLowerCase()}@example.test`, role: userRole }));
  }, role);
  await page.route('**/api/v1/notifications/unread-count/', (route) => route.fulfill({ json: { unread_count: 0 } }));
}

async function emptyPublicEvents(page) {
  await page.route('**/api/v1/notifications/unread-count/', (route) => route.fulfill({ json: { unread_count: 0 } }));
  await page.route('**/api/v1/events/', (route) => route.fulfill({
    json: { count: 0, next: null, previous: null, results: [] },
  }));
}

test('organizer can open My Events and sees event statuses with edit and create links', async ({ page }) => {
  await asRole(page, 'ORGANIZER');
  await page.route(api, (route) => {
    const url = new URL(route.request().url());
    if (url.pathname.endsWith('/events/my-events/')) {
      return route.fulfill({ json: { count: 3, next: null, previous: null, results: [event(21), event(22, 'APPROVED'), event(23, 'REJECTED')] } });
    }
    return route.fulfill({ status: 404, json: { detail: 'Not mocked.' } });
  });
  await page.goto('/organizer/events');
  await expect(page.getByRole('heading', { name: 'My Events' })).toBeVisible();
  await expect(page.getByText('PENDING', { exact: true })).toBeVisible();
  await expect(page.getByText('APPROVED', { exact: true })).toBeVisible();
  await expect(page.getByText('REJECTED', { exact: true })).toBeVisible();
  await expect(page.getByText('Please add venue access details.')).toBeVisible();
  await expect(page.getByRole('link', { name: 'Edit event' })).toHaveCount(3);
  await expect(page.getByRole('link', { name: 'Manage bookings' })).toHaveAttribute('href', '/bookings?event=22');
  await expect(page.getByRole('link', { name: 'Scan tickets' })).toHaveAttribute('href', '/ticket-scanner?event=22');
  await expect(page.getByRole('link', { name: 'Attendance report' })).toHaveAttribute('href', '/organizer/events/22/attendance');
  await expect(page.locator('.management-card').nth(0).getByRole('link', { name: 'Scan tickets' })).toHaveCount(0);
  await expect(page.locator('.management-card').nth(2).getByRole('link', { name: 'Scan tickets' })).toHaveCount(0);
  await page.getByRole('link', { name: 'Create event' }).click();
  await expect(page.getByRole('heading', { name: 'Create Event' })).toBeVisible();
});

test('only organizers can access organizer event routes', async ({ page }) => {
  await emptyPublicEvents(page);
  for (const role of ['CUSTOMER', 'ADMIN']) {
    await page.goto('/');
    await page.evaluate((userRole) => {
      localStorage.setItem('token', 'mock-access-token');
      localStorage.setItem('user', JSON.stringify({ id: 7, role: userRole }));
    }, role);
    for (const path of ['/organizer/events', '/organizer/events/new', '/organizer/events/21/edit']) {
      await page.goto(path);
      await expect(page.getByRole('heading', { name: 'Access denied' })).toBeVisible();
    }
  }
});

test('admin approval view shows pending details and confirms approval before calling the API', async ({ page }) => {
  await asRole(page, 'ADMIN');
  let currentEvent = event(31);
  let approvals = 0;
  await page.route(api, async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname.endsWith('/events/')) {
      return route.fulfill({ json: { count: currentEvent.status === 'PENDING' ? 1 : 0, next: null, previous: null, results: currentEvent.status === 'PENDING' ? [currentEvent] : [] } });
    }
    if (url.pathname.endsWith('/events/31/approve/') && route.request().method() === 'PATCH') {
      approvals += 1;
      currentEvent = { ...currentEvent, status: 'APPROVED' };
      return route.fulfill({ json: { message: 'Event approved successfully.', status: 'APPROVED' } });
    }
    return route.fulfill({ status: 404, json: { detail: 'Not mocked.' } });
  });
  await page.goto('/admin/events');
  await expect(page.getByRole('heading', { name: 'Event Management' })).toBeVisible();
  await expect(page.getByText('Management Event 31')).toBeVisible();
  await page.getByText('View event details').click();
  await expect(page.getByText('Event details for management review.')).toBeVisible();
  await page.getByRole('button', { name: 'Approve' }).click();
  await expect(page.getByRole('dialog')).toContainText('Approve “Management Event 31”?');
  await page.getByRole('button', { name: 'Cancel' }).click();
  expect(approvals).toBe(0);
  await page.getByRole('button', { name: 'Approve' }).click();
  await page.getByRole('dialog').getByRole('button', { name: 'Confirm' }).click();
  await expect(page.getByText('Management Event 31 was approved.')).toBeVisible();
  expect(approvals).toBe(1);
  await expect(page.getByText('There are no pending events to review.')).toBeVisible();
});

test('admin rejection requires a reason and confirmation before sending it', async ({ page }) => {
  await asRole(page, 'ADMIN');
  let rejectedBody;
  await page.route(api, async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname.endsWith('/events/')) return route.fulfill({ json: { count: 1, next: null, previous: null, results: [event(32)] } });
    if (url.pathname.endsWith('/events/32/reject/')) {
      rejectedBody = route.request().postDataJSON();
      return route.fulfill({ json: { message: 'Event rejected successfully.', status: 'REJECTED', rejection_reason: rejectedBody.rejection_reason } });
    }
    return route.fulfill({ status: 404, json: { detail: 'Not mocked.' } });
  });
  await page.goto('/admin/events');
  await page.getByRole('button', { name: 'Reject' }).click();
  await expect(page.getByRole('alert')).toContainText('Enter a rejection reason');
  await page.getByLabel('Rejection reason for Management Event 32').fill('Please include accessibility information.');
  await page.getByRole('button', { name: 'Reject' }).click();
  await expect(page.getByRole('dialog')).toContainText('Please include accessibility information.');
  expect(rejectedBody).toBeUndefined();
  await page.getByRole('dialog').getByRole('button', { name: 'Confirm' }).click();
  await expect(page.getByText('Management Event 32 was rejected.')).toBeVisible();
  expect(rejectedBody).toEqual({ status: 'REJECTED', rejection_reason: 'Please include accessibility information.' });
});

test('non-admin roles cannot access event approval management', async ({ page }) => {
  await emptyPublicEvents(page);
  for (const role of ['CUSTOMER', 'ORGANIZER']) {
    await page.goto('/');
    await page.evaluate((userRole) => {
      localStorage.setItem('token', 'mock-access-token');
      localStorage.setItem('user', JSON.stringify({ id: 7, role: userRole }));
    }, role);
    await page.goto('/admin/events');
    await expect(page.getByRole('heading', { name: 'Access denied' })).toBeVisible();
  }
});

test('organizer create form selects categories, uploads posters and handles API errors', async ({ page }) => {
  await asRole(page, 'ORGANIZER');
  let creates = 0;
  await page.route(api, async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname.endsWith('/events/categories/')) return route.fulfill({ json: { count: 1, next: null, previous: null, results: [{ id: 3, name: 'Music' }] } });
    if (url.pathname.endsWith('/events/') && route.request().method() === 'POST') {
      creates += 1;
      return route.fulfill({ status: 400, json: { event_date: ['Event date cannot be in the past.'] } });
    }
    if (url.pathname.endsWith('/events/my-events/')) return route.fulfill({ json: { count: 0, next: null, previous: null, results: [] } });
    return route.fulfill({ status: 404, json: { detail: 'Not mocked.' } });
  });
  await page.goto('/organizer/events/new');
  await page.getByRole('button', { name: 'Submit event' }).click();
  expect(await page.getByLabel('Event title').evaluate((input) => input.validity.valueMissing)).toBe(true);
  expect(creates).toBe(0);
  await page.getByLabel('Event title').fill('New Organizer Event');
  await page.getByLabel('Category').selectOption('3');
  await page.getByLabel('Description').fill('An event created in a browser test.');
  await page.getByLabel('Venue').fill('City Hall');
  await page.getByLabel('City').fill('Test City');
  await page.getByLabel('Event date').fill('2027-08-20');
  await page.getByLabel('Start time').fill('14:00');
  await page.getByLabel('End time').fill('18:00');
  await page.getByLabel('Ticket price').fill('25.00');
  await page.getByLabel('Total tickets').fill('10');
  await page.getByLabel('Available tickets').fill('10');
  await page.getByLabel('Poster image').setInputFiles({ name: 'poster.png', mimeType: 'image/png', buffer: Buffer.from('fake image fixture') });
  await page.getByRole('button', { name: 'Submit event' }).click();
  await expect(page.getByRole('alert')).toContainText('Event date cannot be in the past.');
  expect(creates).toBe(1);
});

test('organizer edit form loads existing values and reports update errors', async ({ page }) => {
  await asRole(page, 'ORGANIZER');
  let updates = 0;
  await page.route(api, async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname.endsWith('/events/categories/')) return route.fulfill({ json: [{ id: 3, name: 'Music' }] });
    if (url.pathname.endsWith('/events/41/') && route.request().method() === 'GET') return route.fulfill({ json: event(41) });
    if (url.pathname.endsWith('/events/41/') && route.request().method() === 'PATCH') {
      updates += 1;
      return route.fulfill({ status: 400, json: { end_time: ['End time must be later than start time.'] } });
    }
    return route.fulfill({ status: 404, json: { detail: 'Not mocked.' } });
  });
  await page.goto('/organizer/events/41/edit');
  await expect(page.getByLabel('Event title')).toHaveValue('Management Event 41');
  await expect(page.getByLabel('Category')).toHaveValue('3');
  await page.getByLabel('End time').fill('13:00');
  await page.getByRole('button', { name: 'Save changes' }).click();
  await expect(page.getByRole('alert')).toContainText('End time must be later than start time.');
  expect(updates).toBe(1);
});
