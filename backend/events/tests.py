from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from unittest.mock import Mock, patch
from io import StringIO
import tempfile
from pathlib import Path
from PIL import Image
from django.core.management import call_command
from django.test.utils import override_settings
from accounts.models import User
from events.models import EventCategory, Event


class EventAttendanceAPITest(APITestCase):
    def setUp(self):
        self.organizer = User.objects.create_user(
            username="attendance-organizer", email="attendance@example.test",
            password="testpass123", role="ORGANIZER",
        )
        self.other_organizer = User.objects.create_user(
            username="other-organizer", email="other-attendance@example.test",
            password="testpass123", role="ORGANIZER",
        )
        self.event = Event.objects.create(
            title="Attendance Event", description="Attendance report fixture",
            organizer=self.organizer, venue="Main Hall", city="Test City",
            event_date=timezone.now().date() + timedelta(days=30),
            start_time="14:00", end_time="18:00", status=Event.Status.APPROVED,
        )

    def test_owner_can_read_zero_ticket_attendance_report(self):
        self.client.force_authenticate(user=self.organizer)
        response = self.client.get(reverse("event-attendance", kwargs={"pk": self.event.pk}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_paid_tickets"], 0)
        self.assertEqual(response.data["checked_in_tickets"], 0)
        self.assertEqual(response.data["remaining_tickets"], 0)
        self.assertEqual(response.data["attendance_percentage"], 0)

    @patch("tickets.models.Ticket.objects.filter")
    def test_report_counts_only_paid_tickets_and_checkins(self, ticket_filter):
        paid_tickets = Mock()
        paid_tickets.count.return_value = 2
        paid_tickets.filter.return_value.count.return_value = 1
        ticket_filter.return_value = paid_tickets
        self.client.force_authenticate(user=self.organizer)

        response = self.client.get(reverse("event-attendance", kwargs={"pk": self.event.pk}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_paid_tickets"], 2)
        self.assertEqual(response.data["checked_in_tickets"], 1)
        self.assertEqual(response.data["remaining_tickets"], 1)
        self.assertEqual(response.data["attendance_percentage"], 50.0)
        self.assertEqual(ticket_filter.call_args.kwargs["booking__status"], "CONFIRMED")
        self.assertEqual(ticket_filter.call_args.kwargs["payment__status"], "SUCCESS")
        self.assertIs(ticket_filter.call_args.kwargs["payment__signature_verified"], True)
        paid_tickets.filter.assert_called_once_with(status="USED")

    def test_other_organizer_cannot_read_attendance_report(self):
        self.client.force_authenticate(user=self.other_organizer)
        response = self.client.get(reverse("event-attendance", kwargs={"pk": self.event.pk}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class NormalizeEventTitlesAndPostersCommandTest(TestCase):
    def test_apply_is_idempotent_and_preserves_event_identity(self):
        self.media_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.media_directory.cleanup)
        media_override = override_settings(MEDIA_ROOT=self.media_directory.name)
        media_override.enable()
        self.addCleanup(media_override.disable)
        organizer = User.objects.create_user(
            username="poster-organizer", email="poster-organizer@example.test",
            password="Sufficient-Pass-908!", role=User.Role.ORGANIZER,
        )
        category = EventCategory.objects.create(name="Product Design")
        event = Event.objects.create(
            title="[DEMO] [DEMO] Product Design Workshop",
            slug="demo-event-safe-title-update",
            description="Command safety fixture", category=category,
            organizer=organizer, venue="Studio", city="Test City",
            event_date=timezone.now().date() + timedelta(days=30),
            start_time="10:00", end_time="12:00", status=Event.Status.APPROVED,
        )
        event_id = event.pk

        call_command("normalize_event_titles_and_posters", apply=True, stdout=StringIO())
        event.refresh_from_db()
        first_poster_name = event.poster.name
        self.assertEqual(event.title, "Product Design Workshop")
        self.assertEqual(event.slug, "demo-event-safe-title-update")
        self.assertEqual(event.pk, event_id)
        self.assertTrue(event.poster.storage.exists(first_poster_name))
        with event.poster.storage.open(first_poster_name, "rb") as poster_file:
            poster = Image.open(poster_file)
            self.assertEqual(poster.format, "JPEG")
            self.assertEqual(poster.size, (1200, 675))

        call_command("normalize_event_titles_and_posters", apply=True, stdout=StringIO())
        event.refresh_from_db()
        self.assertEqual(event.pk, event_id)
        self.assertEqual(event.title, "Product Design Workshop")
        self.assertEqual(event.poster.name, first_poster_name)
        self.assertEqual(len(list((Path(self.media_directory.name) / "event_posters").glob("*.jpg"))), 1)

class EventCategoryAPITest(APITestCase):
    """Tests for event category API endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.admin_user = User.objects.create_user(
            username="admin",
            email="admin@test.com",
            password="testpass123",
            role="ADMIN",
        )
        self.organizer_user = User.objects.create_user(
            username="organizer",
            email="organizer@test.com",
            password="testpass123",
            role="ORGANIZER",
        )
        self.customer_user = User.objects.create_user(
            username="customer",
            email="customer@test.com",
            password="testpass123",
            role="CUSTOMER",
        )
        self.category, _ = EventCategory.objects.get_or_create(
            name="Music", defaults={"description": "Music events"}
        )

    def test_admin_can_create_category(self):
        """Admin can create event categories."""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("eventcategory-list")
        data = {"name": "Stage & Performance", "description": "Stage events"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "Stage & Performance")

    def test_organizer_cannot_create_category(self):
        """Organizer cannot create event categories."""
        self.client.force_authenticate(user=self.organizer_user)
        url = reverse("eventcategory-list")
        data = {"name": "Sports", "description": "Sports events"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_customer_cannot_create_category(self):
        """Customer cannot create event categories."""
        self.client.force_authenticate(user=self.customer_user)
        url = reverse("eventcategory-list")
        data = {"name": "Sports", "description": "Sports events"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_duplicate_category_name_rejected(self):
        """Duplicate category names are rejected."""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("eventcategory-list")
        data = {"name": "Music", "description": "Duplicate"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unauthenticated_can_list_categories(self):
        """Unauthenticated users can list categories."""
        url = reverse("eventcategory-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_default_categories_are_available_without_duplicates(self):
        expected = {
            "Technology", "Business", "Education", "Music", "Arts & Culture",
            "Sports", "Health & Wellness", "Food & Drink", "Networking", "Community", "Other",
        }
        response = self.client.get(reverse("eventcategory-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = {item["name"] for item in response.data["results"]}
        self.assertTrue(expected.issubset(names))
        self.assertEqual(len(names), len({name.casefold() for name in names}))
        self.assertEqual(EventCategory.objects.filter(name__iexact="Music").count(), 1)


class EventCreationAPITest(APITestCase):
    """Tests for event creation by organizers."""

    def setUp(self):
        self.client = APIClient()
        self.admin_user = User.objects.create_user(
            username="admin",
            email="admin@test.com",
            password="testpass123",
            role="ADMIN",
        )
        self.organizer_user = User.objects.create_user(
            username="organizer",
            email="organizer@test.com",
            password="testpass123",
            role="ORGANIZER",
        )
        self.customer_user = User.objects.create_user(
            username="customer",
            email="customer@test.com",
            password="testpass123",
            role="CUSTOMER",
        )
        self.category, _ = EventCategory.objects.get_or_create(
            name="Music", defaults={"description": "Music events"}
        )
        self.event_data = {
            "title": "Test Concert",
            "description": "A test concert event",
            "category": self.category.id,
            "venue": "Test Venue",
            "city": "Test City",
            "event_date": (timezone.now().date() + timedelta(days=30)).isoformat(),
            "start_time": "14:00:00",
            "end_time": "18:00:00",
            "registration_deadline": (
                timezone.now() + timedelta(days=25)
            ).isoformat(),
            "ticket_price": "25.00",
            "total_tickets": 100,
            "available_tickets": 100,
        }

    def test_organizer_can_create_event(self):
        """Organizer can create events."""
        self.client.force_authenticate(user=self.organizer_user)
        url = reverse("event-list")
        response = self.client.post(url, self.event_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["title"], "Test Concert")
        self.assertEqual(response.data["organizer"], self.organizer_user.id)
        self.assertEqual(response.data["status"], "PENDING")
        self.assertEqual(response.data["category"], self.category.id)
        self.assertEqual(Event.objects.get(pk=response.data["id"]).category_id, self.category.id)

    def test_customer_cannot_create_event(self):
        """Customer cannot create events."""
        self.client.force_authenticate(user=self.customer_user)
        url = reverse("event-list")
        response = self.client.post(url, self.event_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_cannot_create_event(self):
        """Unauthenticated users cannot create events."""
        url = reverse("event-list")
        response = self.client.post(url, self.event_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_event_date_cannot_be_in_past(self):
        """Event date cannot be in the past."""
        self.client.force_authenticate(user=self.organizer_user)
        url = reverse("event-list")
        data = self.event_data.copy()
        data["event_date"] = (timezone.now().date() - timedelta(days=1)).isoformat()
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_end_time_must_be_after_start_time(self):
        """End time must be later than start time."""
        self.client.force_authenticate(user=self.organizer_user)
        url = reverse("event-list")
        data = self.event_data.copy()
        data["start_time"] = "18:00:00"
        data["end_time"] = "14:00:00"
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_registration_deadline_cannot_be_after_event_date(self):
        """Registration deadline cannot be after event date."""
        self.client.force_authenticate(user=self.organizer_user)
        url = reverse("event-list")
        data = self.event_data.copy()
        data["registration_deadline"] = (
            timezone.now() + timedelta(days=35)
        ).isoformat()
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_ticket_price_cannot_be_negative(self):
        """Ticket price cannot be negative."""
        self.client.force_authenticate(user=self.organizer_user)
        url = reverse("event-list")
        data = self.event_data.copy()
        data["ticket_price"] = "-10.00"
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_total_tickets_must_be_greater_than_zero(self):
        """Total tickets must be greater than zero."""
        self.client.force_authenticate(user=self.organizer_user)
        url = reverse("event-list")
        data = self.event_data.copy()
        data["total_tickets"] = 0
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_available_tickets_cannot_exceed_total(self):
        """Available tickets cannot exceed total tickets."""
        self.client.force_authenticate(user=self.organizer_user)
        url = reverse("event-list")
        data = self.event_data.copy()
        data["total_tickets"] = 50
        data["available_tickets"] = 100
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_organizer_is_set_from_request_not_client(self):
        """Organizer is always set from authenticated user, not client data."""
        self.client.force_authenticate(user=self.organizer_user)
        url = reverse("event-list")
        data = self.event_data.copy()
        data["organizer"] = self.admin_user.id  # Try to set different organizer
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["organizer"], self.organizer_user.id)


class EventOwnershipAPITest(APITestCase):
    """Tests for event ownership restrictions."""

    def setUp(self):
        self.client = APIClient()
        self.admin_user = User.objects.create_user(
            username="admin",
            email="admin@test.com",
            password="testpass123",
            role="ADMIN",
        )
        self.organizer_user = User.objects.create_user(
            username="organizer",
            email="organizer@test.com",
            password="testpass123",
            role="ORGANIZER",
        )
        self.customer_user = User.objects.create_user(
            username="customer",
            email="customer@test.com",
            password="testpass123",
            role="CUSTOMER",
        )
        self.other_organizer = User.objects.create_user(
            username="other_org",
            email="other@test.com",
            password="testpass123",
            role="ORGANIZER",
        )
        self.category, _ = EventCategory.objects.get_or_create(
            name="Music", defaults={"description": "Music events"}
        )
        self.event = Event.objects.create(
            title="Organizer Event",
            description="An organizer event",
            category=self.category,
            organizer=self.organizer_user,
            venue="Test Venue",
            city="Test City",
            event_date=timezone.now().date() + timedelta(days=30),
            start_time="14:00:00",
            end_time="18:00:00",
            ticket_price=25.00,
            total_tickets=100,
            available_tickets=100,
            status="PENDING",
        )

    def test_organizer_can_edit_own_event(self):
        """Organizer can edit their own events."""
        self.client.force_authenticate(user=self.organizer_user)
        url = reverse("event-detail", kwargs={"pk": self.event.id})
        new_category = EventCategory.objects.get(name="Technology")
        data = {"title": "Updated Event Title", "category": new_category.id}
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], "Updated Event Title")
        self.assertEqual(response.data["category"], new_category.id)
        self.event.refresh_from_db()
        self.assertEqual(self.event.category_id, new_category.id)

    def test_organizer_cannot_edit_another_organizers_event(self):
        """Organizer cannot edit another organizer's events (404 - not found)."""
        self.client.force_authenticate(user=self.other_organizer)
        url = reverse("event-detail", kwargs={"pk": self.event.id})
        data = {"title": "Hacked Title"}
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_customer_cannot_edit_event(self):
        """Customer cannot edit events (404 - not visible to customers)."""
        self.client.force_authenticate(user=self.customer_user)
        url = reverse("event-detail", kwargs={"pk": self.event.id})
        data = {"title": "Hacked Title"}
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_organizer_can_delete_own_pending_event(self):
        """Organizer can delete their own PENDING events."""
        self.client.force_authenticate(user=self.organizer_user)
        url = reverse("event-detail", kwargs={"pk": self.event.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_organizer_cannot_delete_approved_event(self):
        """Organizer cannot delete APPROVED events."""
        self.event.status = "APPROVED"
        self.event.save()
        self.client.force_authenticate(user=self.organizer_user)
        url = reverse("event-detail", kwargs={"pk": self.event.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class EventApprovalAPITest(APITestCase):
    """Tests for admin approval and rejection."""

    def setUp(self):
        self.client = APIClient()
        self.admin_user = User.objects.create_user(
            username="admin",
            email="admin@test.com",
            password="testpass123",
            role="ADMIN",
        )
        self.organizer_user = User.objects.create_user(
            username="organizer",
            email="organizer@test.com",
            password="testpass123",
            role="ORGANIZER",
        )
        self.customer_user = User.objects.create_user(
            username="customer",
            email="customer@test.com",
            password="testpass123",
            role="CUSTOMER",
        )
        self.category, _ = EventCategory.objects.get_or_create(
            name="Music", defaults={"description": "Music events"}
        )
        self.event = Event.objects.create(
            title="Pending Event",
            description="A pending event",
            category=self.category,
            organizer=self.organizer_user,
            venue="Test Venue",
            city="Test City",
            event_date=timezone.now().date() + timedelta(days=30),
            start_time="14:00:00",
            end_time="18:00:00",
            ticket_price=25.00,
            total_tickets=100,
            available_tickets=100,
            status="PENDING",
        )

    def test_admin_can_approve_event(self):
        """Admin can approve pending events."""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("event-approve", kwargs={"pk": self.event.id})
        response = self.client.patch(url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.event.refresh_from_db()
        self.assertEqual(self.event.status, "APPROVED")

    def test_admin_can_reject_event(self):
        """Admin can reject pending events with a reason."""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("event-reject", kwargs={"pk": self.event.id})
        data = {"status": "REJECTED", "rejection_reason": "Not suitable"}
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.event.refresh_from_db()
        self.assertEqual(self.event.status, "REJECTED")
        self.assertEqual(self.event.rejection_reason, "Not suitable")

    def test_organizer_cannot_approve_event(self):
        """Organizer cannot approve events."""
        self.client.force_authenticate(user=self.organizer_user)
        url = reverse("event-approve", kwargs={"pk": self.event.id})
        response = self.client.patch(url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_customer_cannot_approve_event(self):
        """Customer cannot approve events."""
        self.client.force_authenticate(user=self.customer_user)
        url = reverse("event-approve", kwargs={"pk": self.event.id})
        response = self.client.patch(url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_reject_without_reason_fails(self):
        """Rejecting without a reason fails."""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("event-reject", kwargs={"pk": self.event.id})
        data = {"status": "REJECTED"}
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_approve_non_pending_event(self):
        """Only PENDING events can be approved/rejected."""
        self.event.status = "APPROVED"
        self.event.save()
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("event-approve", kwargs={"pk": self.event.id})
        response = self.client.patch(url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class EventVisibilityAPITest(APITestCase):
    """Tests for approved event visibility."""

    def setUp(self):
        self.client = APIClient()
        self.admin_user = User.objects.create_user(
            username="admin",
            email="admin@test.com",
            password="testpass123",
            role="ADMIN",
        )
        self.organizer_user = User.objects.create_user(
            username="organizer",
            email="organizer@test.com",
            password="testpass123",
            role="ORGANIZER",
        )
        self.customer_user = User.objects.create_user(
            username="customer",
            email="customer@test.com",
            password="testpass123",
            role="CUSTOMER",
        )
        self.category, _ = EventCategory.objects.get_or_create(
            name="Music", defaults={"description": "Music events"}
        )
        self.approved_event = Event.objects.create(
            title="Approved Event",
            description="An approved event",
            category=self.category,
            organizer=self.organizer_user,
            venue="Test Venue",
            city="Test City",
            event_date=timezone.now().date() + timedelta(days=30),
            start_time="14:00:00",
            end_time="18:00:00",
            ticket_price=25.00,
            total_tickets=100,
            available_tickets=100,
            status="APPROVED",
        )
        self.pending_event = Event.objects.create(
            title="Pending Event",
            description="A pending event",
            category=self.category,
            organizer=self.organizer_user,
            venue="Test Venue",
            city="Test City",
            event_date=timezone.now().date() + timedelta(days=30),
            start_time="14:00:00",
            end_time="18:00:00",
            ticket_price=25.00,
            total_tickets=100,
            available_tickets=100,
            status="PENDING",
        )

    def test_customer_can_view_approved_events(self):
        """Customer can view only approved events."""
        self.client.force_authenticate(user=self.customer_user)
        url = reverse("event-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"]
        event_ids = [e["id"] for e in results]
        self.assertIn(self.approved_event.id, event_ids)
        self.assertNotIn(self.pending_event.id, event_ids)

    def test_unauthenticated_can_view_approved_events(self):
        """Unauthenticated users can view approved events."""
        url = reverse("event-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"]
        event_ids = [e["id"] for e in results]
        self.assertIn(self.approved_event.id, event_ids)
        self.assertNotIn(self.pending_event.id, event_ids)

    def test_admin_can_view_all_events(self):
        """Admin can view all events."""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("event-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"]
        event_ids = [e["id"] for e in results]
        self.assertIn(self.approved_event.id, event_ids)
        self.assertIn(self.pending_event.id, event_ids)

    def test_organizer_can_view_own_and_approved_events(self):
        """Organizer can view their own events + approved events."""
        self.client.force_authenticate(user=self.organizer_user)
        url = reverse("event-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"]
        event_ids = [e["id"] for e in results]
        self.assertIn(self.approved_event.id, event_ids)
        self.assertIn(self.pending_event.id, event_ids)

    def test_event_search_by_title(self):
        """Search events by title."""
        url = reverse("event-list")
        response = self.client.get(url, {"search": "Approved"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Approved Event")

    def test_event_filter_by_city(self):
        """Filter events by city."""
        url = reverse("event-list")
        response = self.client.get(url, {"city": "Test City"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_event_ordering_by_date(self):
        """Sort events by date."""
        url = reverse("event-list")
        response = self.client.get(url, {"ordering": "event_date"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_organizer_my_events(self):
        """Organizer can view their own events."""
        self.client.force_authenticate(user=self.organizer_user)
        url = reverse("event-my-events")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"]
        for event in results:
            self.assertEqual(event["organizer"], self.organizer_user.id)

    def test_customer_cannot_access_my_events(self):
        """Customer cannot access my-events endpoint."""
        self.client.force_authenticate(user=self.customer_user)
        url = reverse("event-my-events")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
