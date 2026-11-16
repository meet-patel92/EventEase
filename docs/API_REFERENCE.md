# API Reference

The live OpenAPI document is generated at `/api/schema/`. Swagger UI is `/api/schema/swagger-ui/`; Redoc is `/api/schema/redoc/`. The API prefix is `/api/v1/`. Exact serializer fields and permission responses should be checked in the generated schema and the corresponding backend serializers/views because response fields can evolve with source changes.

## Endpoint groups

| Group | Routes | Purpose |
|---|---|---|
| Authentication | `POST /auth/register/`, `POST /auth/login/`, `POST /auth/logout/`, `GET/PATCH /auth/profile/` | Account lifecycle, token login/logout, profile |
| Categories | `/events/categories/` | Category list/detail and role-protected management |
| Events | `/events/`, `/events/{id}/`, `/events/my-events/`, `PATCH /events/{id}/approve/`, `PATCH /events/{id}/reject/` | Public event browsing/detail and organizer/admin workflows |
| Bookings | `/bookings/`, `/bookings/{id}/`, `POST /bookings/{id}/cancel/`, `/bookings/my-bookings/` | Booking lifecycle |
| Payments | `/payments/`, `POST /payments/create-order/`, `POST /payments/verify/`, `/payments/my-payments/` | Payment records, test order and signature verification |
| Tickets | `/tickets/`, `/tickets/my-tickets/`, `POST /tickets/verify/`, `/tickets/{id}/download/`, `/tickets/booking/{booking_id}/download-all/` | Ticket access, PDF download and scanner verification |
| Reviews | `/reviews/` | Review CRUD/list, including `?event={id}` filtering |
| Notifications | `GET /notifications/`, `GET /notifications/{id}/`, `GET /notifications/unread-count/`, `PATCH /notifications/{id}/mark-read/`, `PATCH /notifications/mark-all-read/` | Authenticated, user-scoped notification list/detail, unread count and read actions |
| Dashboard | `GET /dashboard/overview/`, `/dashboard/stats/` | Role-scoped overview and admin stats management |

## Authentication and conventions

Protected endpoints use the SimpleJWT bearer token scheme: `Authorization: Bearer <access-token>`. Do not paste real tokens into reports or screenshots. Django REST Framework pagination is configured with a page size of 20. The default API permission is authenticated; public views may override it. Ownership and role constraints are enforced by backend views/permissions.

## Known contract notes

- Login uses email and password in the current API implementation; refer to schema for exact request/response shape.
- Payment endpoints are for configured Razorpay test-mode credentials; use the local E2E mock for automated testing.
- Notification responses include `is_read` (existing records migrate as unread). `PATCH /notifications/{id}/mark-read/` marks one of the signed-in user's notifications read; `PATCH /notifications/mark-all-read/` marks only that user's unread notifications read. `GET /notifications/unread-count/` returns `{ "unread_count": n }`. Existing clients may continue using the POST aliases for mark actions. Admin accounts are scoped to their own notifications as well.
- Review uniqueness is per user/event; duplicates should be handled as validation errors while the database unique constraint remains.
- Binary ticket downloads return a document response rather than a JSON payload.

## Safe usage

Use synthetic data and test credentials. Do not use customer payment credentials or real Razorpay transactions in development tests. API examples and schema are generated from the running backend; this document intentionally avoids hard-coding serializer fields that may be changed independently.
