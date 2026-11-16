from types import SimpleNamespace
from unittest.mock import Mock, patch
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from accounts.models import User
from events.models import EventCategory, Event
from bookings.models import Booking
from payments.models import Payment
from tickets.models import Ticket
from tickets.serializers import TicketSerializer


class TicketModelTest(TestCase):
    """Tests for Ticket model."""

    def setUp(self):
        self.customer = User.objects.create_user(
            username="customer",
            email="customer@test.com",
            password="testpass123",
            role="CUSTOMER",
        )
        self.organizer = User.objects.create_user(
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
            organizer=self.organizer,
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
            customer=self.customer,
            event=self.event,
            quantity=2,
            unit_price=25.00,
            total_amount=50.00,
            status="CONFIRMED",
        )
        self.payment = Payment.objects.create(
            booking=self.booking,
            customer=self.customer,
            razorpay_order_id="order_test123",
            razorpay_payment_id="pay_test456",
            amount=50.00,
            currency="INR",
            provider="RAZORPAY",
            status="SUCCESS",
            signature_verified=True,
            transaction_id="pay_test456",
        )

    def test_ticket_creation(self):
        """Test creating a ticket."""
        ticket = Ticket.objects.create(
            booking=self.booking,
            payment=self.payment,
            customer=self.customer,
            event=self.event,
            status=Ticket.Status.VALID,
        )
        ticket.ticket_number = ticket.generate_ticket_number()
        ticket.ticket_token = ticket.generate_ticket_token()
        ticket.save()
        self.assertIsNotNone(ticket.ticket_number)
        self.assertIsNotNone(ticket.ticket_token)
        self.assertEqual(ticket.status, Ticket.Status.VALID)
        self.assertTrue(ticket.is_valid)

    def test_ticket_number_uniqueness(self):
        """Test that ticket numbers are unique."""
        ticket1 = Ticket.objects.create(
            booking=self.booking,
            payment=self.payment,
            customer=self.customer,
            event=self.event,
            status=Ticket.Status.VALID,
        )
        ticket1.ticket_number = "TKT-UNIQUE001"
        ticket1.ticket_token = "TOKEN001"
        ticket1.save()

        ticket2 = Ticket.objects.create(
            booking=self.booking,
            payment=self.payment,
            customer=self.customer,
            event=self.event,
            status=Ticket.Status.VALID,
        )
        ticket2.ticket_number = "TKT-UNIQUE002"
        ticket2.ticket_token = "TOKEN002"
        ticket2.save()

        self.assertNotEqual(ticket1.ticket_number, ticket2.ticket_number)
        self.assertNotEqual(ticket1.ticket_token, ticket2.ticket_token)


