"""Safely seed clearly marked EventEase demo data into the configured DB.

By default this command is read-only. Pass --apply only after reviewing the
dry-run plan and confirming that insertion into eventease_db is intended.
"""

from datetime import datetime, time, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.db.models import Sum
from django.utils import timezone

from accounts.models import User
from bookings.models import Booking
from events.models import Event, EventCategory
from notifications.models import Notification
from reviews.models import Review


CATEGORY_SPECS = [
    ("Music & Live Performance", "Concerts, live music, and performances."),
    ("Arts & Culture", "Exhibitions, heritage, and cultural programs."),
    ("Food & Culinary", "Food festivals, tastings, and culinary workshops."),
    ("Technology", "Technology talks, workshops, and product events."),
    ("Sports & Fitness", "Community sports, fitness, and active experiences."),
    ("Business & Networking", "Professional gatherings and networking events."),
    ("Education & Learning", "Classes, workshops, and public lectures."),
    ("Wellness", "Health, wellbeing, and mindful experiences."),
    ("Community", "Neighborhood gatherings and civic programs."),
    ("Film & Media", "Film screenings and media programs."),
]

EVENT_SPECS = [
    {
        "slug": "demo-event-01-city-jazz-evening",
        "title": "City Jazz Evening",
        "category": "Music & Live Performance",
        "description": "An intimate evening of contemporary jazz, local ensembles, and a short post-show conversation with the performers.",
        "venue": "Namma Community Arts Hall",
        "city": "Bengaluru",
        "days": -45,
        "price": "850.00",
        "tickets": 120,
        "status": Event.Status.APPROVED,
    },
    {
        "slug": "demo-event-02-urban-photography-walk",
        "title": "Urban Photography Walk",
        "category": "Arts & Culture",
        "description": "A guided photo walk through historic streets with practical composition tips and a small participant showcase.",
        "venue": "Fort Heritage Courtyard",
        "city": "Mumbai",
        "days": -36,
        "price": "450.00",
        "tickets": 45,
        "status": Event.Status.APPROVED,
    },
    {
        "slug": "demo-event-03-regional-food-festival",
        "title": "Regional Food Festival",
        "category": "Food & Culinary",
        "description": "A family-friendly tasting event featuring independent kitchens, regional recipes, and short chef demonstrations.",
        "venue": "Deccan Community Pavilion",
        "city": "Pune",
        "days": -28,
        "price": "600.00",
        "tickets": 180,
        "status": Event.Status.APPROVED,
    },
    {
        "slug": "demo-event-04-product-design-workshop",
        "title": "Product Design Workshop",
        "category": "Technology",
        "description": "A hands-on workshop on user research, prototyping, and responsible product design for early-career practitioners.",
        "venue": "HITEC Learning Studio",
        "city": "Hyderabad",
        "days": -19,
        "price": "1200.00",
        "tickets": 60,
        "status": Event.Status.APPROVED,
    },
    {
        "slug": "demo-event-05-community-running-clinic",
        "title": "Community Running Clinic",
        "category": "Sports & Fitness",
        "description": "A beginner-friendly running clinic covering warm-ups, pacing, and recovery, followed by a supervised group run.",
        "venue": "Ridgeview Sports Ground",
        "city": "New Delhi",
        "days": -10,
        "price": "300.00",
        "tickets": 90,
        "status": Event.Status.APPROVED,
    },
    {
        "slug": "demo-event-06-founders-networking-forum",
        "title": "Founders Networking Forum",
        "category": "Business & Networking",
        "description": "A structured networking evening for small-business founders with moderated introductions and practical peer sessions.",
        "venue": "Innovation Exchange Centre",
        "city": "Bengaluru",
        "days": 18,
        "price": "950.00",
        "tickets": 100,
        "status": Event.Status.APPROVED,
    },
    {
        "slug": "demo-event-07-public-science-lecture",
        "title": "Public Science Lecture",
        "category": "Education & Learning",
        "description": "An accessible public lecture on climate science with audience questions and a reading list for further learning.",
        "venue": "Seaside Learning Auditorium",
        "city": "Kochi",
        "days": 32,
        "price": "250.00",
        "tickets": 140,
        "status": Event.Status.APPROVED,
    },
    {
        "slug": "demo-event-08-mindful-morning-session",
        "title": "Mindful Morning Session",
        "category": "Wellness",
        "description": "A low-intensity morning session with guided breathing, gentle movement, and practical wellbeing resources.",
        "venue": "Lakeview Wellness Studio",
        "city": "Jaipur",
        "days": 46,
        "price": "400.00",
        "tickets": 55,
        "status": Event.Status.APPROVED,
    },
    {
        "slug": "demo-event-09-neighborhood-ideas-forum",
        "title": "Neighborhood Ideas Forum",
        "category": "Community",
        "description": "A facilitated community forum for sharing local improvement ideas and learning about collaborative civic projects.",
        "venue": "Salt Lake Community Centre",
        "city": "Kolkata",
        "days": 60,
        "price": "150.00",
        "tickets": 80,
        "status": Event.Status.PENDING,
    },
    {
        "slug": "demo-event-10-independent-film-screening",
        "title": "Independent Film Screening",
        "category": "Film & Media",
        "description": "A proposed screening of independent short films followed by a moderated discussion with local media makers.",
        "venue": "Chennai Community Cinema",
        "city": "Chennai",
        "days": 74,
        "price": "500.00",
        "tickets": 70,
        "status": Event.Status.REJECTED,
        "rejection_reason": "Please provide the screening license details.",
    },
]

