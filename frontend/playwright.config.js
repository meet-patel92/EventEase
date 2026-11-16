import { defineConfig } from '@playwright/test';
import { randomUUID } from 'node:crypto';
import { mkdirSync } from 'node:fs';
import { join, resolve } from 'node:path';
import process from 'node:process';

const testResults = join(process.cwd(), 'test-results');
mkdirSync(testResults, { recursive: true });
const testRunId = randomUUID();
process.env.EVENTEASE_E2E_DB_PATH = join(testResults, `eventease-${testRunId}.sqlite3`);
process.env.EVENTEASE_E2E_MEDIA_DIR = join(testResults, `media-${testRunId}`);
process.env.DJANGO_SETTINGS_MODULE = 'config.e2e_settings';
process.env.VITE_API_BASE_URL = '/api/v1';
process.env.E2E_BACKEND_URL = 'http://127.0.0.1:8765';
const backendPython = resolve(process.cwd(), '..', '.venv', 'Scripts', 'python.exe');

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  // The browser suite shares one per-run SQLite API database; serialize tests
  // to keep write-heavy booking and event-management workflows deterministic.
  workers: 1,
  reporter: 'list',
  timeout: 60_000,
  use: {
    baseURL: 'http://127.0.0.1:5174',
    browserName: 'chromium',
    channel: 'chrome',
    headless: true,
    trace: 'retain-on-failure',
  },
  globalTimeout: 900_000,
  webServer: [
    {
      command: 'npm run dev -- --host 127.0.0.1 --port 5174',
      url: 'http://127.0.0.1:5174',
      reuseExistingServer: false,
      timeout: 30_000,
    },
    {
      command: `"${backendPython}" e2e/start_backend.py`,
      url: 'http://127.0.0.1:8765/api/v1/events/',
      env: { DJANGO_SETTINGS_MODULE: 'config.e2e_settings' },
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
});
