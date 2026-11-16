import os
import sys
from datetime import timedelta
from pathlib import Path

os.environ["DJANGO_SETTINGS_MODULE"] = "config.e2e_settings"

backend_dir = Path(__file__).resolve().parents[2] / "backend"
project_test_results = Path(__file__).resolve().parents[1] / "test-results"
database_path = Path(os.environ["EVENTEASE_E2E_DB_PATH"]).resolve()
media_path = Path(os.environ["EVENTEASE_E2E_MEDIA_DIR"]).resolve()
run_id = database_path.stem.removeprefix("eventease-")
if (
    database_path.suffix != ".sqlite3"
    or database_path.parent != project_test_results.resolve()
    or not run_id
    or media_path.parent != project_test_results.resolve()
    or media_path.name != f"media-{run_id}"
):
    raise RuntimeError("Playwright requires a unique SQLite database and matching media directory under frontend/test-results.")

os.chdir(backend_dir)
sys.path.insert(0, str(backend_dir))
media_path.mkdir(parents=True, exist_ok=True)

import django  # noqa: E402

django.setup()

from django.conf import settings  # noqa: E402

database_config = settings.DATABASES["default"]
if database_config["ENGINE"] != "django.db.backends.sqlite3":
    raise RuntimeError("Refusing to start Playwright backend without SQLite settings.")
if Path(database_config["NAME"]).resolve() != database_path:
    raise RuntimeError("Playwright database setting does not match its unique SQLite path.")
if Path(settings.MEDIA_ROOT).resolve() != media_path:
    raise RuntimeError("Playwright media setting does not match its unique media directory.")

from django.core.management import call_command  # noqa: E402
from django.utils import timezone  # noqa: E402

from accounts.models import User  # noqa: E402
from events.models import Event, EventCategory  # noqa: E402
from notifications.models import Notification  # noqa: E402


call_command("migrate", interactive=False, verbosity=0)

customer, _ = User.objects.get_or_create(
    email="browser.customer@example.test",
    defaults={"username": "browser-customer", "role": User.Role.CUSTOMER},
)
customer.set_password("browser-test-password-123")
customer.save(update_fields=["password"])

organizer, _ = User.objects.get_or_create(
    email="browser.organizer@example.test",
    defaults={"username": "browser-organizer", "role": User.Role.ORGANIZER},
)
organizer.set_password("browser-organizer-password-123")
organizer.save(update_fields=["password"])

admin, _ = User.objects.get_or_create(
    email="browser.admin@example.test",
    defaults={"username": "browser-admin", "role": User.Role.ADMIN},
)
admin.set_password("browser-admin-password-123")
admin.save(update_fields=["password"])

category, _ = EventCategory.objects.get_or_create(
    name="Browser QA Category", defaults={"description": "Isolated browser test category."}
)
Event.objects.get_or_create(
    slug="browser-qa-event",
    defaults={
        "title": "Browser QA Event",
        "description": "Event seeded in a separate SQLite browser test database.",
        "category": category,
        "organizer": organizer,
        "venue": "QA Test Hall",
        "city": "Test City",
        "event_date": timezone.localdate() + timedelta(days=30),
        "start_time": "14:00",
        "end_time": "18:00",
        "ticket_price": "25.00",
        "total_tickets": 10,
        "available_tickets": 10,
        "status": Event.Status.APPROVED,
    },
)
Notification.objects.get_or_create(
    user=customer,
    title="Browser QA notification",
    defaults={
        "message": "This notification belongs to the isolated browser test account.",
        "type": Notification.Type.EMAIL,
        "status": Notification.Status.SENT,
        "sent_at": timezone.now(),
    },
)


print(
    f"Starting Django with SQLite at {database_path} and isolated media at {media_path}.",
    flush=True,
)
call_command("runserver", "127.0.0.1:8765", use_reloader=False, verbosity=1)
