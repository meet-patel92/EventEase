# EventEase

EventEase is an event management and online ticket booking application. The repository contains a Django REST Framework backend and a React/Vite single page frontend.

## Current project status

- Backend API, JWT authentication, role-scoped dashboards, event management and approval, bookings, test-mode Razorpay order/signature flows, QR tickets, ticket verification, reviews and user-scoped notification read/unread workflows are implemented.
- The React app includes public event browsing, authentication, organizer event creation/editing/status tracking, admin event approval/rejection, bookings, payment history, dashboards, ticket pages, a ticket scanner, reviews and notifications.
- Razorpay configuration is explicitly test-mode only in the current backend. No production payment processing or deployment is claimed.
- See [`docs/FINAL_PROJECT_REPORT.md`](docs/FINAL_PROJECT_REPORT.md) and the documents under [`docs/`](docs/).

## Requirements

- Windows 10/11 (commands below use PowerShell)
- Python 3.12 and a MySQL server for normal development
- Node.js/npm compatible with the Vite 8 project
- Chrome for the Playwright browser suite

## Local setup

Run from the repository root. These commands do not reset or delete an existing database.

```powershell
Set-Location C:\Users\LENOVO\Documents\EventEase
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
Copy-Item backend\.env.example backend\.env
```

Edit `backend\.env` locally with the MySQL database name, user, password, host and port, a local Django secret, the frontend origin, and matching Razorpay **test-mode** credentials (`RAZORPAY_KEY_ID` beginning with `rzp_test_` plus its `RAZORPAY_KEY_SECRET`). The example values are placeholders; never use `rzp_live_` keys or commit `backend\.env`. If `eventease_db` already exists, retain it and its records. For a new local database only, create an empty database with MySQL using the instructions in [`docs/INSTALLATION_AND_SETUP.md`](docs/INSTALLATION_AND_SETUP.md). Then:

```powershell
.\.venv\Scripts\python.exe backend\manage.py check
.\.venv\Scripts\python.exe backend\manage.py migrate
.\.venv\Scripts\python.exe backend\manage.py createsuperuser
.\.venv\Scripts\python.exe backend\manage.py runserver 127.0.0.1:8000
```

In a second PowerShell window:

```powershell
Set-Location C:\Users\LENOVO\Documents\EventEase\frontend
npm ci
npm run dev
```

Open `http://localhost:5173`. API schema and interactive documentation are at `http://127.0.0.1:8000/api/schema/`, `/api/schema/swagger-ui/`, and `/api/schema/redoc/`.

## Checks and tests

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

**SQLite safety:** Keep `config.e2e_settings` on every Django test/check command and provide unique `EVENTEASE_E2E_DB_PATH` and `EVENTEASE_E2E_MEDIA_DIR` values as above. A plain `manage.py test` uses `config.settings`, whose database engine is MySQL and whose database name comes from `backend/.env`; do not use that plain command when the requirement is isolated SQLite testing.

The Playwright configuration creates a unique SQLite database and matching media directory under `frontend/test-results`, forces `DJANGO_SETTINGS_MODULE=config.e2e_settings`, and starts only local Vite/Django servers. Payment flows use a deterministic local mock and never call Razorpay. Scanner browser tests cover manual ticket-token entry, validation, duplicate check-in, and role authorization. The installed headless Chrome does not expose `BarcodeDetector`, so camera QR decoding is not automated; verify physical camera permission, focus, and QR decoding manually in a supported browser. Keep generated test artifacts when diagnosing failures; tests do not clean up prior run artifacts. See [`docs/TESTING_QA_REPORT.md`](docs/TESTING_QA_REPORT.md) for recorded QA results and limitations.

### Manual camera check

Run the local app on `localhost`, sign in as an Organizer or Admin, and open **Ticket check-in**. Select the event, choose **Start camera scanner**, and allow the browser camera prompt. Hold an issued QR code in view; when it is decoded, its token appears in the token field. Press **Verify and check in** to submit it. Repeat the same token to confirm duplicate check-in is rejected. If camera permission, device access, or QR decoding is unavailable, use the manual token field; actual physical-camera decoding has not been verified in this project environment.

### Razorpay test mode

Automated payment tests use a local deterministic mock and do not test Razorpay checkout. A real Razorpay test-mode checkout remains unverified until genuine `rzp_test_` credentials are configured locally and the provider checkout is deliberately verified. The secret key must remain in the backend environment and must never be placed in `VITE_*` frontend variables or committed files. Do not use live keys for development tests.

## Documentation index

- [Project documentation](docs/PROJECT_DOCUMENTATION.md)
- [API reference](docs/API_REFERENCE.md)
- [System diagrams](docs/DIAGRAMS.md)
- [Screenshot checklist](docs/SCREENSHOT_CHECKLIST.md)
- [Installation and setup](docs/INSTALLATION_AND_SETUP.md)
- [User and admin manuals](docs/USER_AND_ADMIN_MANUAL.md)
- [Deployment preparation](docs/DEPLOYMENT_GUIDE.md)
- [Testing and QA report](docs/TESTING_QA_REPORT.md)
- [Final project report](docs/FINAL_PROJECT_REPORT.md)
