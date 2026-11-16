import { expect, test } from '@playwright/test';

const api = '**/api/v1/**';
const event = {
  id: 42,
  title: 'Browser Test Festival',
  description: 'A mocked event for browser QA.',
  venue: 'Test Park',
  city: 'Test City',
  event_date: '2027-06-15',
  start_time: '14:00:00',
  end_time: '18:00:00',
  ticket_price: '25.00',
  total_tickets: 40,
  available_tickets: 40,
  status: 'APPROVED',
};

const ticket = {
  id: 91,
  ticket_number: 'TKT-BROWSER1',
  ticket_token: 'MOCK-QR-TOKEN',
  event: 42,
  event_title: event.title,
  event_date: event.event_date,
  start_time: event.start_time,
  venue: event.venue,
  city: event.city,
  status: 'VALID',
  booking_id: 51,
  booking_reference: 'BM-BROWSER1',
  booking_quantity: 2,
  booking_total_amount: '50.00',
  booking_status: 'CONFIRMED',
  customer_email: 'customer@example.test',
  issued_at: '2026-11-01T10:00:00Z',
};

async function mockDefaultApi(page) {
  await page.route(api, async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname.endsWith('/notifications/unread-count/')) {
      await route.fulfill({ json: { unread_count: 0 } });
      return;
    }
    if (url.pathname.endsWith('/events/')) {
      await route.fulfill({ json: { count: 0, next: null, previous: null, results: [] } });
      return;
    }
    await route.fulfill({ status: 404, json: { detail: 'Not mocked by this test.' } });
  });
}

async function setUser(page, role = 'CUSTOMER') {
  await page.addInitScript((userRole) => {
    localStorage.setItem('token', 'mock-access-token');
    localStorage.setItem('user', JSON.stringify({ id: 7, email: 'customer@example.test', role: userRole }));
  }, role);
  await page.route('**/api/v1/notifications/unread-count/', (route) => route.fulfill({ json: { unread_count: 0 } }));
}

test('login shows service errors and keeps the user on the login page', async ({ page }) => {
  await mockDefaultApi(page);
  await page.route('**/api/v1/auth/login/', (route) => route.fulfill({
    status: 400,
    json: { non_field_errors: ['Invalid email or password.'] },
  }));
  await page.goto('/login');
  await page.getByLabel('Email').fill('customer@example.test');
  await page.getByLabel('Password').fill('not-a-real-password');
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page.getByRole('alert')).toHaveText('Invalid email or password.');
  await expect(page).toHaveURL(/\/login$/);
});

test('login accepts a mocked response and redirects to the event listing', async ({ page }) => {
  await page.route(api, async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname.endsWith('/auth/login/')) {
      await route.fulfill({ json: {
        user: { id: 7, email: 'customer@example.test', role: 'CUSTOMER' },
        tokens: { access: 'mock-access-token' },
      } });
    } else if (url.pathname.endsWith('/events/')) {
      await route.fulfill({ json: { count: 0, next: null, previous: null, results: [] } });
    } else {
      await route.fulfill({ status: 404, json: { detail: 'Not mocked.' } });
    }
  });
  await page.goto('/login');
  await page.getByLabel('Email').fill('customer@example.test');
  await page.getByLabel('Password').fill('mock-password');
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole('heading', { name: 'Find your next event' })).toBeVisible();
  await expect(page.getByText('No events are available right now.')).toBeVisible();
});

test('event listing exposes loading, empty and API error states', async ({ page }) => {
  let releaseResponse;
  const waitForResponse = new Promise((resolve) => { releaseResponse = resolve; });
  await page.route('**/api/v1/events/', async (route) => {
    await waitForResponse;
    await route.fulfill({ json: { count: 0, next: null, previous: null, results: [] } });
  });
  await page.goto('/');
  await expect(page.getByRole('status').filter({ hasText: 'Loading events' })).toBeVisible();
  releaseResponse();
  await expect(page.getByText('No events are available right now.')).toBeVisible();

  await page.unroute('**/api/v1/events/');
  await page.route('**/api/v1/events/', (route) => route.fulfill({
    status: 503,
    json: { detail: 'Event service unavailable.' },
  }));
  await page.reload();
  await expect(page.getByRole('alert')).toContainText('Event service unavailable.');
});

