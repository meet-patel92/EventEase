import razorpay
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, extend_schema_view

from .models import Payment
from .serializers import (
    PaymentSerializer,
    PaymentListSerializer,
    PaymentCreateOrderSerializer,
    PaymentVerifySerializer,
)
from .permissions import IsCustomer, IsPaymentOwner, CanViewPayment


# Initialize Razorpay client
razorpay_client = razorpay.Client(
    auth=(
        settings.RAZORPAY_KEY_ID,
        settings.RAZORPAY_KEY_SECRET,
    )
)

RAZORPAY_TEST_MODE_CONFIGURATION_ERROR = (
    "Razorpay test mode is unavailable. Configure a test Key ID starting with "
    "rzp_test_ and its matching RAZORPAY_KEY_SECRET in backend/.env, then "
    "restart Django. Live keys are not accepted."
)


def razorpay_test_mode_ready():
    """Return whether real, non-placeholder Razorpay test credentials are set."""
    key_id = (settings.RAZORPAY_KEY_ID or "").strip()
    key_secret = (settings.RAZORPAY_KEY_SECRET or "").strip()
    placeholder_markers = ("your_", "placeholder", "replace_me", "replace-with", "replace with", "example")
    return (
        key_id.startswith("rzp_test_")
        and len(key_id) > len("rzp_test_")
        and bool(key_secret)
        and not any(marker in key_id.lower() for marker in placeholder_markers)
        and not any(marker in key_secret.lower() for marker in placeholder_markers)
    )


