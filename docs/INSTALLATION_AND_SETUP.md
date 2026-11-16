# Installation and Setup Guide (Windows)

## Prerequisites

Install Python 3.12, Node.js/npm compatible with the lockfile, MySQL Server, Git (if cloning), and Chrome for browser tests. The application dependencies are described by `backend/requirements.txt` and `frontend/package-lock.json`.

## Python environment and backend configuration

```powershell
Set-Location C:\Users\LENOVO\Documents\EventEase
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
Copy-Item backend\.env.example backend\.env
notepad backend\.env
```

Set the local MySQL connection and a strong local-only Django secret in `backend\.env`. Never commit it. If this is a fresh local installation with no database, a MySQL administrator may create the database with `CREATE DATABASE eventease_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;`. Do not run that statement against an existing database. Do not drop, truncate, or reset a database to install the application.

Apply only pending migrations, then run the backend:

```powershell
.\.venv\Scripts\python.exe backend\manage.py check
.\.venv\Scripts\python.exe backend\manage.py migrate
.\.venv\Scripts\python.exe backend\manage.py createsuperuser
.\.venv\Scripts\python.exe backend\manage.py runserver 127.0.0.1:8000
```

The Django administration site is `/admin/`. API schema is `/api/schema/`; Swagger and Redoc are under `/api/schema/swagger-ui/` and `/api/schema/redoc/`.

## Frontend

Open another PowerShell window:

```powershell
Set-Location C:\Users\LENOVO\Documents\EventEase\frontend
npm ci
npm run dev
```

Vite serves the app at `http://localhost:5173`. By default Axios targets `http://localhost:8000/api/v1`; `VITE_API_BASE_URL` can override the API base.

## Tests and build

```powershell
Set-Location C:\Users\LENOVO\Documents\EventEase
$env:EVENTEASE_E2E_DB_PATH = Join-Path $env:TEMP ("eventease-backend-" + [guid]::NewGuid().ToString() + ".sqlite3")
$env:EVENTEASE_E2E_MEDIA_DIR = Join-Path $env:TEMP ("eventease-backend-media-" + [guid]::NewGuid().ToString())
.\.venv\Scripts\python.exe backend\manage.py test --settings=config.e2e_settings
.\.venv\Scripts\python.exe backend\manage.py check --settings=config.e2e_settings
.\.venv\Scripts\python.exe backend\manage.py makemigrations --check --dry-run --settings=config.e2e_settings
Set-Location frontend
npm run lint
npm run build
$env:DJANGO_SETTINGS_MODULE = "config.e2e_settings"
npm run test:e2e
```

**SQLite safety:** Always pass `--settings=config.e2e_settings` and provide unique `EVENTEASE_E2E_DB_PATH` and `EVENTEASE_E2E_MEDIA_DIR` values for Django tests and checks. A plain `manage.py test` selects `config.settings`, which configures MySQL using `backend/.env`; Django may create/use a MySQL test database. Do not use the plain command for SQLite-only testing.

The Playwright configuration forces `DJANGO_SETTINGS_MODULE=config.e2e_settings`, creates a unique SQLite database and matching media directory under `frontend/test-results`, and starts only local Django/Vite servers (ports 8765 and 5174). Razorpay calls are replaced with a deterministic local mock; no real checkout is attempted. Scanner E2E covers manual token entry, check-in, invalid/repeated-token errors, and role restrictions. The installed headless Chrome does not expose `BarcodeDetector`, so automated camera decoding is not claimed. Manually verify physical camera permissions, camera focus, and QR decoding in a browser that supports `BarcodeDetector`. Keep generated database/media/test-result artifacts for diagnosis; the suite does not remove earlier runs.

### Manual camera scanner verification

Run the local app at `http://localhost:5173` and backend at `http://127.0.0.1:8000`. Sign in as an Organizer or Admin, open **Ticket check-in**, select the correct event, and choose **Start camera scanner**. Allow camera permission in the browser. Hold an issued ticket QR code steady in front of the camera. A detected token is placed in the **Ticket token** field; select **Verify and check in** to submit it. Verify the success message and `USED` status, then submit the same token again and verify that the duplicate is rejected. Try a deliberately invalid token and confirm that the not-found error appears. To verify the fallback, deny camera permission or use a browser without `BarcodeDetector`, then enter a known test ticket token manually. Camera decoding with a physical device has not been verified by the automated suite.

### Razorpay status

Automated tests use a local payment mock and do not contact Razorpay. A genuine provider checkout in test mode is not yet verified. Only if you intentionally perform a separate manual test, use genuine Razorpay test credentials (`rzp_test_` key ID and its matching secret) in the backend environment; never put the secret in a frontend variable or use live credentials for development testing. The E2E suite keeps its local mock and must not be used for real payment attempts.
