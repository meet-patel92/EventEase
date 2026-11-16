# Deployment Preparation Guide

**Deployment status: not deployed.** These are preparation recommendations, not a completed production configuration. The current settings are development-oriented in important areas and Razorpay is test-mode only.

## Environment variables

See [`../backend/.env.example`](../backend/.env.example). It contains placeholder values only. Production secrets must be injected through the hosting provider's secret manager/environment and never committed. Set `DEBUG=False`, a strong unique `SECRET_KEY`, explicit production `ALLOWED_HOSTS`, production DB connection, exact `CORS_ALLOWED_ORIGINS`, JWT lifetimes as approved, and valid payment provider settings only after a separate live-payment implementation and security review. Current source expects Razorpay test-mode keys; do not assume production payment support.

## Django production settings recommendations

- Enforce `DEBUG=False`, strong secret, explicit hosts, restricted CORS, and HTTPS at the ingress/load balancer.
- Configure `CSRF_TRUSTED_ORIGINS` if admin/session-protected browser origins require it; confirm deployment's proxy SSL settings.
- Set secure session/CSRF cookies, HTTPS redirect, HSTS (after validating TLS), secure content/security headers, and allowed origins for the actual domains.
- Use a dedicated least-privilege database account, encrypted network path where supported, backups, monitoring and restore drills.
- Run `manage.py check --deploy` with production environment values before release and resolve findings.
- Configure structured logs, error reporting, rate limits, operational health checks and secret rotation.

The repository settings do not establish all of these controls; they must be implemented and reviewed for the selected hosting platform.

## React production build

```powershell
Set-Location C:\Users\LENOVO\Documents\EventEase\frontend
$env:VITE_API_BASE_URL = "https://api.example.invalid/api/v1"
npm ci
npm run lint
npm run build
```

The output is `frontend/dist`. Serve it from a static host/CDN with SPA fallback to `index.html`, TLS, and the correct API base at build time. The example host is deliberately non-routable and must be replaced. Do not put secrets in `VITE_*` variables; they are included in client assets.

## Database backup

For an existing MySQL database, coordinate a backup window and verify the target before running a dump. Example (prompts for password; does not include it in command history):

```powershell
mysqldump --host=127.0.0.1 --port=3306 --user=YOUR_DB_USER --single-transaction --routines --triggers eventease_db --result-file=eventease_db_backup.sql
```

Store the backup encrypted with access controls and test restoration into a separate, non-production database. Never use `DROP`, `TRUNCATE`, or a restore-over-production procedure as part of routine setup. MySQL command-line flags can vary by version; have the DBA validate the exact invocation.

## Static and media files

Django currently declares `STATIC_URL`, `STATIC_ROOT`, `MEDIA_URL` and `MEDIA_ROOT`; `collectstatic` is part of deployment preparation. Development URL serving for media is conditional on DEBUG and is not a production media server. Configure a web server/object store for collected static assets and uploaded event media, with access policy, size/type validation, backups, lifecycle and malware review appropriate to the host.

```powershell
Set-Location C:\Users\LENOVO\Documents\EventEase
.\.venv\Scripts\python.exe backend\manage.py collectstatic --noinput
```

Run only after production settings and target paths have been reviewed; this command writes collected files.

## CORS and hosts

Set `ALLOWED_HOSTS` to exact backend DNS names and `CORS_ALLOWED_ORIGINS` to exact trusted frontend origins including scheme. Do not use wildcard origins for authenticated APIs. Configure `CSRF_TRUSTED_ORIGINS` for the actual HTTPS admin origin where required. CORS is not authentication.

## Deployment checklist

- [ ] Select host, DNS, TLS, reverse proxy/static/media services and operational owner.
- [ ] Implement and review production settings; keep `DEBUG=False` and secrets outside source control.
- [ ] Confirm production payment support separately; current verified integration is test mode.
- [ ] Provision least-privilege MySQL and verify migrations against a staging copy first.
- [ ] Back up and test restore; document retention and recovery objectives.
- [ ] Configure CORS, hosts, HTTPS, secure cookies, trusted origins and security headers.
- [ ] Build frontend against production API origin; validate SPA route fallback.
- [ ] Configure static/media persistence and access.
- [ ] Run Django checks, tests, frontend lint/build, E2E in staging and security review.
- [ ] Monitor errors, logs, queues/email integration, DB capacity and payment reconciliation.
- [ ] Deploy with rollback plan and verify smoke tests. No deployment has been performed by this work.
