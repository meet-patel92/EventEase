# EventEase Project Documentation

## 1. Project introduction

EventEase is a web-based event management and ticket booking system. It provides public event discovery, role-aware event administration, booking and payment workflows, digital tickets, ticket verification, reviews, notifications and dashboards. Its implementation is split between a Django REST API and a React single page application.

## 2. Problem statement

Event information, registration, ticket issuance and attendee validation can be fragmented across separate manual processes. This increases administrative effort and makes it harder for attendees to find event details, retain ticket information and prove entry. Event organizers and administrators also need workflows to manage event publication and inspect operational summaries.

## 3. Objectives and scope

Objectives are to provide a centralized event catalogue, support distinct administrator/organizer/customer roles, manage event approval, accept bookings, integrate a payment provider in test mode, issue QR tickets, validate ticket use, and provide reviews, notifications and role-scoped summary data.

The scope is the current web application and its APIs. Live Razorpay processing, production deployment, and operational guarantees such as high availability are outside the verified implementation scope.

## 4. Existing and proposed system

In a manual process, event details, attendee lists, payment confirmation and entry checks may be handled in separate tools. EventEase proposes a shared web application with a Django API and relational persistence, a React client, JWT-based API authentication, event approval, booking/payment records, QR ticketing and scanner verification. It reduces duplicated workflow effort while keeping roles and status transitions explicit in the application.

## 5. Hardware and software requirements

### Development baseline

- Windows 10/11 workstation, 64-bit, with internet access for dependency installation.
- Recommended: 4 CPU cores, 8 GB RAM, and 5 GB free space for Python/Node dependencies and browser tests. These are practical development recommendations, not benchmarked minimums.
- Python 3.12; Django 5.2.x; MySQL 8.x compatible server; Node.js/npm compatible with Vite 8; Chrome for Playwright.
- The Playwright suite uses a per-run SQLite database and local media directory, separately from the configured MySQL database.

## 6. Technology stack

| Layer | Technologies observed in the project |
|---|---|
| Backend | Python 3.12, Django 5.2, Django REST Framework, SimpleJWT, drf-spectacular |
| Persistence | MySQL for normal application configuration; SQLite for isolated browser E2E runs |
| Frontend | React 19, React Router 7, Vite 8, Axios, Bootstrap, Lucide React, Recharts |
| Ticket/payment support | Razorpay SDK in test-mode flow, qrcode, Pillow, ReportLab |
| Testing | Django tests, Playwright browser tests, ESLint, Vite production build |

Exact package constraints are maintained in `backend/requirements.txt` and `frontend/package.json` / `frontend/package-lock.json`.

## 7. System architecture

The browser loads the React application from Vite in development or a built static asset set in a future deployment. The client calls `/api/v1` endpoints through Axios. Django REST Framework applies JWT authentication and view/serializer validation, uses Django ORM models backed by MySQL in normal operation, and provides OpenAPI through drf-spectacular. Ticket services create QR images and PDF responses. Razorpay order/signature integration is configured for test mode. The actual production hosting topology is not established.

See [DIAGRAMS.md](DIAGRAMS.md).

## 8. Module description

- **Accounts:** custom user, registration, login, logout/profile, role fields and JWT authentication.
- **Events:** event categories, event CRUD/list/detail, organizer-owned events, and approval/rejection status actions.
- **Bookings:** customer bookings, quantity/amount snapshots, cancellation and booking references.
- **Payments:** payment/order records and Razorpay test-mode order/signature verification flow.
- **Tickets:** QR-backed ticket records, PDF downloads, scanner verification and used-ticket prevention.
- **Reviews:** event ratings and text, event filtering, validation, unique user/event review constraint.
- **Notifications:** user-scoped notification list/detail with delivery type/status, read/unread state, individual and bulk mark-as-read actions, and an unread-count endpoint used by the navigation badge.
- **Dashboard:** role-scoped aggregate overview; legacy dashboard stats endpoint is admin-managed.
- **Frontend:** public event catalogue/detail plus login/registration, organizer event creation/editing/status views, admin pending-event review and decision confirmation, booking, payment, dashboard, ticket, scanner, notification and review views.

## 9. Functional and non-functional requirements

### Functional requirements represented in code

Users can register/login, browse events, and access authenticated features according to role/ownership checks. Organizers manage their events; admins review event status. Customers can create/cancel bookings, use payment endpoints, access tickets, submit reviews for eligible events, and view their notifications/dashboard. Authorized scanner users can validate tickets. API schema is served in OpenAPI, Swagger UI and Redoc.

### Non-functional considerations

The application separates client and API layers, uses database constraints for important uniqueness rules, validates request data through serializers, uses JWT for API authentication, and includes automated backend/browser checks. Deployment security, backup monitoring, performance under production load, accessibility certification, disaster recovery and uptime have not been independently certified.

## 10. Database design

The custom `accounts.User` is the identity entity (`USERNAME_FIELD=email`) with ADMIN, ORGANIZER and CUSTOMER roles. Event categories may be attached to events; each event belongs to its organizer. Bookings reference a customer and event. A booking may have multiple payment rows (the model does not enforce one-to-one). Ticket records reference booking/payment/customer/event where supplied. Reviews link a user and event and enforce one review per user/event. Notifications belong to a user. DashboardStat is a standalone persisted statistic record; role overview values are aggregated from application data.

See the ER diagram in [DIAGRAMS.md](DIAGRAMS.md). Relationship lines there reflect model foreign keys and the optional category/ticket references; they do not assert undocumented business cardinalities.

## 11. Authentication and role management

The custom user model authenticates by email. The REST framework is configured for SimpleJWT bearer tokens, and authenticated access is the default unless a view overrides permissions. Roles include ADMIN, ORGANIZER and CUSTOMER. API permissions and ownership checks are the security boundary; frontend route guards improve navigation but do not replace backend authorization. The ticket-scanner frontend route permits ADMIN and ORGANIZER in the current route configuration; backend verification permissions must remain authoritative. Do not treat role labels stored client-side as trusted authorization.

## 12. Limitations and future enhancements

- Razorpay backend integration is restricted to test-mode keys; live payment support needs provider configuration, webhook/reconciliation design and security review.
- Notification read/unread state is available per account; delivery through production email/SMS providers still needs provider setup.
- Email backend is console-oriented in development; production email/SMS delivery needs provider setup.
- Production static/media storage and serving, HTTPS, observability, deployment automation and backup restore drills need configuration.
- Future work may add production provider adapters, richer audit trails, accessibility and load testing.

## 13. Conclusion and references

EventEase implements a role-aware event discovery, booking and ticket lifecycle with API and web clients. Its current verified boundaries and remaining work are summarized in [FINAL_PROJECT_REPORT.md](FINAL_PROJECT_REPORT.md).

References: Django documentation (https://docs.djangoproject.com/), Django REST Framework (https://www.django-rest-framework.org/), drf-spectacular (https://drf-spectacular.readthedocs.io/), React (https://react.dev/), Vite (https://vite.dev/), Playwright (https://playwright.dev/), MySQL (https://dev.mysql.com/doc/). These are framework references, not claims of external certification.
