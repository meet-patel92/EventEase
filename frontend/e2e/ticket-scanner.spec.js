import { expect, test } from '@playwright/test';

const localApi = 'http://127.0.0.1:5174/api/v1';
const scannerTicketToken = 'REGRESSION-ONLY-TOKEN';

async function signIn(page, email, password) {
  await page.goto('/login');
  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Password').fill(password);
  const loginResponsePromise = page.waitForResponse((response) => (
    response.url().includes('/api/v1/auth/login/')
    && response.request().method() === 'POST'
  ));
  await page.getByRole('button', { name: 'Sign in' }).click();
  expect((await loginResponsePromise).status()).toBe(200);
  await expect(page).toHaveURL(/\/$/);
}

test('organizer gets a no-ticket hint and the scanner submits the selected event and manual token', async ({ page }) => {
  try {
    await signIn(page, 'browser.customer@example.test', 'browser-test-password-123');
    const customerToken = await page.evaluate(() => localStorage.getItem('token'));

    await page.goto('/ticket-scanner');
    await expect(page.getByRole('heading', { name: 'Access denied' })).toBeVisible();
    const customerCheckIn = await page.request.post(`${localApi}/tickets/verify/`, {
      headers: { Authorization: `Bearer ${customerToken}` },
      data: { ticket_token: scannerTicketToken, event_id: 1 },
    });
    expect(customerCheckIn.status()).toBe(403);

    await signIn(page, 'browser.organizer@example.test', 'browser-organizer-password-123');
    await page.goto('/ticket-scanner');
    const organizerToken = await page.evaluate(() => localStorage.getItem('token'));
    const eventsResponse = await page.request.get(`${localApi}/events/my-events/`, {
      headers: { Authorization: `Bearer ${organizerToken}` },
    });
    expect(eventsResponse.status()).toBe(200);
    const organizerEvents = (await eventsResponse.json()).results;
    const cameraEvent = organizerEvents.find((event) => event.title === 'Browser QA Event');
    expect(cameraEvent).toBeTruthy();
    await page.getByLabel('Event').selectOption(String(cameraEvent.id));
    await expect(page.getByRole('status')).toContainText('No paid tickets have been issued');

    const missingTicket = await page.request.post(`${localApi}/tickets/verify/`, {
      headers: { Authorization: `Bearer ${organizerToken}` },
      data: { ticket_token: scannerTicketToken, event_id: cameraEvent.id },
    });
    expect(missingTicket.status()).toBe(404);

    let verificationCount = 0;
    await page.route('**/api/v1/tickets/verify/', async (route) => {
      const payload = route.request().postDataJSON();
      expect(payload).toEqual({ ticket_token: scannerTicketToken, event_id: cameraEvent.id });
      verificationCount += 1;
      if (verificationCount === 1) {
        await route.fulfill({ json: { ticket_number: 'TKT-REGRESSION', event_title: 'Browser QA Event', event_date: '2027-08-20', venue: 'QA Test Hall', ticket_status: 'USED' } });
      } else {
        await route.fulfill({ status: 400, json: { error: 'Ticket is used and cannot be checked in.' } });
      }
    });

    await page.getByLabel('Check-in code').fill(scannerTicketToken);
    await page.getByRole('button', { name: 'Verify and check in' }).click();
    await expect(page.locator('.scanner-result')).toContainText('Ticket checked in');
    await expect(page.locator('.scanner-result')).toContainText('USED');

    await page.getByLabel('Check-in code').fill(scannerTicketToken);
    await page.getByRole('button', { name: 'Verify and check in' }).click();
    await expect(page.getByRole('alert')).toHaveText('Ticket is used and cannot be checked in.');
  } finally {
    await page.goto('about:blank').catch(() => {});
  }
});

test('QR decoder fallback is available when BarcodeDetector is unsupported', async ({ page }) => {
  await page.addInitScript(() => {
    Object.defineProperty(window, 'BarcodeDetector', { configurable: true, value: undefined });
    Object.defineProperty(navigator.mediaDevices, 'getUserMedia', {
      configurable: true,
      value: async () => { throw new DOMException('Camera unavailable', 'NotAllowedError'); },
    });
  });
  await signIn(page, 'browser.organizer@example.test', 'browser-organizer-password-123');
  await page.goto('/ticket-scanner');
  await page.getByRole('button', { name: 'Start camera scanner' }).click();
  await expect(page.getByRole('alert')).toHaveText('Camera access was denied or unavailable. Enter the check-in code manually.');
  await expect(page.getByLabel('Check-in code')).toBeEnabled();
});

test('camera permission or device errors retain the manual token fallback', async ({ page }) => {
  await page.addInitScript(() => {
    window.BarcodeDetector = class {};
    Object.defineProperty(navigator.mediaDevices, 'getUserMedia', {
      configurable: true,
      value: async () => { throw new DOMException('Camera unavailable', 'NotAllowedError'); },
    });
  });
  await signIn(page, 'browser.organizer@example.test', 'browser-organizer-password-123');
  await page.goto('/ticket-scanner');
  await page.getByRole('button', { name: 'Start camera scanner' }).click();
  await expect(page.getByRole('alert')).toHaveText('Camera access was denied or unavailable. Enter the check-in code manually.');
  await expect(page.getByLabel('Check-in code')).toBeEnabled();
});

test('camera tracks stop when the scanner page is left', async ({ page }) => {
  await page.addInitScript(() => {
    window.__cameraTrackStops = 0;
    window.BarcodeDetector = class { async detect() { return []; } };
    Object.defineProperty(HTMLMediaElement.prototype, 'srcObject', {
      configurable: true,
      get() { return null; },
      set() {},
    });
    Object.defineProperty(navigator.mediaDevices, 'getUserMedia', {
      configurable: true,
      value: async () => ({ getTracks: () => [{ stop: () => { window.__cameraTrackStops += 1; } }] }),
    });
  });
  await signIn(page, 'browser.organizer@example.test', 'browser-organizer-password-123');
  await page.goto('/ticket-scanner');
  await page.getByRole('button', { name: 'Start camera scanner' }).click();
  await expect(page.locator('.scanner-video-wrap video')).toBeVisible();
  await page.getByRole('link', { name: 'Home' }).click();
  await expect.poll(() => page.evaluate(() => window.__cameraTrackStops)).toBe(1);
});
