# MCA Submission Screenshot Checklist

Capture screenshots from a running local environment using synthetic accounts and data. No screenshots are fabricated by this document. Hide browser password managers, tokens, private email/address details, environment values, and real payment identifiers before submission. Use a test-mode payment or show the safe mock flow.

| Page / screenshot | Purpose and suggested evidence |
|---|---|
| Home page | EventEase identity, navigation, event catalogue and public browsing state |
| Registration | Account creation fields and validation; use a synthetic account |
| Login | Email/password sign-in form and successful navigation; do not show the password or token |
| Customer dashboard | Customer role and customer-scoped summary |
| Organizer dashboard | Organizer role and organizer-scoped summary |
| Admin dashboard | Admin role and administration summary |
| Event listing | Public event cards, category/search/filter state if present |
| Event details | Description, venue/date, ticket price/availability and booking entry point |
| Event creation | Show the organizer-only Create Event page, category selection, entered details and optional poster selection using synthetic data |
| Event approval | Show the admin-only pending queue, expanded details, required rejection reason, confirmation, and resulting status using isolated test data |
| Booking and payment | Isolated booking and Razorpay test/mock confirmation; never use real payment details |
| QR ticket and PDF | Issued synthetic ticket QR and downloaded PDF; mask ticket token/identifier as required |
| Ticket scanner | Authorized ADMIN/ORGANIZER scanner page and successful synthetic scan result |
| Reviews | Event review list/form, validation and success state; use synthetic review data |
| Notifications | Notification list and delivery state. Do not claim read/unread UI exists; it is not currently implemented |

For each capture, record browser viewport, application version/commit, test role and whether the evidence is from local integration or the API/admin interface.