BOOKING_SPECS = [
    (5, 0, 2),
    (5, 1, 1),
    (6, 0, 1),
    (6, 1, 3),
    (7, 0, 2),
    (7, 1, 1),
    (5, 0, 1),
    (6, 1, 2),
    (7, 0, 1),
    (5, 1, 2),
]


def demo_category_name(label):
    # Demo status belongs to the seeded event records, not the user-facing
    # category name shown throughout the product.
    return label


class Command(BaseCommand):
    help = "Preview or seed clearly marked EventEase dashboard demo data."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Insert missing demo records (requires explicit confirmation).",
        )

    def handle(self, *args, **options):
        database_name = connection.settings_dict.get("NAME")
        if connection.vendor != "mysql" or database_name != "eventease_db":
            raise CommandError(
                "This seed command is restricted to the inspected MySQL database eventease_db."
            )

        accounts = self._existing_accounts()
        existing_counts = self._existing_demo_counts()
        self.stdout.write(f"Target database: {database_name} (MySQL)")
        self.stdout.write(
            "Existing accounts by role: "
            + ", ".join(f"{role}={count}" for role, count in accounts["counts"].items())
        )
        self.stdout.write(
            "Existing marked demo records: "
            + ", ".join(f"{name}={count}" for name, count in existing_counts.items())
        )
        if not options["apply"]:
            self.stdout.write(self.style.WARNING("DRY RUN ONLY; no records were inserted."))
            self.stdout.write("Plan: add up to 10 categories, 10 events, 10 pending bookings, 10 reviews, and 10 pending notifications.")
            self.stdout.write("Event mix: 8 APPROVED (5 completed, 3 upcoming), 1 upcoming PENDING, 1 upcoming REJECTED.")
            self.stdout.write("Bookings: 10 PENDING reservations against approved upcoming demo events; inventory decreases by each reservation quantity.")
            self.stdout.write("Reviews: 10 marked sample reviews on 5 completed approved demo events, split across two existing customers.")
            self.stdout.write("No payments or tickets will be created. Event ID 1 and existing records are never updated or deleted.")
            self.stdout.write("Demo event titles:")
            for spec in EVENT_SPECS:
                self.stdout.write(f"  - {spec['title']} ({spec['status']})")
            return

        created = {"categories": 0, "events": 0, "bookings": 0, "reviews": 0, "notifications": 0}
        with transaction.atomic():
            categories = self._seed_categories(created)
            events = self._seed_events(categories, accounts["organizer"], created)
            self._seed_bookings(events, accounts["customers"], created)
            self._seed_reviews(events, accounts["customers"], created)
            self._seed_notifications(accounts, created)
            self._check_integrity(events)

        self.stdout.write(self.style.SUCCESS("Demo seed completed; integrity checks passed."))
        for module, count in created.items():
            self.stdout.write(f"{module}: created {count}")
        self.stdout.write("payments: created 0")
        self.stdout.write("tickets: created 0")

    def _existing_accounts(self):
        active = User.objects.filter(is_active=True)
        admins = list(active.filter(role=User.Role.ADMIN).order_by("pk")[:1])
        organizers = list(active.filter(role=User.Role.ORGANIZER).order_by("pk")[:1])
        customers = list(active.filter(role=User.Role.CUSTOMER).order_by("pk")[:2])
        counts = {
            role: active.filter(role=role).count()
            for role in (User.Role.ADMIN, User.Role.ORGANIZER, User.Role.CUSTOMER)
        }
        if not admins or not organizers or len(customers) < 2:
            raise CommandError(
                "Demo data requires an active ADMIN, ORGANIZER, and two CUSTOMER accounts. "
                "The command will not create accounts."
            )
        return {"admin": admins[0], "organizer": organizers[0], "customers": customers, "counts": counts}

    def _existing_demo_counts(self):
        return {
            "categories": EventCategory.objects.filter(events__slug__startswith="demo-event-").distinct().count(),
            "events": Event.objects.filter(slug__startswith="demo-event-").count(),
            "bookings": Booking.objects.filter(booking_reference__startswith="DEMO-BK-").count(),
            "reviews": Review.objects.filter(comment__startswith="[DEMO DATA]").count(),
            "notifications": Notification.objects.filter(title__startswith="[DEMO]").count(),
        }

    def _seed_categories(self, created):
        categories = {}
        for label, description in CATEGORY_SPECS:
            name = demo_category_name(label)
            category, was_created = EventCategory.objects.get_or_create(
                name=name,
                defaults={"description": f"{description}"},
            )
            categories[label] = category
            created["categories"] += int(was_created)
        return categories

    def _seed_events(self, categories, organizer, created):
        events = []
        today = timezone.localdate()
        for spec in EVENT_SPECS:
            event_date = today + timedelta(days=spec["days"])
            defaults = {
                "title": spec["title"],
                "description": spec["description"],
                "category": categories[spec["category"]],
                "organizer": organizer,
                "venue": spec["venue"],
                "address": f"{spec['city']} event district",
                "city": spec["city"],
                "event_date": event_date,
                "start_time": time(18, 0),
                "end_time": time(21, 0),
                "registration_deadline": timezone.make_aware(
                    datetime.combine(event_date - timedelta(days=2), time(23, 59))
                ),
                "ticket_price": Decimal(spec["price"]),
                "total_tickets": spec["tickets"],
                "available_tickets": spec["tickets"],
                "status": spec["status"],
                "rejection_reason": spec.get("rejection_reason"),
            }
            event, was_created = Event.objects.get_or_create(
                slug=spec["slug"], defaults=defaults
            )
            if not event.slug.startswith("demo-event-"):
                raise CommandError(
                    f"Refusing to use an event without the reserved demo slug marker: {spec['slug']}."
                )
            events.append(event)
            created["events"] += int(was_created)
        return events

    def _seed_bookings(self, events, customers, created):
        for number, (event_index, customer_index, quantity) in enumerate(BOOKING_SPECS, start=1):
            event = events[event_index]
            customer = customers[customer_index]
            if event.status != Event.Status.APPROVED or event.event_date < timezone.localdate():
                raise CommandError("Demo bookings must reference approved upcoming demo events.")
            reference = f"DEMO-BK-{number:04d}"
            booking = Booking.objects.filter(booking_reference=reference).first()
            if booking:
                if not booking.event.slug.startswith("demo-event-") or booking.customer_id != customer.pk:
                    raise CommandError(f"Refusing to reuse unrelated booking reference {reference}.")
                continue
            event = Event.objects.select_for_update().get(pk=event.pk)
            if event.available_tickets < quantity:
                raise CommandError(f"Not enough inventory for {event.slug}.")
            Booking.objects.create(
                booking_reference=reference,
                customer=customer,
                event=event,
                quantity=quantity,
                unit_price=event.ticket_price,
                total_amount=event.ticket_price * quantity,
                status=Booking.Status.PENDING,
            )
            event.available_tickets -= quantity
            event.save(update_fields=["available_tickets", "updated_at"])
            created["bookings"] += 1

    def _seed_reviews(self, events, customers, created):
        # Five completed approved events × two existing customers = ten unique pairs.
        for event in events[:5]:
            if event.status != Event.Status.APPROVED or event.event_date >= timezone.localdate():
                raise CommandError("Demo review targets must be completed approved events.")
            for customer in customers:
                review = Review.objects.filter(user=customer, event=event).first()
                if review:
                    if not (review.comment or "").startswith("[DEMO DATA]"):
                        raise CommandError(
                            f"A non-demo review already exists for demo event {event.slug}; refusing to overwrite it."
                        )
                    continue
                rating = 5 if (event.pk + customer.pk) % 2 else 4
                Review.objects.create(
                    user=customer,
                    event=event,
                    rating=rating,
                    comment="[DEMO DATA] I enjoyed the event and found the experience well organized.",
                )
                created["reviews"] += 1

    def _seed_notifications(self, accounts, created):
        recipients = [accounts["admin"], accounts["organizer"], *accounts["customers"]]
        notification_specs = [
            ("Event reminder", "Your event is coming up soon. Review the event details in your dashboard.", Notification.Type.EMAIL),
            ("Organizer submission received", "Your event submission is being reviewed.", Notification.Type.PUSH),
            ("Booking awaiting payment", "Your booking is awaiting payment confirmation.", Notification.Type.EMAIL),
            ("Review activity", "New attendee feedback is available for a completed event.", Notification.Type.PUSH),
            ("Event status update", "An event status update is available in My Events.", Notification.Type.EMAIL),
            ("Upcoming event notice", "Your booking is awaiting payment confirmation.", Notification.Type.SMS),
            ("Approval queue update", "An event is waiting in the approval queue.", Notification.Type.PUSH),
            ("Booking reminder", "This booking has no payment or ticket attached yet.", Notification.Type.EMAIL),
            ("Event review summary", "New reviews are available for a completed event.", Notification.Type.PUSH),
            ("Submission decision", "An event submission includes a rejection reason.", Notification.Type.EMAIL),
        ]
        for number, (title, message, notification_type) in enumerate(notification_specs, start=1):
            recipient = recipients[(number - 1) % len(recipients)]
            marked_title = f"[DEMO] {number:02d} {title}"
            notification = Notification.objects.filter(user=recipient, title=marked_title).first()
            if notification:
                if not notification.message.startswith("[DEMO DATA]"):
                    raise CommandError(f"Refusing to reuse unmarked notification {marked_title}.")
                continue
            Notification.objects.create(
                user=recipient,
                title=marked_title,
                message=f"[DEMO DATA] {message}",
                type=notification_type,
                status=Notification.Status.PENDING,
                sent_at=None,
            )
            created["notifications"] += 1

    def _check_integrity(self, events):
        counts = self._existing_demo_counts()
        expected = {"categories": 10, "events": 10, "bookings": 10, "reviews": 10, "notifications": 10}
        if counts != expected:
            raise CommandError(f"Demo record counts do not match the seed plan: {counts}")
        if Event.objects.filter(pk=1).values_list("status", flat=True).first() != Event.Status.APPROVED:
            raise CommandError("Event ID 1 changed unexpectedly; rolling back the seed transaction.")
        for event in events:
            reserved = event.bookings.filter(
                status__in=(Booking.Status.PENDING, Booking.Status.CONFIRMED)
            ).aggregate(total=Sum("quantity"))["total"] or 0
            event.refresh_from_db()
            if event.available_tickets != event.total_tickets - reserved:
                raise CommandError(f"Ticket inventory is inconsistent for demo event {event.slug}.")
        if Review.objects.filter(
            comment__startswith="[DEMO DATA]", event__status=Event.Status.REJECTED
        ).exists():
            raise CommandError("A demo review is linked to a rejected event.")

