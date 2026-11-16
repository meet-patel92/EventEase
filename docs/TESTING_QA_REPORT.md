# Testing and QA Report

## Notification read/unread feature verification (4 November 2026)

- Backend notification API tests: **8 passed**, including ownership, admin scoping, read status, unread count, mark-one and mark-all behavior. Ran against isolated SQLite with the new migration applied.
- Playwright suite: **22 passed**, including notification visual state and navigation unread count; isolated SQLite backend and local payment mock.
- Frontend lint and production build passed. Django system check reported no issues, and `makemigrations --check --dry-run` reported no changes.
- The new `notifications.0002_notification_is_read` migration adds `is_read` with a default of `False`; existing rows retain their content and start unread. It was applied to `eventease_db` after a read-only pre-migration snapshot. Post-migration, all 10 existing notification rows matched their prior content hash and were unread; migration status shows 0002 applied.

## Recorded verification

Latest backend verification: **125 tests passed** against a fresh, uniquely named MySQL test database (`test_eventease_verify_<run-id>`), in 943.743 seconds. Django removed that test database at teardown, and a read-only schema check confirmed it no longer exists. The earlier temporary-SQLite run had 124 passed and one dashboard revenue string-format assertion failure (`"50.00"` expected, `"50"` returned); the MySQL run passed that same assertion, confirming the observed difference is SQLite-specific. No application database data was selected or changed.

Latest frontend verification: **21 Playwright tests passed** (2.2 minutes) against local React and Django. The browser suite included a real API integration journey using the isolated SQLite test database. Frontend lint/build, Django system check and migration drift check passed. No Razorpay network transaction was used.

## Coverage represented in the recorded run

Backend tests cover existing API/model/service behavior, including authentication/permissions, reviews, notifications, dashboards, booking/payment/ticket flows and duplicate check-in scenarios. The Playwright suite runs a local React app against a local Django backend backed by a unique SQLite database and temporary media directory. It includes browser workflows and safe mocked payment responses. The test config points to ports 5174/8765 and is designed not to connect to configured MySQL. Playwright runs serially because its tests share the same per-run SQLite database.

## Scope and limits

- Passing tests do not establish production deployment, security certification, load capacity or live payment readiness.
- Real Razorpay transactions were not run.
- Production email/SMS delivery was not verified.
- Cross-browser/device and assistive technology coverage is not represented by the Chromium suite.
- Browser tests use isolated fixture data rather than existing MySQL accounts/events.
- Screenshots for academic submission must be captured manually from the running application.

Use the exact commands in [INSTALLATION_AND_SETUP.md](INSTALLATION_AND_SETUP.md) to rerun. The exact dashboard revenue assertion passes against the configured MySQL backend. The alternate SQLite backend formats this aggregate differently. Do not use the application database as a test database. Test output and generated Playwright report are the source of truth for subsequent runs.
