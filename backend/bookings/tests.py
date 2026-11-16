from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
import tempfile
from django.test.utils import override_settings
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from accounts.models import User
from events.models import EventCategory, Event
from bookings.models import Booking
from tickets.models import Ticket
from payments.models import Payment


class BookingCreationAPITest(APITestCase):
    """Tests for booking creation."""

    def setUp(self):
        self.media_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.media_directory.cleanup)
        media_override = override_settings(MEDIA_ROOT=self.media_directory.name)
        media_override.enable()
        self.addCleanup(media_override.disable)
        self.client = APIClient()
        self.customer_user = User.objects.create_user(
            username="customer",
            email="customer@test.com",
            password="testpass123",
            role="CUSTOMER",
        )
        self.organizer_user = User.objects.create_user(
            username="organizer",
            email="organizer@test.com",
            password="testpass123",
            role="ORGANIZER",
        )
        self.admin_user = User.objects.create_user(
            username="admin",
            email="admin@test.com",
            password="testpass123",
            role="ADMIN",
        )
        self.category, _ = EventCategory.objects.get_or_create(name="Music", defaults={"description": "Music events"})
        self.event = Event.objects.create(
            title="Test Concert",
            description="A test concert",
            category=self.category,
            organizer=self.organizer_user,
            venue="Test Venue",
            city="Test City",
            event_date=timezone.now().date() + timedelta(days=30),
            start_time="14:00:00",
            end_time="18:00:00",
            registration_deadline=timezone.now() + timedelta(days=25),
            ticket_price=25.00,
            total_tickets=100,
            available_tickets=100,
            status="APPROVED",
        )
        self.booking_data = {
            "event": self.event.id,
            "quantity": 2,
        }

    def test_customer_can_create_booking(self):
        """Customer can create a booking."""
        self.client.force_authenticate(user=self.customer_user)
        url = reverse("booking-list")
        response = self.client.post(url, self.booking_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["quantity"], 2)
        self.assertEqual(response.data["customer"], self.customer_user.id)
        self.assertEqual(response.data["status"], "PENDING")
        self.assertIsNotNone(response.data["booking_reference"])

    def test_new_booking_waits_for_verified_payment_before_ticket_issuance(self):
        self.client.force_authenticate(user=self.customer_user)
        create_response = self.client.post(
            reverse("booking-list"), self.booking_data, format="json"
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        booking = Booking.objects.get(pk=create_response.data["id"])
        self.assertEqual(booking.status, Booking.Status.PENDING)
        self.assertEqual(Ticket.objects.filter(booking=booking).count(), 0)

        tickets_response = self.client.get(reverse("ticket-my-tickets"))
        self.assertEqual(tickets_response.status_code, status.HTTP_200_OK)
        self.assertEqual(tickets_response.data["count"], 0)

    def test_customer_cannot_book_unapproved_event(self):
        """Customer cannot book unapproved events."""
        self.event.status = "PENDING"
        self.event.save()
        self.client.force_authenticate(user=self.customer_user)
        url = reverse("booking-list")
        response = self.client.post(url, self.booking_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_customer_cannot_book_past_event(self):
        """Customer cannot book past events."""
        self.event.event_date = timezone.now().date() - timedelta(days=1)
        self.event.save()
        self.client.force_authenticate(user=self.customer_user)
        url = reverse("booking-list")
        response = self.client.post(url, self.booking_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_quantity_must_be_greater_than_zero(self):
        """Quantity must be greater than zero."""
        self.client.force_authenticate(user=self.customer_user)
        url = reverse("booking-list")
        data = self.booking_data.copy()
        data["quantity"] = 0
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_insufficient_tickets(self):
        """Cannot book more tickets than available."""
        self.event.available_tickets = 1
        self.event.save()
        self.client.force_authenticate(user=self.customer_user)
        url = reverse("booking-list")
        data = self.booking_data.copy()
        data["quantity"] = 5
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_organizer_cannot_create_booking(self):
        """Organizer cannot create bookings."""
        self.client.force_authenticate(user=self.organizer_user)
        url = reverse("booking-list")
        response = self.client.post(url, self.booking_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_cannot_create_booking(self):
        """Unauthenticated users cannot create bookings."""
        url = reverse("booking-list")
        response = self.client.post(url, self.booking_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_booking_decreases_available_tickets(self):
        """Booking decreases event available_tickets."""
        self.client.force_authenticate(user=self.customer_user)
        url = reverse("booking-list")
        response = self.client.post(url, self.booking_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.event.refresh_from_db()
        self.assertEqual(self.event.available_tickets, 98)

    def test_booking_stores_unit_price(self):
        """Booking stores event ticket price at booking time."""
        self.client.force_authenticate(user=self.customer_user)
        url = reverse("booking-list")
        response = self.client.post(url, self.booking_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["unit_price"], "25.00")
        self.assertEqual(response.data["total_amount"], "50.00")


class BookingCancellationAPITest(APITestCase):
    """Tests for booking cancellation."""

    def setUp(self):
        self.client = APIClient()
        self.customer_user = User.objects.create_user(
            username="customer",
            email="customer@test.com",
            password="testpass123",
            role="CUSTOMER",
        )
        self.other_customer = User.objects.create_user(
            username="customer2",
            email="customer2@test.com",
            password="testpass123",
            role="CUSTOMER",
        )
        self.organizer_user = User.objects.create_user(
            username="organizer",
            email="organizer@test.com",
            password="testpass123",
            role="ORGANIZER",
        )
        self.category, _ = EventCategory.objects.get_or_create(name="Music", defaults={"description": "Music events"})
        self.event = Event.objects.create(
            title="Test Concert",
            description="A test concert",
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
        self.booking = Booking.objects.create(
            customer=self.customer_user,
            event=self.event,
            quantity=2,
            unit_price=25.00,
            total_amount=50.00,
            status=Booking.Status.CONFIRMED,
        )

    def test_customer_can_cancel_own_booking(self):
        """Customer can cancel their own booking."""
        self.client.force_authenticate(user=self.customer_user)
        url = reverse("booking-cancel", kwargs={"pk": self.booking.id})
        response = self.client.post(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, "CANCELLED")

    def test_cancellation_restores_tickets(self):
        """Cancellation restores event available_tickets."""
        self.event.available_tickets = 98
        self.event.save()
        self.client.force_authenticate(user=self.customer_user)
        url = reverse("booking-cancel", kwargs={"pk": self.booking.id})
        response = self.client.post(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.event.refresh_from_db()
        self.assertEqual(self.event.available_tickets, 100)

    def test_customer_cannot_cancel_others_booking(self):
        """Customer cannot cancel another customer's booking."""
        self.client.force_authenticate(user=self.other_customer)
        url = reverse("booking-cancel", kwargs={"pk": self.booking.id})
        response = self.client.post(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_cancel_already_cancelled_booking(self):
        """Cannot cancel already cancelled booking."""
        self.booking.status = Booking.Status.CANCELLED
        self.booking.save()
        self.client.force_authenticate(user=self.customer_user)
        url = reverse("booking-cancel", kwargs={"pk": self.booking.id})
        response = self.client.post(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_cancel_does_not_restore_inventory_twice(self):
        self.event.available_tickets = 98
        self.event.save()
        self.client.force_authenticate(user=self.customer_user)
        url = reverse("booking-cancel", kwargs={"pk": self.booking.id})

        first = self.client.post(url, format="json")
        second = self.client.post(url, format="json")

        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)
        self.event.refresh_from_db()
        self.assertEqual(self.event.available_tickets, 100)

    def test_paid_booking_cannot_be_cancelled_without_refund(self):
        Payment.objects.create(
            booking=self.booking,
            customer=self.customer_user,
            amount=self.booking.total_amount,
            currency="INR",
            status=Payment.Status.SUCCESS,
            signature_verified=True,
        )
        self.event.available_tickets = 98
        self.event.save()
        self.client.force_authenticate(user=self.customer_user)

        response = self.client.post(reverse("booking-cancel", kwargs={"pk": self.booking.id}), format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.booking.refresh_from_db()
        self.event.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.CONFIRMED)
        self.assertEqual(self.event.available_tickets, 98)

    def test_organizer_cannot_cancel_customer_booking(self):
        """Organizer cannot cancel customer bookings via cancel endpoint."""
        self.client.force_authenticate(user=self.organizer_user)
        url = reverse("booking-cancel", kwargs={"pk": self.booking.id})
        response = self.client.post(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class BookingListAPITest(APITestCase):
    """Tests for booking list views."""

    def setUp(self):
        self.client = APIClient()
        self.customer_user = User.objects.create_user(
            username="customer",
            email="customer@test.com",
            password="testpass123",
            role="CUSTOMER",
        )
        self.other_customer = User.objects.create_user(
            username="customer2",
            email="customer2@test.com",
            password="testpass123",
            role="CUSTOMER",
        )
        self.organizer_user = User.objects.create_user(
            username="organizer",
            email="organizer@test.com",
            password="testpass123",
            role="ORGANIZER",
        )
        self.admin_user = User.objects.create_user(
            username="admin",
            email="admin@test.com",
            password="testpass123",
            role="ADMIN",
        )
        self.category, _ = EventCategory.objects.get_or_create(name="Music", defaults={"description": "Music events"})
        self.event1 = Event.objects.create(
            title="Event 1",
            description="First event",
            category=self.category,
            organizer=self.organizer_user,
            venue="Venue 1",
            city="City 1",
            event_date=timezone.now().date() + timedelta(days=30),
            start_time="14:00:00",
            end_time="18:00:00",
            ticket_price=25.00,
            total_tickets=100,
            available_tickets=100,
            status="APPROVED",
        )
        self.event2 = Event.objects.create(
            title="Event 2",
            description="Second event",
            category=self.category,
            organizer=self.organizer_user,
            venue="Venue 2",
            city="City 2",
            event_date=timezone.now().date() + timedelta(days=30),
            start_time="14:00:00",
            end_time="18:00:00",
            ticket_price=30.00,
            total_tickets=50,
            available_tickets=50,
            status="APPROVED",
        )
        self.booking1 = Booking.objects.create(
            customer=self.customer_user,
            event=self.event1,
            quantity=2,
            unit_price=25.00,
            total_amount=50.00,
            status=Booking.Status.CONFIRMED,
        )
        self.booking2 = Booking.objects.create(
            customer=self.other_customer,
            event=self.event2,
            quantity=1,
            unit_price=30.00,
            total_amount=30.00,
            status=Booking.Status.CONFIRMED,
        )

    def test_customer_sees_only_own_bookings(self):
        """Customer sees only their own bookings."""
        self.client.force_authenticate(user=self.customer_user)
        url = reverse("booking-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"]
        booking_ids = [b["id"] for b in results]
        self.assertIn(self.booking1.id, booking_ids)
        self.assertNotIn(self.booking2.id, booking_ids)

    def test_my_bookings_endpoint(self):
        """My-bookings endpoint returns customer's bookings."""
        self.client.force_authenticate(user=self.customer_user)
        url = reverse("booking-my-bookings")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"]
        for b in results:
            self.assertEqual(b["customer"], self.customer_user.id)

    def test_customer_cannot_access_my_bookings(self):
        """Non-customer cannot access my-bookings."""
        self.client.force_authenticate(user=self.organizer_user)
        url = reverse("booking-my-bookings")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_organizer_sees_bookings_for_own_events(self):
        """Organizer sees bookings for their own events."""
        self.client.force_authenticate(user=self.organizer_user)
        url = reverse("booking-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"]
        booking_ids = [b["id"] for b in results]
        self.assertIn(self.booking1.id, booking_ids)
        self.assertIn(self.booking2.id, booking_ids)

    def test_admin_sees_all_bookings(self):
        """Admin sees all bookings."""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("booking-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"]
        booking_ids = [b["id"] for b in results]
        self.assertIn(self.booking1.id, booking_ids)
        self.assertIn(self.booking2.id, booking_ids)

    def test_customer_cannot_access_other_booking_detail(self):
        """Customer cannot access another customer's booking detail."""
        self.client.force_authenticate(user=self.customer_user)
        url = reverse("booking-detail", kwargs={"pk": self.booking2.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class BookingConcurrencyAPITest(APITestCase):
    """Tests for concurrent booking protection."""

    def setUp(self):
        self.client = APIClient()
        self.customer1 = User.objects.create_user(
            username="customer1",
            email="c1@test.com",
            password="testpass123",
            role="CUSTOMER",
        )
        self.customer2 = User.objects.create_user(
            username="customer2",
            email="c2@test.com",
            password="testpass123",
            role="CUSTOMER",
        )
        self.organizer_user = User.objects.create_user(
            username="organizer",
            email="organizer@test.com",
            password="testpass123",
            role="ORGANIZER",
        )
        self.category, _ = EventCategory.objects.get_or_create(name="Music", defaults={"description": "Music events"})
        self.event = Event.objects.create(
            title="Limited Event",
            description="Limited tickets",
            category=self.category,
            organizer=self.organizer_user,
            venue="Venue",
            city="City",
            event_date=timezone.now().date() + timedelta(days=30),
            start_time="14:00:00",
            end_time="18:00:00",
            ticket_price=10.00,
            total_tickets=1,
            available_tickets=1,
            status="APPROVED",
        )

    def test_concurrent_booking_prevents_overselling(self):
        """Concurrent bookings cannot exceed available tickets."""
        # First booking succeeds
        self.client.force_authenticate(user=self.customer1)
        url = reverse("booking-list")
        response = self.client.post(
            url, {"event": self.event.id, "quantity": 1}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.event.refresh_from_db()
        self.assertEqual(self.event.available_tickets, 0)

        # Second booking fails
        self.client.force_authenticate(user=self.customer2)
        response = self.client.post(
            url, {"event": self.event.id, "quantity": 1}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
