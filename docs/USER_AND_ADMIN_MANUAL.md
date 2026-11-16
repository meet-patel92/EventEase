# User and Admin Manual

## Customer

1. Open the home page and browse available events. Select an event to view its details.
2. Register or sign in using the account credentials. Authentication uses email and password.
3. Start a booking from an eligible event, choose a valid ticket quantity, and continue through payment. In development this flow is configured for Razorpay test mode; use provider test credentials or the local automated mock only.
4. View booking status under Bookings. Ticket pages show issued tickets and provide PDF downloads where available.
5. Present the ticket QR at entry. A successful scan consumes/marks the ticket used; a repeat scan is expected to be rejected.
6. Submit an eligible event review. The backend allows one review per user/event.
7. Open Notifications to view delivery status and read state. Unread notifications are highlighted; choose **Mark as read** on one item or **Mark all as read**. The navigation badge shows your unread count.

## Organizer

Sign in with an ORGANIZER account to see organizer-scoped dashboard data. Open **My Events** to review statuses or start **Create event**. The form supports event details, category selection and an optional poster upload. New events are submitted as PENDING. Use **Edit event** from My Events to update an event you own. Event publication is subject to administrator approval. Organizer scanner access is role guarded on the frontend and must also be permitted by backend authorization.

## Administrator

Sign in with an ADMIN account. The dashboard presents the role-scoped overview. Open **Event approvals** to view pending submissions and expand event details. Approve or enter a rejection reason, then confirm the action. The underlying event approval/rejection endpoints enforce backend permissions. API schema gives request/response definitions. Keep staff account creation and role assignment controlled; do not grant roles through client-side storage.

## Ticket scanner

Open `/ticket-scanner` as ADMIN or ORGANIZER. Scan or submit the ticket identifier using the scanner UI. Use an issued ticket from an isolated test booking for demonstrations. The backend decides whether a ticket is valid and prevents duplicate check-in; the browser route guard is not a replacement for backend authorization.

## Troubleshooting

- If requests fail, confirm Django is listening at the configured API base URL and CORS includes the frontend origin.
- A booking that is not paid/confirmed may not have a valid ticket yet.
- A used, cancelled, unknown, or unauthorized ticket should not be accepted by verification.
- For local test payment issues, confirm the test-mode configuration; never substitute live credentials in test runs.