test('public event list opens the event detail page', async ({ page }) => {
  await page.route('**/api/v1/events/**', (route) => {
    const url = new URL(route.request().url());
    if (url.pathname.endsWith('/events/')) {
      return route.fulfill({ json: { count: 1, next: null, previous: null, results: [event] } });
    }
    return route.fulfill({ json: event });
  });
  await page.goto('/');
  await page.getByRole('link', { name: 'View event' }).click();
  await expect(page).toHaveURL(/\/events\/42$/);
  await expect(page.getByRole('heading', { name: event.title })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Sign in to book' })).toBeVisible();
});

test('dashboard shortcuts respect customer, organizer and admin roles', async ({ page }) => {
  let currentRole = 'CUSTOMER';
  await mockDefaultApi(page);
  await page.route('**/api/v1/dashboard/overview/', (route) => {
    return route.fulfill({ json: { role: currentRole, cards: [], upcoming_events: [], recent_bookings: [], event_bookings: [] } });
  });
  for (const role of ['CUSTOMER', 'ORGANIZER', 'ADMIN']) {
    currentRole = role;
    await page.goto('/');
    await page.evaluate((userRole) => {
      localStorage.setItem('token', 'mock-access-token');
      localStorage.setItem('user', JSON.stringify({ id: 7, role: userRole }));
    }, role);
    await page.goto('/dashboard');
    await expect(page.getByRole('heading', { name: `${role} dashboard` })).toBeVisible();
    const scannerLink = page.getByRole('link', { name: 'Ticket check-in' });
    if (role === 'CUSTOMER') await expect(scannerLink).toHaveCount(0);
    else await expect(scannerLink).toBeVisible();
    const approvalsLink = page.getByRole('link', { name: 'Events and approvals' });
    if (role === 'ADMIN') await expect(approvalsLink).toBeVisible();
    else await expect(approvalsLink).toHaveCount(0);
  }
});

test('customer is denied direct access to the staff ticket scanner route', async ({ page }) => {
  await setUser(page, 'CUSTOMER');
  await mockDefaultApi(page);
  await page.goto('/ticket-scanner');
  await expect(page.getByRole('heading', { name: 'Access denied' })).toBeVisible();
});

test('admin and organizer can open the ticket scanner', async ({ page }) => {
  await page.route('**/api/v1/notifications/unread-count/', (route) => route.fulfill({ json: { unread_count: 0 } }));
  await page.route('**/api/v1/events/**', (route) => route.fulfill({
    json: { count: 0, next: null, previous: null, results: [] },
  }));
  for (const role of ['ADMIN', 'ORGANIZER']) {
    await page.goto('/');
    await page.evaluate((userRole) => {
      localStorage.setItem('token', 'mock-access-token');
      localStorage.setItem('user', JSON.stringify({ id: 7, role: userRole }));
    }, role);
    await page.goto('/ticket-scanner');
    await expect(page.getByRole('heading', { name: 'Ticket check-in' })).toBeVisible();
  }
});

test('customer can submit or update an event review and sees validation and success states', async ({ page }) => {
  await setUser(page);
  let attempts = 0;
  await page.route('**/api/v1/events/42/', (route) => route.fulfill({ json: event }));
  await page.route('**/api/v1/reviews/**', async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname.endsWith('/reviews/') && route.request().method() === 'GET') {
      await route.fulfill({ json: { count: 0, next: null, previous: null, results: [] } });
    } else if (route.request().method() === 'POST') {
      attempts += 1;
      if (attempts === 1) {
        await route.fulfill({ status: 400, json: { event: ['A review already exists for this event.'] } });
      } else {
        await route.fulfill({ status: 201, json: {
          id: 8, event: 42, user: 7, user_email: 'customer@example.test', rating: 5,
          comment: 'Great event.', created_at: '2026-11-01T10:00:00Z',
        } });
      }
    } else {
      await route.fulfill({ status: 404, json: { detail: 'Not mocked.' } });
    }
  });
  await page.goto('/events/42');
  await expect(page.getByText('No reviews yet. Be the first to share your experience.')).toBeVisible();
  await page.getByLabel('Comment').fill('Great event.');
  await page.getByRole('button', { name: 'Submit review' }).click();
  await expect(page.getByRole('alert')).toHaveText('A review already exists for this event.');
  await page.getByRole('button', { name: 'Submit review' }).click();
  await expect(page.getByRole('status').filter({ hasText: 'Your review was saved.' })).toBeVisible();
  await expect(page.getByText('Your review', { exact: true })).toBeVisible();
});

