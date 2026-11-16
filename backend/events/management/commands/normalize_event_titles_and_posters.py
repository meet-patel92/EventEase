"""Remove visible demo title labels and fill only genuinely missing posters."""

from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify
from PIL import Image

from events.models import Event
from events.posters import render_poster


class Command(BaseCommand):
    help = "Remove leading [DEMO] labels and assign local posters to events missing one."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Save the listed title and poster updates.")

    def handle(self, *args, **options):
        apply_changes = options["apply"]
        renamed = poster_count = 0
        events = list(Event.objects.select_related("category").order_by("pk"))
        used_poster_names = {
            event.poster.name for event in events if self._poster_is_valid(event)
        }
        self.stdout.write(f"Events inspected: {len(events)}")
        for event in events:
            new_title = event.title
            while new_title.startswith("[DEMO]"):
                new_title = new_title[len("[DEMO]"):].lstrip()
            title_changed = new_title != event.title
            needs_poster = not self._poster_is_valid(event)
            category_name = event.category.name if event.category else "Uncategorized"
            self.stdout.write(f"Event {event.pk}: {event.title!r} [{category_name}]")
            if title_changed or needs_poster:
                self.stdout.write(
                    "  "
                    + (f"title -> {new_title!r}" if title_changed else "title unchanged")
                    + ("; poster missing" if needs_poster else "; existing poster preserved")
                )
            if not apply_changes:
                renamed += int(title_changed)
                poster_count += int(needs_poster)
                continue

            with transaction.atomic():
                if title_changed:
                    event.title = new_title
                update_fields = []
                if title_changed:
                    update_fields.append("title")
                if needs_poster:
                    storage = event.poster.storage
                    candidate = f"event_posters/{slugify(new_title) or f'event-{event.pk}'}.jpg"
                    if storage.exists(candidate) and candidate not in used_poster_names:
                        saved_name = candidate
                    else:
                        asset_name = f"event-{event.pk}-{event.slug or event.pk}.jpg"
                        with TemporaryDirectory(prefix="eventease-poster-") as temp_dir:
                            asset_path = render_poster(
                                new_title,
                                event.category.name if event.category else "",
                                Path(temp_dir) / asset_name,
                                identity=event.pk,
                            )
                            saved_name = storage.save(
                                f"event_posters/{asset_name}", ContentFile(asset_path.read_bytes())
                            )
                    event.poster.name = saved_name
                    used_poster_names.add(saved_name)
                    update_fields.append("poster")
                if update_fields:
                    update_fields.append("updated_at")
                    event.save(update_fields=update_fields)
            renamed += int(title_changed)
            poster_count += int(needs_poster)

        mode = "Applied" if apply_changes else "Dry run"
        self.stdout.write(self.style.SUCCESS(f"{mode}: {renamed} title labels removed; {poster_count} posters assigned."))
        if not apply_changes:
            self.stdout.write("Rerun with --apply to save these changes. Event IDs, relationships, and existing poster files are untouched.")

    @staticmethod
    def _poster_is_valid(event):
        if not event.poster or not event.poster.name or not event.poster.storage.exists(event.poster.name):
            return False
        try:
            with event.poster.storage.open(event.poster.name, "rb") as poster_file:
                image = Image.open(poster_file)
                if image.format not in {"JPEG", "PNG", "WEBP", "GIF"}:
                    return False
                image.verify()
            return True
        except (OSError, ValueError):
            return False
