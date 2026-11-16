"""Settings for browser integration tests; never connect to the project MySQL DB."""

import os
from pathlib import Path

from .settings import *  # noqa: F403


DATABASES = {  # noqa: F405
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.environ["EVENTEASE_E2E_DB_PATH"],
    }
}
MEDIA_ROOT = Path(os.environ["EVENTEASE_E2E_MEDIA_DIR"])

CORS_ALLOWED_ORIGINS = ["http://127.0.0.1:5174", "http://localhost:5174"]
RAZORPAY_KEY_ID = "rzp_test_local_mock"
RAZORPAY_KEY_SECRET = "local_browser_test_mock_secret"