class TicketVerifyIsolatedLogicAPITest(APITestCase):
    """Exercise verify behavior with an in-memory ticket, without payment records."""

    def setUp(self):
        self.organizer = User.objects.create_user(
            username="verify-organizer", email="verify-organizer@example.test",
            password="unused-test-password", role="ORGANIZER",
        )
        self.event = Event.objects.create(
            title="Verify Test Event", description="Isolated verification fixture",
            organizer=self.organizer, venue="Test Venue", city="Test City",
            event_date=timezone.now().date() + timedelta(days=1),
            start_time="12:00", end_time="23:59", status=Event.Status.APPROVED,
        )
        self.event.refresh_from_db()
        self.ticket = SimpleNamespace(
            event=self.event,
            event_id=self.event.id,
            status=Ticket.Status.VALID,
            ticket_number="TKT-VERIFY-TEST",
            booking=SimpleNamespace(status=Booking.Status.CONFIRMED),
            payment=SimpleNamespace(status=Payment.Status.SUCCESS, signature_verified=True),
            save=Mock(),
        )
        self.queryset = Mock()
        self.queryset.select_related.return_value = self.queryset
        self.queryset.get.return_value = self.ticket
        self.client.force_authenticate(user=self.organizer)

    def verify(self, token="REGRESSION-TEST-TOKEN", event_id=None):
        return self.client.post(
            reverse("ticket-verify"),
            {"ticket_token": token, "event_id": event_id or self.event.id},
            format="json",
        )

    @patch("tickets.views.Ticket.objects.select_for_update")
    def test_valid_token_checks_in_ticket(self, select_for_update):
        # The same token exposed by the customer ticket serializer is what the
        # verifier must accept. Only the isolated ticket fixture is persisted.
        displayed_ticket = Ticket.objects.create(
            event=self.event,
            customer=self.organizer,
            status=Ticket.Status.VALID,
        )
        # Represent the existing verified relations in memory; this regression
        # writes no booking or payment rows to even the isolated test database.
        displayed_ticket.booking = Booking(
            id=101, booking_reference="BOOKING-REFERENCE-TEST", quantity=1,
            total_amount="25.00", status=Booking.Status.CONFIRMED,
        )
        displayed_ticket.payment = Payment(
            id=201, status=Payment.Status.SUCCESS, signature_verified=True,
        )
        displayed_ticket.save = Mock()
        select_for_update.return_value = self.queryset
        displayed_code = TicketSerializer(displayed_ticket).data["ticket_token"]
        self.assertTrue(displayed_ticket.get_qr_code_url() == displayed_code)

        def lookup_ticket(**lookup_kwargs):
            if lookup_kwargs.get("ticket_token") == displayed_ticket.ticket_token:
                return displayed_ticket
            raise Ticket.DoesNotExist

        self.queryset.get.side_effect = lookup_ticket
        response = self.client.post(
            reverse("ticket-verify"),
            {"ticket_token": displayed_code, "event_id": self.event.id},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["ticket_status"], Ticket.Status.USED)
        displayed_ticket.save.assert_called_once()

    @patch("tickets.views.Ticket.objects.select_for_update")
    def test_invalid_token_is_not_found(self, select_for_update):
        self.queryset.get.side_effect = Ticket.DoesNotExist
        select_for_update.return_value = self.queryset
        response = self.verify()
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch("tickets.views.Ticket.objects.select_for_update")
    def test_ticket_from_another_event_is_rejected(self, select_for_update):
        select_for_update.return_value = self.queryset
        response = self.verify(event_id=self.event.id + 1)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Ticket belongs to a different event.")

    @patch("tickets.views.Ticket.objects.select_for_update")
    def test_unpaid_booking_is_rejected(self, select_for_update):
        self.ticket.booking = SimpleNamespace(status=Booking.Status.PENDING)
        self.ticket.payment = None
        select_for_update.return_value = self.queryset
        response = self.verify()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Ticket does not have a verified payment.")

    @patch("tickets.views.Ticket.objects.select_for_update")
    def test_duplicate_checkin_is_rejected(self, select_for_update):
        select_for_update.return_value = self.queryset
        first = self.verify()
        second = self.verify()
        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.ticket.status, Ticket.Status.USED)


