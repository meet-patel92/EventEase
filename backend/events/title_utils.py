"""Helpers for event names shown to people."""

import re


def display_event_title(value):
    return re.sub(r"^(?:\[DEMO\]\s*)+", "", value or "", flags=re.IGNORECASE)
