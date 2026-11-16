from unittest.mock import patch, MagicMock
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from accounts.models import User
from events.models import EventCategory, Event
from bookings.models import Booking
from payments.models import Payment


class PaymentOrderCreationAPITest(APITestCase):
    """Tests for Razorpay order creation."""

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
        self.booking = Booking.objects.create(
            customer=self.customer_user,
            event=self.event,
            quantity=2,
            unit_price=25.00,
            total_amount=50.00,
            status="PENDING",
        )

    @override_settings(
        RAZORPAY_KEY_ID="",
        RAZORPAY_KEY_SECRET="",
    )
    def test_order_creation_fails_closed_without_test_credentials(self):
        with patch("payments.views.razorpay_client.order.create") as mock_order_create:
            self.client.force_authenticate(user=self.customer_user)
            url = reverse("payment-create-order")
            response = self.client.post(
                url, {"booking_id": self.booking.id}, format="json"
            )
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertIn("RAZORPAY_KEY_SECRET", response.data["error"])
        self.assertIn("rzp_test_", response.data["error"])
        self.assertNotIn("key", response.data)
        self.assertEqual(self.booking.payments.count(), 0)
        mock_order_create.assert_not_called()

    @override_settings(
        RAZORPAY_KEY_ID="rzp_live_must_not_work",
        RAZORPAY_KEY_SECRET="configured_but_live_only",
    )
    def test_live_key_is_rejected_by_test_mode_order_endpoint(self):
        with patch("payments.views.razorpay_client.order.create") as mock_order_create:
            self.client.force_authenticate(user=self.customer_user)
            response = self.client.post(
                reverse("payment-create-order"),
                {"booking_id": self.booking.id},
                format="json",
            )
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        mock_order_create.assert_not_called()

    def test_customer_cannot_pay_for_others_booking(self):
        """Customer cannot create order for another customer's booking."""
        other_booking = Booking.objects.create(
            customer=self.other_customer,
            event=self.event,
            quantity=1,
            unit_price=25.00,
            total_amount=25.00,
            status="PENDING",
        )

        self.client.force_authenticate(user=self.customer_user)
        url = reverse("payment-create-order")
        response = self.client.post(
            url, {"booking_id": other_booking.id}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_cannot_pay_for_non_pending_booking(self):
        """Cannot create order for non-PENDING booking."""
        confirmed_booking = Booking.objects.create(
            customer=self.customer_user,
            event=self.event,
            quantity=1,
            unit_price=25.00,
            total_amount=25.00,
            status="CONFIRMED",
        )

        self.client.force_authenticate(user=self.customer_user)
        url = reverse("payment-create-order")
        response = self.client.post(
            url, {"booking_id": confirmed_booking.id}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_organizer_cannot_create_order(self):
        """Organizer cannot create payment orders."""
        self.client.force_authenticate(user=self.organizer_user)
        url = reverse("payment-create-order")
        response = self.client.post(
            url, {"booking_id": self.booking.id}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_cannot_create_order(self):
        """Unauthenticated users cannot create orders."""
        url = reverse("payment-create-order")
        response = self.client.post(
            url, {"booking_id": self.booking.id}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_booking_not_found(self):
        """Returns 404 for non-existent booking."""
        self.client.force_authenticate(user=self.customer_user)
        url = reverse("payment-create-order")
        response = self.client.post(
            url, {"booking_id": 99999}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_duplicate_payment_for_confirmed_booking(self):
        """Cannot create order for booking with existing successful payment."""
        # Create a successful payment for the booking
        Payment.objects.create(
            booking=self.booking,
            customer=self.customer_user,
            razorpay_order_id="order_existing",
            razorpay_payment_id="pay_existing",
            amount=50.00,
            currency="INR",
            provider="RAZORPAY",
            status="SUCCESS",
            payment_method="razorpay",
            signature_verified=True,
            transaction_id="pay_existing",
        )
        # Update booking status to CONFIRMED
        self.booking.status = "CONFIRMED"
        self.booking.save()

        self.client.force_authenticate(user=self.customer_user)
        url = reverse("payment-create-order")
        response = self.client.post(
            url, {"booking_id": self.booking.id}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


@override_settings(
    RAZORPAY_KEY_ID="rzp_test_payment_suite",
    RAZORPAY_KEY_SECRET="test_suite_secret_only",
)
class PaymentVerificationAPITest(APITestCase):
    """Tests for Razorpay payment verification."""

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
            status="PENDING",
        )
        self.payment = Payment.objects.create(
            booking=self.booking,
            customer=self.customer_user,
            razorpay_order_id="order_test123",
            amount=50.00,
            currency="INR",
            provider="RAZORPAY",
            status="CREATED",
        )

    @override_settings(RAZORPAY_KEY_ID="", RAZORPAY_KEY_SECRET="")
    def test_verify_fails_closed_without_test_credentials(self):
        with patch("payments.views.razorpay_client.utility.verify_payment_signature") as mock_verify:
            self.client.force_authenticate(user=self.customer_user)
            response = self.client.post(
                reverse("payment-verify"),
                {
                    "razorpay_order_id": self.payment.razorpay_order_id,
                    "razorpay_payment_id": "pay_unverified",
                    "razorpay_signature": "unverified_signature",
                },
                format="json",
            )
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertIn("Razorpay test mode is unavailable", response.data["error"])
        mock_verify.assert_not_called()
        self.payment.refresh_from_db()
        self.booking.refresh_from_db()
        self.assertEqual(self.payment.status, "CREATED")
        self.assertEqual(self.booking.status, "PENDING")

    @patch("payments.views.razorpay_client.utility.verify_payment_signature")
    @patch("payments.views.razorpay_client.payment.fetch")
    def test_valid_signature_confirms_payment(self, mock_fetch, mock_verify):
        """Valid Razorpay signature confirms payment and booking."""
        mock_verify.return_value = True
        mock_fetch.return_value = {
            "id": "pay_test456",
            "order_id": "order_test123",
            "amount": 5000,
            "currency": "INR",
            "status": "captured",
        }

        self.client.force_authenticate(user=self.customer_user)
        url = reverse("payment-verify")
        response = self.client.post(
            url,
            {
                "razorpay_order_id": "order_test123",
                "razorpay_payment_id": "pay_test456",
                "razorpay_signature": "sig_test789",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "SUCCESS")

        # Verify payment updated
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, "SUCCESS")
        self.assertTrue(self.payment.signature_verified)
        self.assertEqual(self.payment.razorpay_payment_id, "pay_test456")

        # Verify booking confirmed
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, "CONFIRMED")

    @patch("payments.views.razorpay_client.utility.verify_payment_signature")
    @patch("payments.views.razorpay_client.payment.fetch")
    def test_payment_with_wrong_amount_is_rejected(self, mock_fetch, mock_verify):
        """A valid signature cannot confirm a payment for the wrong amount."""
        mock_verify.return_value = True
        mock_fetch.return_value = {
            "id": "pay_test_wrong_amount",
            "order_id": "order_test123",
            "amount": 4999,
            "currency": "INR",
            "status": "captured",
        }

        self.client.force_authenticate(user=self.customer_user)
        response = self.client.post(
            reverse("payment-verify"),
            {
                "razorpay_order_id": "order_test123",
                "razorpay_payment_id": "pay_test_wrong_amount",
                "razorpay_signature": "sig_test789",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["error"], "Payment amount does not match booking total."
        )
        self.payment.refresh_from_db()
        self.booking.refresh_from_db()
        self.assertEqual(self.payment.status, "FAILED")
        self.assertFalse(self.payment.signature_verified)
        self.assertEqual(self.booking.status, "PENDING")

    @patch("payments.views.razorpay_client.utility.verify_payment_signature")
    def test_invalid_signature_fails_payment(self, mock_verify):
        """Invalid Razorpay signature fails payment."""
        mock_verify.side_effect = Exception("Invalid signature")

        self.client.force_authenticate(user=self.customer_user)
        url = reverse("payment-verify")
        response = self.client.post(
            url,
            {
                "razorpay_order_id": "order_test123",
                "razorpay_payment_id": "pay_test456",
                "razorpay_signature": "invalid_sig",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Verify payment marked as FAILED
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, "FAILED")

    def test_duplicate_verification_is_idempotent(self):
        """Duplicate verification of already successful payment is idempotent."""
        self.payment.status = "SUCCESS"
        self.payment.signature_verified = True
        self.payment.razorpay_payment_id = "pay_existing"
        self.payment.save()

        self.client.force_authenticate(user=self.customer_user)
        url = reverse("payment-verify")
        response = self.client.post(
            url,
            {
                "razorpay_order_id": "order_test123",
                "razorpay_payment_id": "pay_existing",
                "razorpay_signature": "any_sig",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Payment already verified.")

    def test_customer_cannot_verify_others_payment(self):
        """Customer cannot verify another customer's payment."""
        # Create a separate booking and payment for the other customer
        other_booking = Booking.objects.create(
            customer=self.other_customer,
            event=self.event,
            quantity=1,
            unit_price=25.00,
            total_amount=25.00,
            status="PENDING",
        )
        other_payment = Payment.objects.create(
            booking=other_booking,
            customer=self.other_customer,
            razorpay_order_id="order_other",
            amount=25.00,
            currency="INR",
            provider="RAZORPAY",
            status="CREATED",
        )

        self.client.force_authenticate(user=self.customer_user)
        url = reverse("payment-verify")
        response = self.client.post(
            url,
            {
                "razorpay_order_id": "order_other",
                "razorpay_payment_id": "pay_other",
                "razorpay_signature": "sig",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_order_not_found(self):
        """Returns 404 for non-existent order."""
        self.client.force_authenticate(user=self.customer_user)
        url = reverse("payment-verify")
        response = self.client.post(
            url,
            {
                "razorpay_order_id": "order_nonexistent",
                "razorpay_payment_id": "pay_nonexistent",
                "razorpay_signature": "sig",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthenticated_cannot_verify(self):
        """Unauthenticated users cannot verify payments."""
        url = reverse("payment-verify")
        response = self.client.post(
            url,
            {
                "razorpay_order_id": "order_test123",
                "razorpay_payment_id": "pay_test456",
                "razorpay_signature": "sig",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PaymentListAPITest(APITestCase):
    """Tests for payment list views."""

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
            status="CONFIRMED",
        )
        self.booking2 = Booking.objects.create(
            customer=self.other_customer,
            event=self.event2,
            quantity=1,
            unit_price=30.00,
            total_amount=30.00,
            status="CONFIRMED",
        )
        self.payment1 = Payment.objects.create(
            booking=self.booking1,
            customer=self.customer_user,
            razorpay_order_id="order_1",
            razorpay_payment_id="pay_1",
            amount=50.00,
            currency="INR",
            provider="RAZORPAY",
            status="SUCCESS",
            signature_verified=True,
            transaction_id="pay_1",
        )
        self.payment2 = Payment.objects.create(
            booking=self.booking2,
            customer=self.other_customer,
            razorpay_order_id="order_2",
            razorpay_payment_id="pay_2",
            amount=30.00,
            currency="INR",
            provider="RAZORPAY",
            status="SUCCESS",
            signature_verified=True,
            transaction_id="pay_2",
        )

    def test_customer_sees_only_own_payments(self):
        """Customer sees only their own payments."""
        self.client.force_authenticate(user=self.customer_user)
        url = reverse("payment-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"]
        payment_ids = [p["id"] for p in results]
        self.assertIn(self.payment1.id, payment_ids)
        self.assertNotIn(self.payment2.id, payment_ids)

    def test_my_payments_endpoint(self):
        """My-payments endpoint returns customer's payments."""
        self.client.force_authenticate(user=self.customer_user)
        url = reverse("payment-my-payments")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"]
        for p in results:
            self.assertEqual(p["customer"], self.customer_user.id)

    def test_customer_cannot_access_my_payments(self):
        """Non-customer cannot access my-payments."""
        self.client.force_authenticate(user=self.organizer_user)
        url = reverse("payment-my-payments")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_organizer_sees_payments_for_own_events(self):
        """Organizer sees payments for their own events' bookings."""
        self.client.force_authenticate(user=self.organizer_user)
        url = reverse("payment-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"]
        payment_ids = [p["id"] for p in results]
        self.assertIn(self.payment1.id, payment_ids)
        self.assertIn(self.payment2.id, payment_ids)

    def test_admin_sees_all_payments(self):
        """Admin sees all payments."""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("payment-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"]
        payment_ids = [p["id"] for p in results]
        self.assertIn(self.payment1.id, payment_ids)
        self.assertIn(self.payment2.id, payment_ids)

    def test_customer_cannot_access_other_payment_detail(self):
        """Customer cannot access another customer's payment detail."""
        self.client.force_authenticate(user=self.customer_user)
        url = reverse("payment-detail", kwargs={"pk": self.payment2.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


@override_settings(
    RAZORPAY_KEY_ID="rzp_test_mock",
    RAZORPAY_KEY_SECRET="mock_test_secret",
)
class RazorpaySDKMockTest(APITestCase):
    """Tests for Razorpay SDK mock behavior."""

    def setUp(self):
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
            status="PENDING",
        )

    @patch("payments.views.razorpay_client.order.create")
    def test_razorpay_order_creation_api_call(self, mock_order_create):
        """Verify Razorpay order creation API is called with correct params."""
        mock_order_create.return_value = {
            "id": "order_mock123",
            "amount": 5000,
            "currency": "INR",
            "receipt": "booking_TEST12345678",
            "payment_capture": 1,
        }

        self.client.force_authenticate(user=self.customer_user)
        url = reverse("payment-create-order")
        response = self.client.post(url, {"booking_id": self.booking.id}, format="json")

        # Verify Razorpay was called with correct amount (in paise)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["key"], "rzp_test_mock")
        self.assertNotIn("mock_test_secret", str(response.data))
        mock_order_create.assert_called_once()
        call_args = mock_order_create.call_args[0][0]
        self.assertEqual(call_args["amount"], 5000)
        self.assertEqual(call_args["currency"], "INR")
        self.assertEqual(call_args["payment_capture"], 1)

    @patch("payments.views.razorpay_client.order.create")
    def test_razorpay_api_error_handled(self, mock_order_create):
        """Razorpay API errors are handled gracefully."""
        mock_order_create.side_effect = Exception("Razorpay API error")

        self.client.force_authenticate(user=self.customer_user)
        url = reverse("payment-create-order")
        response = self.client.post(
            url, {"booking_id": self.booking.id}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
