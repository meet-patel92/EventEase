from datetime import timedelta
from decimal import Decimal

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from bookings.models import Booking
from events.models import Event, EventCategory
from payments.models import Payment
from tickets.models import Ticket


class DashboardOverviewAPITest(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin", email="admin@example.test", password="test-pass-123", role="ADMIN"
        )
        self.organizer = User.objects.create_user(
            username="organizer", email="organizer@example.test", password="test-pass-123", role="ORGANIZER"
        )
        self.other_organizer = User.objects.create_user(
            username="otherorg", email="otherorg@example.test", password="test-pass-123", role="ORGANIZER"
        )
        self.customer = User.objects.create_user(
            username="customer", email="customer@example.test", password="test-pass-123", role="CUSTOMER"
        )
        category = EventCategory.objects.create(name="Dashboard Test Category")
        fields = {
            "description": "Dashboard test event",
            "category": category,
            "venue": "Test hall",
            "city": "Test city",
            "event_date": timezone.localdate() + timedelta(days=30),
            "start_time": "14:00",
            "end_time": "18:00",
            "ticket_price": 25,
            "total_tickets": 20,
            "available_tickets": 20,
        }
        self.event = Event.objects.create(
            title="Organizer dashboard event", organizer=self.organizer,
            status=Event.Status.APPROVED, **fields
        )
        self.other_event = Event.objects.create(
            title="Other organizer event", organizer=self.other_organizer,
            status=Event.Status.PENDING, **fields
        )
        self.booking = Booking.objects.create(
            customer=self.customer, event=self.event, quantity=2,
            unit_price=25, total_amount=50, status=Booking.Status.CONFIRMED,
        )
        self.payment = Payment.objects.create(
            booking=self.booking, customer=self.customer,
            razorpay_order_id="order_dashboard_test", razorpay_payment_id="pay_dashboard_test",
            amount=50, currency="INR", provider="RAZORPAY", status=Payment.Status.SUCCESS,
            signature_verified=True,
        )
        self.ticket = Ticket.objects.create(
            booking=self.booking, payment=self.payment, customer=self.customer,
            event=self.event, status=Ticket.Status.VALID,
        )
        self.url = reverse("dashboard-overview")

    def test_anonymous_user_cannot_access_dashboard(self):
        self.assertEqual(self.client.get(self.url).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_customer_dashboard_contains_scoped_counts_and_upcoming_booking(self):
        self.client.force_authenticate(self.customer)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["role"], "CUSTOMER")
        cards = {card["key"]: card["value"] for card in response.data["cards"]}
        self.assertEqual(cards["bookings"], 1)
        self.assertEqual(cards["confirmed"], 1)
        self.assertEqual(cards["tickets"], 1)
        self.assertEqual(response.data["upcoming_events"][0]["event"], self.event.title)

    def test_organizer_dashboard_scopes_events_and_counts_verified_revenue(self):
        self.client.force_authenticate(self.organizer)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["role"], "ORGANIZER")
        cards = {card["key"]: card["value"] for card in response.data["cards"]}
        self.assertEqual(cards["events"], 1)
        self.assertEqual(cards["confirmed"], 1)
        # Aggregate numeric types differ by backend: MySQL returns Decimal,
        # while SQLite may return an int/float. Compare the monetary value.
        self.assertEqual(Decimal(str(cards["revenue"])), Decimal("50.00"))
        self.assertEqual([row["id"] for row in response.data["event_bookings"]], [self.event.id])

    def test_admin_dashboard_includes_global_counts(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["role"], "ADMIN")
        cards = {card["key"]: card["value"] for card in response.data["cards"]}
        self.assertEqual(cards["users"], 4)
        self.assertEqual(cards["events"], 2)
        self.assertEqual(cards["confirmed_bookings"], 1)
        self.assertEqual(cards["payments"], 1)

    def test_organizer_dashboard_is_empty_for_user_without_events(self):
        no_event_organizer = User.objects.create_user(
            username="noevents", email="noevents@example.test",
            password="test-pass-123", role="ORGANIZER",
        )
        self.client.force_authenticate(no_event_organizer)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        cards = {card["key"]: card["value"] for card in response.data["cards"]}
        self.assertEqual(cards["events"], 0)
        self.assertEqual(cards["bookings"], 0)
        self.assertEqual(response.data["event_bookings"], [])