test('notifications show read state and update the unread navigation count', async ({ page }) => {
  await setUser(page);
  let rows = [{
      id: 5, user: 7, title: 'Booking update', message: 'Your booking is confirmed.',
      type: 'EMAIL', status: 'SENT', is_read: false, created_at: '2026-11-01T10:00:00Z', sent_at: '2026-11-01T10:01:00Z',
    }, {
      id: 6, user: 7, title: 'Event reminder', message: 'Your event starts soon.',
      type: 'PUSH', status: 'PENDING', is_read: false, created_at: '2026-11-02T10:00:00Z', sent_at: null,
    }];
  await page.route('**/api/v1/notifications/unread-count/', (route) => route.fulfill({ json: { unread_count: 2 } }));
  await page.route('**/api/v1/notifications/', (route) => route.fulfill({ json: {
    count: rows.length, next: null, previous: null, results: rows,
  } }));
  await page.route('**/api/v1/notifications/5/mark-read/', async (route) => {
    rows = rows.map((row) => row.id === 5 ? { ...row, is_read: true } : row);
    await route.fulfill({ json: rows.find((row) => row.id === 5) });
  });
  await page.route('**/api/v1/notifications/mark-all-read/', async (route) => {
    rows = rows.map((row) => ({ ...row, is_read: true }));
    await route.fulfill({ json: { updated: 1, unread_count: 0 } });
  });
  await page.goto('/notifications');
  await expect(page.getByRole('heading', { name: 'Notifications' })).toBeVisible();
  await expect(page.getByText('Booking update')).toBeVisible();
  await expect(page.getByText('SENT')).toBeVisible();
  await expect(page.getByRole('link', { name: /Notifications 2/ })).toBeVisible();
  const unreadCard = page.locator('.notification-card.unread');
  await expect(unreadCard.first()).toContainText('Unread');
  await unreadCard.first().getByRole('button', { name: 'Mark as read' }).click();
  await expect(page.locator('.notification-card.unread')).toHaveCount(1);
  await expect(page.getByRole('link', { name: /Notifications 1/ })).toBeVisible();
  await page.getByRole('button', { name: 'Mark all as read' }).click();
  await expect(page.getByRole('button', { name: 'Mark all as read' })).toBeDisabled();
  await expect(page.locator('.notification-card.read')).toHaveCount(2);
});

test('notification page handles empty and service-error states', async ({ page }) => {
  await setUser(page);
  await page.route('**/api/v1/notifications/', (route) => route.fulfill({
    json: { count: 0, next: null, previous: null, results: [] },
  }));
  await page.goto('/notifications');
  await expect(page.getByText('You have no notifications yet.')).toBeVisible();

  await page.unroute('**/api/v1/notifications/');
  await page.route('**/api/v1/notifications/', (route) => route.fulfill({
    status: 503, json: { detail: 'Notifications temporarily unavailable.' },
  }));
  await page.reload();
  await expect(page.getByRole('alert')).toContainText('Notifications temporarily unavailable.');
});

test('reviews page lists reviews and handles empty and error states', async ({ page }) => {
  await setUser(page);
  await page.route('**/api/v1/reviews/', (route) => route.fulfill({ json: {
    count: 1, next: null, previous: null,
    results: [{
      id: 12, user: 7, user_email: 'customer@example.test', event: 42, rating: 5,
      comment: '[DEMO DATA] Sample feedback.', created_at: '2026-11-01T10:00:00Z',
    }, {
      id: 13, user: 8, user_email: 'attendee@example.test', event: 42, rating: 4,
      comment: 'The event was welcoming and well organized.', created_at: '2026-11-02T10:00:00Z',
    }],
  } }));
  await page.goto('/reviews');
  await expect(page.getByRole('heading', { name: 'Event reviews' })).toBeVisible();
  await expect(page.getByText('[DEMO DATA] Sample feedback.')).toHaveCount(0);
  await expect(page.getByText('The event was welcoming and well organized.')).toBeVisible();
  await expect(page.getByRole('link', { name: 'View event' })).toHaveAttribute('href', '/events/42');

  await page.unroute('**/api/v1/reviews/');
  await page.route('**/api/v1/reviews/', (route) => route.fulfill({
    json: { count: 0, next: null, previous: null, results: [] },
  }));
  await page.reload();
  await expect(page.getByText('No event reviews have been submitted yet.')).toBeVisible();

  await page.unroute('**/api/v1/reviews/');
  await page.route('**/api/v1/reviews/', (route) => route.fulfill({
    status: 503, json: { detail: 'Reviews temporarily unavailable.' },
  }));
  await page.reload();
  await expect(page.getByRole('alert')).toContainText('Reviews temporarily unavailable.');
});