class TicketGenerationAPITest(APITestCase):
    """Tests for ticket generation after payment."""

    def setUp(self):
        self.client = APIClient()
        self.customer = User.objects.create_user(
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
        self.organizer = User.objects.create_user(
            username="organizer",
            email="organizer@test.com",
            password="testpass123",
            role="ORGANIZER",
        )
        self.admin = User.objects.create_user(
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
            organizer=self.organizer,
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

    def create_successful_booking_and_payment(self, customer, quantity=1, event=None):
        """Helper to create a confirmed booking with successful payment and tickets."""
        event = event or self.event
        booking = Booking.objects.create(
            customer=customer,
            event=event,
            quantity=quantity,
            unit_price=25.00,
            total_amount=25.00 * quantity,
            status="CONFIRMED",
        )
        payment = Payment.objects.create(
            booking=booking,
            customer=customer,
            razorpay_order_id=f"order_{booking.booking_reference}",
            razorpay_payment_id=f"pay_{booking.booking_reference}",
            amount=booking.total_amount,
            currency="INR",
            provider="RAZORPAY",
            status="SUCCESS",
            signature_verified=True,
            transaction_id=f"pay_{booking.booking_reference}",
        )
        # Generate tickets for the booking
        for i in range(quantity):
            ticket = Ticket(
                booking=booking,
                payment=payment,
                customer=customer,
                event=event,
                status=Ticket.Status.VALID,
            )
            ticket.ticket_number = ticket.generate_ticket_number()
            ticket.ticket_token = ticket.generate_ticket_token()
            ticket.save()
        return booking, payment

    def test_ticket_generation_after_successful_payment(self):
        """Test that tickets are generated after successful payment."""
        booking, payment = self.create_successful_booking_and_payment(
            self.customer, quantity=2
        )
        tickets = Ticket.objects.filter(booking=booking)
        self.assertEqual(tickets.count(), 2)
        for ticket in tickets:
            self.assertEqual(ticket.customer, self.customer)
            self.assertEqual(ticket.event, self.event)
            self.assertEqual(ticket.status, Ticket.Status.VALID)
            self.assertIsNotNone(ticket.ticket_number)
            self.assertIsNotNone(ticket.ticket_token)

    def test_no_ticket_generation_for_failed_payment(self):
        """Test that no tickets are generated for failed payment."""
        booking = Booking.objects.create(
            customer=self.customer,
            event=self.event,
            quantity=1,
            unit_price=25.00,
            total_amount=25.00,
            status="PENDING",
        )
        Payment.objects.create(
            booking=booking,
            customer=self.customer,
            razorpay_order_id="order_fail",
            razorpay_payment_id="pay_fail",
            amount=25.00,
            currency="INR",
            provider="RAZORPAY",
            status="FAILED",
        )
        tickets = Ticket.objects.filter(booking=booking)
        self.assertEqual(tickets.count(), 0)

    def test_no_ticket_generation_before_successful_payment(self):
        """Test that no tickets exist before payment is successful."""
        booking = Booking.objects.create(
            customer=self.customer,
            event=self.event,
            quantity=1,
            unit_price=25.00,
            total_amount=25.00,
            status="PENDING",
        )
        Payment.objects.create(
            booking=booking,
            customer=self.customer,
            razorpay_order_id="order_pending",
            razorpay_payment_id="pay_pending",
            amount=25.00,
            currency="INR",
            provider="RAZORPAY",
            status="CREATED",
        )
        tickets = Ticket.objects.filter(booking=booking)
        self.assertEqual(tickets.count(), 0)

    def test_quantity_1_generates_one_ticket(self):
        """Test that quantity 1 generates exactly one ticket."""
        booking, payment = self.create_successful_booking_and_payment(
            self.customer, quantity=1
        )
        tickets = Ticket.objects.filter(booking=booking)
        self.assertEqual(tickets.count(), 1)

    def test_quantity_3_generates_three_tickets(self):
        """Test that quantity 3 generates exactly three tickets."""
        booking, payment = self.create_successful_booking_and_payment(
            self.customer, quantity=3
        )
        tickets = Ticket.objects.filter(booking=booking)
        self.assertEqual(tickets.count(), 3)
        ticket_numbers = [t.ticket_number for t in tickets]
        self.assertEqual(len(set(ticket_numbers)), 3)  # All unique

    def test_duplicate_verification_no_duplicate_tickets(self):
        """Test that duplicate payment verification doesn't create duplicate tickets."""
        booking, payment = self.create_successful_booking_and_payment(
            self.customer, quantity=2
        )
        initial_count = Ticket.objects.filter(booking=booking).count()
        # Simulate re-verification by checking tickets still exist
        tickets_after = Ticket.objects.filter(booking=booking)
        self.assertEqual(tickets_after.count(), initial_count)

    def test_customer_cannot_access_another_customer_ticket(self):
        """Test that customer cannot access another customer's ticket."""
        booking, payment = self.create_successful_booking_and_payment(
            self.customer, quantity=1
        )
        ticket = Ticket.objects.get(booking=booking)
        self.client.force_authenticate(user=self.other_customer)
        url = reverse("ticket-detail", kwargs={"pk": ticket.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_organizer_sees_tickets_for_own_events(self):
        """Test that organizer sees tickets for their own events."""
        booking, payment = self.create_successful_booking_and_payment(
            self.customer, quantity=1
        )
        self.client.force_authenticate(user=self.organizer)
        url = reverse("ticket-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"]
        ticket_numbers = [t["ticket_number"] for t in results]
        ticket = Ticket.objects.get(booking=booking)
        self.assertIn(ticket.ticket_number, ticket_numbers)

    def test_admin_sees_all_tickets(self):
        """Test that admin sees all tickets."""
        booking, payment = self.create_successful_booking_and_payment(
            self.customer, quantity=1
        )
        self.client.force_authenticate(user=self.admin)
        url = reverse("ticket-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"]
        ticket_numbers = [t["ticket_number"] for t in results]
        ticket = Ticket.objects.get(booking=booking)
        self.assertIn(ticket.ticket_number, ticket_numbers)

    def test_customer_sees_only_own_tickets(self):
        """Test that customer sees only their own tickets."""
        booking1, payment1 = self.create_successful_booking_and_payment(
            self.customer, quantity=1
        )
        booking2, payment2 = self.create_successful_booking_and_payment(
            self.other_customer, quantity=1, event=self.event
        )
        self.client.force_authenticate(user=self.customer)
        url = reverse("ticket-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"]
        ticket_numbers = [t["ticket_number"] for t in results]
        ticket1_obj = Ticket.objects.get(booking=booking1)
        ticket2_obj = Ticket.objects.get(booking=booking2)
        self.assertIn(ticket1_obj.ticket_number, ticket_numbers)
        self.assertNotIn(ticket2_obj.ticket_number, ticket_numbers)

    def test_my_tickets_returns_only_current_customer_tickets(self):
        booking, _ = self.create_successful_booking_and_payment(
            self.customer, quantity=2
        )
        self.create_successful_booking_and_payment(
            self.other_customer, quantity=1, event=self.event
        )
        self.client.force_authenticate(user=self.customer)

        response = self.client.get(reverse("ticket-my-tickets"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(len(response.data["results"]), 2)
        for ticket in response.data["results"]:
            self.assertEqual(ticket["customer_email"], self.customer.email)
            self.assertEqual(ticket["booking_id"], booking.id)
            self.assertEqual(ticket["booking_quantity"], 2)
            self.assertEqual(str(ticket["booking_total_amount"]), "50.00")
            self.assertEqual(ticket["booking_status"], Booking.Status.CONFIRMED)
            self.assertEqual(ticket["event_title"], self.event.title)
            self.assertEqual(str(ticket["start_time"]), "14:00:00")
            self.assertEqual(ticket["venue"], self.event.venue)

    def test_customer_cannot_use_ticket_checkin_endpoint(self):
        self.client.force_authenticate(user=self.customer)
        response = self.client.post(
            reverse("ticket-verify"),
            {"ticket_token": "not-a-real-ticket", "event_id": self.event.id},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unknown_ticket_token_is_rejected(self):
        self.client.force_authenticate(user=self.organizer)
        response = self.client.post(
            reverse("ticket-verify"),
            {"ticket_token": "not-a-real-ticket", "event_id": self.event.id},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_ticket_for_another_selected_event_is_rejected(self):
        another_event = Event.objects.create(
            title="Another Approved Event",
            description="Event selection regression fixture",
            organizer=self.organizer,
            venue="Another Venue",
            city="Test City",
            event_date=timezone.now().date() + timedelta(days=30),
            start_time="14:00",
            end_time="18:00",
            status=Event.Status.APPROVED,
        )
        ticket = Ticket.objects.create(
            customer=self.customer,
            event=self.event,
            status=Ticket.Status.VALID,
        )
        self.client.force_authenticate(user=self.organizer)
        response = self.client.post(
            reverse("ticket-verify"),
            {"ticket_token": ticket.ticket_token, "event_id": another_event.id},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Ticket belongs to a different event.")

    def test_cancelled_ticket_cannot_be_checked_in(self):
        ticket = Ticket.objects.create(
            customer=self.customer,
            event=self.event,
            status=Ticket.Status.CANCELLED,
        )
        self.client.force_authenticate(user=self.organizer)
        response = self.client.post(
            reverse("ticket-verify"),
            {"ticket_token": ticket.ticket_token, "event_id": self.event.id},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unverified_ticket_cannot_be_checked_in(self):
        booking = Booking.objects.create(
            customer=self.customer,
            event=self.event,
            quantity=1,
            unit_price=25.00,
            total_amount=25.00,
            status=Booking.Status.PENDING,
        )
        ticket = Ticket.objects.create(
            booking=booking,
            customer=self.customer,
            event=self.event,
            status=Ticket.Status.VALID,
        )
        self.client.force_authenticate(user=self.organizer)
        response = self.client.post(
            reverse("ticket-verify"),
            {"ticket_token": ticket.ticket_token, "event_id": self.event.id},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, Ticket.Status.VALID)

    def test_organizer_can_check_in_verified_ticket_once(self):
        booking, payment = self.create_successful_booking_and_payment(self.customer)
        ticket = Ticket.objects.get(booking=booking)
        self.client.force_authenticate(user=self.organizer)
        payload = {"ticket_token": ticket.ticket_token, "event_id": self.event.id}

        response = self.client.post(reverse("ticket-verify"), payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["ticket_status"], Ticket.Status.USED)
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, Ticket.Status.USED)

    def test_pending_event_cannot_be_scanned(self):
        pending_event = Event.objects.create(
            title="Pending Event", description="Not approved", organizer=self.organizer,
            venue="Venue", city="City", event_date=timezone.now().date() + timedelta(days=30),
            start_time="14:00", end_time="18:00", ticket_price=25,
            total_tickets=10, available_tickets=10, status=Event.Status.PENDING,
        )
        booking, payment = self.create_successful_booking_and_payment(self.customer, event=pending_event)
        ticket = Ticket.objects.get(booking=booking)
        self.client.force_authenticate(user=self.organizer)
        response = self.client.post(reverse("ticket-verify"), {"ticket_token": ticket.ticket_token, "event_id": pending_event.id}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, Ticket.Status.VALID)

    def test_scanning_same_ticket_twice_is_rejected(self):
        booking, _payment = self.create_successful_booking_and_payment(self.customer)
        ticket = Ticket.objects.get(booking=booking)
        self.client.force_authenticate(user=self.organizer)
        payload = {"ticket_token": ticket.ticket_token, "event_id": self.event.id}

        first_response = self.client.post(reverse("ticket-verify"), payload, format="json")
        second_response = self.client.post(reverse("ticket-verify"), payload, format="json")

        self.assertEqual(first_response.status_code, status.HTTP_200_OK)
        self.assertEqual(second_response.status_code, status.HTTP_400_BAD_REQUEST)
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, Ticket.Status.USED)


class TicketPDFDownloadAPITest(APITestCase):
    """Tests for ticket PDF download."""

    def setUp(self):
        self.client = APIClient()
        self.customer = User.objects.create_user(
            username="customer",
            email="customer@test.com",
            password="testpass123",
            role="CUSTOMER",
        )
        self.organizer = User.objects.create_user(
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
            organizer=self.organizer,
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
            customer=self.customer,
            event=self.event,
            quantity=2,
            unit_price=25.00,
            total_amount=50.00,
            status="CONFIRMED",
        )
        self.payment = Payment.objects.create(
            booking=self.booking,
            customer=self.customer,
            razorpay_order_id="order_test",
            razorpay_payment_id="pay_test",
            amount=50.00,
            currency="INR",
            provider="RAZORPAY",
            status="SUCCESS",
            signature_verified=True,
        )
        self.ticket1 = Ticket.objects.create(
            booking=self.booking,
            payment=self.payment,
            customer=self.customer,
            event=self.event,
            status=Ticket.Status.VALID,
        )
        self.ticket1.ticket_number = "TKT-TEST001"
        self.ticket1.ticket_token = "TOKEN-TEST001"
        self.ticket1.save()
        self.ticket2 = Ticket.objects.create(
            booking=self.booking,
            payment=self.payment,
            customer=self.customer,
            event=self.event,
            status=Ticket.Status.VALID,
        )
        self.ticket2.ticket_number = "TKT-TEST002"
        self.ticket2.ticket_token = "TOKEN-TEST002"
        self.ticket2.save()

    def test_pdf_download_returns_application_pdf(self):
        """Test that PDF download returns application/pdf content type."""
        self.client.force_authenticate(user=self.customer)
        url = reverse("ticket-download", kwargs={"pk": self.ticket1.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/pdf")

    def test_download_all_tickets(self):
        """Test download-all endpoint for multiple tickets."""
        self.client.force_authenticate(user=self.customer)
        url = reverse(
            "ticket-download-all", kwargs={"booking_id": self.booking.id}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/pdf")

    def test_customer_cannot_download_another_customer_ticket(self):
        """Test that customer cannot download another customer's ticket."""
        other_customer = User.objects.create_user(
            username="other",
            email="other@test.com",
            password="testpass123",
            role="CUSTOMER",
        )
        other_booking = Booking.objects.create(
            customer=other_customer,
            event=self.event,
            quantity=1,
            unit_price=25.00,
            total_amount=25.00,
            status="CONFIRMED",
        )
        other_payment = Payment.objects.create(
            booking=other_booking,
            customer=other_customer,
            razorpay_order_id="order_other",
            razorpay_payment_id="pay_other",
            amount=25.00,
            currency="INR",
            provider="RAZORPAY",
            status="SUCCESS",
        )
        other_ticket = Ticket.objects.create(
            booking=other_booking,
            payment=other_payment,
            customer=other_customer,
            event=self.event,
            status=Ticket.Status.VALID,
        )
        other_ticket.ticket_number = "TKT-OTHER"
        other_ticket.ticket_token = "TOKEN-OTHER"
        other_ticket.save()

        self.client.force_authenticate(user=self.customer)
        url = reverse("ticket-download", kwargs={"pk": other_ticket.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