@extend_schema_view(
    list=extend_schema(
        summary="List payments",
        description="Get payments. Customers see their own, organizers see their events' payments, admins see all.",
        tags=["Payments"],
    ),
    retrieve=extend_schema(
        summary="Get payment",
        description="Get a single payment by ID.",
        tags=["Payments"],
    ),
    create_order=extend_schema(
        summary="Create Razorpay order",
        description="Create a Razorpay order for a booking payment (Customer only).",
        tags=["Payments"],
    ),
    verify=extend_schema(
        summary="Verify Razorpay payment",
        description="Verify a Razorpay payment signature and confirm booking.",
        tags=["Payments"],
    ),
    my_payments=extend_schema(
        summary="My payments",
        description="Get payments for the current customer.",
        tags=["Payments"],
    ),
)
class PaymentViewSet(viewsets.ModelViewSet):
    """ViewSet for payments with Razorpay integration."""

    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    http_method_names = ["get", "post"]

    def get_serializer_class(self):
        if self.action == "list":
            return PaymentListSerializer
        if self.action == "create_order":
            return PaymentCreateOrderSerializer
        if self.action == "verify":
            return PaymentVerifySerializer
        return PaymentSerializer

    def get_queryset(self):
        """Filter payments based on user role."""
        user = self.request.user
        queryset = Payment.objects.all()

        if not user or not user.is_authenticated:
            return queryset.none()

        if user.role == "ADMIN":
            return queryset

        if user.role == "ORGANIZER":
            # Organizer: payments for their own events' bookings
            return queryset.filter(booking__event__organizer=user)

        if user.role == "CUSTOMER":
            # Customer: only own payments
            return queryset.filter(customer=user)

        return queryset.none()

    def get_permissions(self):
        """Role-based permissions per action."""
        if self.action == "create_order":
            return [IsAuthenticated(), IsCustomer()]
        if self.action == "verify":
            return [IsAuthenticated(), IsCustomer()]
        if self.action in ["update", "partial_update", "destroy"]:
            return [IsAuthenticated(), IsPaymentOwner()]
        if self.action == "my_payments":
            return [IsAuthenticated(), IsCustomer()]
        # list, retrieve
        return [IsAuthenticated(), CanViewPayment()]

    @extend_schema(
        summary="Create Razorpay order",
        description="Create a Razorpay order for a booking payment (Customer only).",
        tags=["Payments"],
    )
    @action(detail=False, methods=["post"], url_path="create-order")
    def create_order(self, request):
        """Create a Razorpay order for a booking."""
        serializer = PaymentCreateOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        booking_id = serializer.validated_data["booking_id"]

        from bookings.models import Booking

        with transaction.atomic():
            try:
                booking = (
                    Booking.objects.select_for_update()
                    .select_related("event")
                    .get(id=booking_id)
                )
            except Booking.DoesNotExist:
                return Response(
                    {"error": "Booking not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            if booking.customer_id != request.user.id:
                return Response(
                    {"error": "You can only pay for your own bookings."},
                    status=status.HTTP_403_FORBIDDEN,
                )
            if booking.status != "PENDING":
                return Response(
                    {"error": f"Booking is already {booking.status.lower()}. Cannot create payment."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if booking.payments.filter(status="SUCCESS").exists():
                return Response(
                    {"error": "Payment already completed for this booking."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if not razorpay_test_mode_ready():
                return Response(
                    {"error": RAZORPAY_TEST_MODE_CONFIGURATION_ERROR},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )

            # Reuse a pending order on retry; preserve failed attempts for audit.
            payment = booking.payments.filter(status="CREATED").order_by("-created_at").first()
            if payment:
                return Response(
                    {
                        "order_id": payment.razorpay_order_id,
                        "amount": int(payment.amount * 100),
                        "currency": payment.currency,
                        "booking_id": booking.id,
                        "booking_reference": booking.booking_reference,
                        "key": settings.RAZORPAY_KEY_ID,
                    },
                    status=status.HTTP_200_OK,
                )

            amount = int(booking.total_amount * 100)
            try:
                razorpay_order = razorpay_client.order.create(
                    {
                        "amount": amount,
                        "currency": "INR",
                        "receipt": f"booking_{booking.booking_reference}",
                        "payment_capture": 1,
                    }
                )
            except Exception:
                return Response(
                    {"error": "Failed to create a Razorpay test order."},
                    status=status.HTTP_502_BAD_GATEWAY,
                )

            payment = Payment.objects.create(
                booking=booking,
                customer=request.user,
                razorpay_order_id=razorpay_order["id"],
                amount=booking.total_amount,
                currency="INR",
                provider="RAZORPAY",
                status="CREATED",
            )

            return Response(
                {
                    "order_id": payment.razorpay_order_id,
                    "amount": amount,
                    "currency": payment.currency,
                    "booking_id": booking.id,
                    "booking_reference": booking.booking_reference,
                    "key": settings.RAZORPAY_KEY_ID,
                },
                status=status.HTTP_201_CREATED,
            )

    @extend_schema(
        summary="Verify Razorpay payment",
        description="Verify a Razorpay payment signature and confirm booking.",
        tags=["Payments"],
    )
    @action(detail=False, methods=["post"], url_path="verify")
    @transaction.atomic
    def verify(self, request):
        """Verify a Razorpay payment signature."""
        serializer = PaymentVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        razorpay_order_id = serializer.validated_data["razorpay_order_id"]
        razorpay_payment_id = serializer.validated_data["razorpay_payment_id"]
        razorpay_signature = serializer.validated_data["razorpay_signature"]

        try:
            payment = Payment.objects.select_for_update().get(
                razorpay_order_id=razorpay_order_id
            )
        except Payment.DoesNotExist:
            return Response(
                {"error": "Payment order not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Security: Only the payment owner can verify
        if payment.customer != request.user:
            return Response(
                {"error": "You can only verify your own payments."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Idempotency: If already verified, return success
        if payment.status == "SUCCESS":
            return Response(
                {
                    "message": "Payment already verified.",
                    "payment_id": payment.id,
                    "status": payment.status,
                },
                status=status.HTTP_200_OK,
            )

        from bookings.models import Booking

        booking = Booking.objects.select_for_update().get(pk=payment.booking_id)
        if booking.status != "PENDING":
            return Response(
                {"error": "This booking is no longer pending and cannot be confirmed by this payment."},
                status=status.HTTP_409_CONFLICT,
            )

        if booking.customer_id != payment.customer_id:
            return Response(
                {"error": "Payment owner does not match the booking owner."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not razorpay_test_mode_ready():
            return Response(
                {"error": RAZORPAY_TEST_MODE_CONFIGURATION_ERROR},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        # Verify signature with Razorpay SDK
        try:
            razorpay_client.utility.verify_payment_signature(
                {
                    "razorpay_order_id": razorpay_order_id,
                    "razorpay_payment_id": razorpay_payment_id,
                    "razorpay_signature": razorpay_signature,
                }
            )
        except Exception:
            # Signature verification failed - record failed payment
            payment.status = "FAILED"
            payment.razorpay_payment_id = razorpay_payment_id
            payment.save(update_fields=["status", "razorpay_payment_id", "updated_at"])
            return Response(
                {"error": "Invalid payment signature."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Fetch payment details from Razorpay server to verify amount
        try:
            razorpay_payment = razorpay_client.payment.fetch(razorpay_payment_id)
        except Exception:
            payment.status = "FAILED"
            payment.razorpay_payment_id = razorpay_payment_id
            payment.save(update_fields=["status", "razorpay_payment_id", "updated_at"])
            return Response(
                {"error": "Failed to verify payment with Razorpay."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Verify amount matches booking total_amount (Razorpay stores amount in paise)
        razorpay_amount = razorpay_payment.get("amount", 0)  # amount in paise
        expected_amount = int(booking.total_amount * 100)  # convert to paise
        if razorpay_amount != expected_amount:
            payment.status = "FAILED"
            payment.razorpay_payment_id = razorpay_payment_id
            payment.signature_verified = False
            payment.save(
                update_fields=[
                    "status",
                    "razorpay_payment_id",
                    "signature_verified",
                    "updated_at",
                ]
            )
            return Response(
                {"error": "Payment amount does not match booking total."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Verify currency matches
        razorpay_currency = razorpay_payment.get("currency", "INR")
        if razorpay_currency != payment.currency:
            payment.status = "FAILED"
            payment.razorpay_payment_id = razorpay_payment_id
            payment.signature_verified = False
            payment.save(
                update_fields=[
                    "status",
                    "razorpay_payment_id",
                    "signature_verified",
                    "updated_at",
                ]
            )
            return Response(
                {"error": "Payment currency does not match booking currency."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if razorpay_payment.get("order_id") != razorpay_order_id:
            payment.status = "FAILED"
            payment.razorpay_payment_id = razorpay_payment_id
            payment.signature_verified = False
            payment.save(
                update_fields=["status", "razorpay_payment_id", "signature_verified", "updated_at"]
            )
            return Response(
                {"error": "Payment does not belong to this Razorpay order."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if razorpay_payment.get("status") != "captured":
            payment.status = "FAILED"
            payment.razorpay_payment_id = razorpay_payment_id
            payment.save(update_fields=["status", "razorpay_payment_id", "updated_at"])
            return Response(
                {"error": "Razorpay has not captured this payment."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Signature verified - update payment and booking
        with transaction.atomic():
            payment.razorpay_payment_id = razorpay_payment_id
            payment.signature_verified = True
            payment.status = "SUCCESS"
            payment.payment_method = "razorpay"
            payment.transaction_id = razorpay_payment_id
            payment.save()

            booking.status = "CONFIRMED"
            booking.save(update_fields=["status", "updated_at"])

            # Issue any missing tickets after successful payment. This is
            # idempotent if tickets were already issued for a confirmed booking.
            from tickets.services import ensure_booking_tickets

            ensure_booking_tickets(booking, payment=payment)

        return Response(
            {
                "message": "Payment verified successfully.",
                "payment_id": payment.id,
                "status": payment.status,
                "booking_id": booking.id,
                "booking_status": booking.status,
                "tickets_generated": booking.quantity,
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        summary="My payments",
        description="Get payments for the current customer.",
        tags=["Payments"],
    )
    @action(detail=False, methods=["get"], url_path="my-payments")
    def my_payments(self, request):
        """Get payments for the current customer."""
        if request.user.role != "CUSTOMER":
            return Response(
                {"error": "Only customers can access this endpoint."},
                status=status.HTTP_403_FORBIDDEN,
            )
        payments = Payment.objects.filter(customer=request.user)
        page = self.paginate_queryset(payments)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(payments, many=True)
        return Response(serializer.data)