test('customer can complete a mocked booking and payment journey to tickets', async ({ page }) => {
  await setUser(page);
  await page.addInitScript(() => {
    window.Razorpay = function MockRazorpay(options) {
      this.on = () => {};
      this.open = () => setTimeout(() => options.handler({
        razorpay_order_id: 'order_mock',
        razorpay_payment_id: 'payment_mock',
        razorpay_signature: 'local-browser-test-signature',
      }), 0);
    };
  });
  const booking = {
    id: 51,
    booking_reference: 'BM-BROWSER1',
    customer: 7,
    event: 42,
    event_title: event.title,
    event_date: event.event_date,
    start_time: event.start_time,
    end_time: event.end_time,
    venue: event.venue,
    city: event.city,
    quantity: 2,
    unit_price: '25.00',
    total_amount: '50.00',
    status: 'PENDING',
    booking_date: '2026-11-01T10:00:00Z',
  };
  await page.route(api, async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (url.pathname.endsWith('/events/')) {
      await route.fulfill({ json: { count: 1, next: null, previous: null, results: [event] } });
    } else if (url.pathname.endsWith('/events/42/')) {
      await route.fulfill({ json: event });
    } else if (url.pathname.endsWith('/bookings/') && request.method() === 'POST') {
      await route.fulfill({ status: 201, json: booking });
    } else if (url.pathname.endsWith('/bookings/51/')) {
      await route.fulfill({ json: booking });
    } else if (url.pathname.endsWith('/payments/create-order/')) {
      await route.fulfill({ status: 201, json: {
        order_id: 'order_mock', amount: 5000, currency: 'INR', booking_id: 51,
        booking_reference: booking.booking_reference, key: 'rzp_test_mock',
      } });
    } else if (url.pathname.endsWith('/payments/verify/')) {
      await route.fulfill({ json: { status: 'SUCCESS', booking_status: 'CONFIRMED' } });
    } else if (url.pathname.endsWith('/tickets/my-tickets/')) {
      await route.fulfill({ json: { count: 1, next: null, previous: null, results: [ticket] } });
    } else {
      await route.fulfill({ status: 404, json: { detail: 'Not mocked.' } });
    }
  });

  await page.goto('/');
  await page.getByRole('link', { name: 'View event' }).click();
  await page.getByLabel('Quantity').fill('2');
  await page.getByRole('button', { name: 'Reserve tickets' }).click();
  await expect(page).toHaveURL(/\/bookings\/51$/);
  await expect(page.getByRole('heading', { name: event.title })).toBeVisible();
  await page.getByRole('button', { name: 'Pay ₹50.00' }).click();
  await expect(page).toHaveURL(/\/tickets$/);
  await expect(page.getByText('TKT-BROWSER1')).toBeVisible();
});

test('customer ticket page loads, opens ticket details and shows empty state', async ({ page }) => {
  await setUser(page);
  await page.route('**/api/v1/tickets/my-tickets/', (route) => route.fulfill({
    json: { count: 1, next: null, previous: null, results: [ticket] },
  }));
  await page.route('**/api/v1/tickets/91/', (route) => route.fulfill({ json: ticket }));
  await page.goto('/tickets');
  await expect(page.getByText('TKT-BROWSER1')).toBeVisible();
  await page.goto('/tickets/91');
  await expect(page.getByRole('heading', { name: 'Ticket Details' })).toBeVisible();
  await expect(page.getByText(event.title)).toBeVisible();
  await expect(page.getByText('Ticket number (reference):')).toBeVisible();
  await expect(page.getByLabel('Check-in code')).toBeVisible();
  await expect(page.locator('.ticket-manual-code code')).toHaveText(ticket.ticket_token);

  await page.route('**/api/v1/tickets/my-tickets/', (route) => route.fulfill({
    json: { count: 0, next: null, previous: null, results: [] },
  }));
  await page.goto('/tickets');
  await expect(page.getByText("You haven't booked any tickets yet.")).toBeVisible();
});
