import { randomUUID } from 'node:crypto';
import { expect, test } from '@playwright/test';

async function fillValidRegistrationForm(page, { username, email }) {
  await page.getByLabel('Username').fill(username);
  await page.getByLabel('Email').fill(email);
  await page.getByLabel('First name').fill('Browser');
  await page.getByLabel('Last name').fill('Customer');
  await page.getByLabel('Password', { exact: true }).fill('Browser-Test-Password-29!');
  await page.getByLabel('Confirm password').fill('Browser-Test-Password-29!');
}

test('customer can register, gets a session and is redirected to events', async ({ page }) => {
  const uniqueId = randomUUID();
  const email = `browser.registration.${uniqueId}@example.test`;
  const username = `registration-${uniqueId}`;
  await page.route('**/api/v1/notifications/unread-count/', (route) => (
    route.fulfill({ json: { unread_count: 0 } })
  ));
  await page.route('**/api/v1/events/', (route) => route.fulfill({
    json: { count: 0, next: null, previous: null, results: [] },
  }));
  await page.goto('/register');
  await fillValidRegistrationForm(page, { username, email });
  const registrationResponsePromise = page.waitForResponse((response) => (
    response.url().includes('/api/v1/auth/register/')
    && response.request().method() === 'POST'
  ));
  await page.getByRole('button', { name: 'Create account' }).click();
  const registrationResponse = await registrationResponsePromise;
  expect(registrationResponse.status()).toBe(201);

  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByText('Welcome', { exact: true })).toBeVisible();
  const session = await page.evaluate(() => ({
    token: localStorage.getItem('token'),
    user: JSON.parse(localStorage.getItem('user') || 'null'),
  }));
  expect(session.token).toBeTruthy();
  expect(session.user).toMatchObject({ username, email, role: 'CUSTOMER' });
});

test('registration requires all required fields before submitting', async ({ page }) => {
  let registrationRequests = 0;
  await page.route('**/api/v1/auth/register/', async (route) => {
    registrationRequests += 1;
    await route.fulfill({ status: 201, json: {} });
  });
  await page.goto('/register');
  await page.getByRole('button', { name: 'Create account' }).click();

  expect(await page.getByLabel('Username').evaluate((input) => input.validity.valueMissing)).toBe(true);
  expect(await page.getByLabel('Email').evaluate((input) => input.validity.valueMissing)).toBe(true);
  expect(registrationRequests).toBe(0);
});

test('registration rejects malformed email and too-short passwords in the browser', async ({ page }) => {
  let registrationRequests = 0;
  await page.route('**/api/v1/auth/register/', async (route) => {
    registrationRequests += 1;
    await route.fulfill({ status: 201, json: {} });
  });
  await page.goto('/register');
  await page.getByLabel('Username').fill('browser-invalid-input');
  await page.getByLabel('Email').fill('not-an-email');
  await page.getByLabel('First name').fill('Browser');
  await page.getByLabel('Last name').fill('Customer');
  await page.getByLabel('Password', { exact: true }).fill('Browser-Test-Password-29!');
  await page.getByLabel('Confirm password').fill('Browser-Test-Password-29!');
  await page.getByRole('button', { name: 'Create account' }).click();
  expect(await page.getByLabel('Email').evaluate((input) => input.validity.typeMismatch)).toBe(true);
  expect(registrationRequests).toBe(0);

  await page.getByLabel('Email').fill('valid.address@example.test');
  await page.getByLabel('Password', { exact: true }).fill('short');
  await page.getByLabel('Confirm password').fill('short');
  await page.getByRole('button', { name: 'Create account' }).click();
  expect(await page.getByLabel('Password', { exact: true }).evaluate((input) => input.validity.tooShort)).toBe(true);
  expect(registrationRequests).toBe(0);
});

test('registration shows a password confirmation error from the server', async ({ page }) => {
  await page.goto('/register');
  await fillValidRegistrationForm(page, {
    username: `password-mismatch-${randomUUID()}`,
    email: `password.mismatch.${randomUUID()}@example.test`,
  });
  await page.getByLabel('Confirm password').fill('A-different-valid-password-78!');

  const registrationResponsePromise = page.waitForResponse((response) => (
    response.url().includes('/api/v1/auth/register/')
    && response.request().method() === 'POST'
  ));
  await page.getByRole('button', { name: 'Create account' }).click();
  const response = await registrationResponsePromise;
  expect(response.status()).toBe(400);
  await expect(page.getByRole('alert')).toContainText('Passwords do not match.');
  expect(await page.evaluate(() => localStorage.getItem('token'))).toBeNull();
});

test('registration reports an email address that is already in use', async ({ page }) => {
  await page.goto('/register');
  await fillValidRegistrationForm(page, {
    username: `duplicate-email-${randomUUID()}`,
    email: 'browser.customer@example.test',
  });

  const registrationResponsePromise = page.waitForResponse((response) => (
    response.url().includes('/api/v1/auth/register/')
    && response.request().method() === 'POST'
  ));
  await page.getByRole('button', { name: 'Create account' }).click();
  const response = await registrationResponsePromise;
  expect(response.status()).toBe(400);
  await expect(page.getByRole('alert')).toContainText(/email/i);
  await expect(page).toHaveURL(/\/register$/);
  expect(await page.evaluate(() => localStorage.getItem('token'))).toBeNull();
});
