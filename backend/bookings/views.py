from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from drf_spectacular.utils import extend_schema, extend_schema_view
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db import transaction
from django.utils import timezone
from datetime import datetime
from rest_framework.exceptions import ValidationError
from .models import Booking
from .serializers import (
    BookingSerializer,
    BookingListSerializer,
    BookingCreateSerializer,
)
from .filters import BookingFilter
from .permissions import (
    IsCustomer,
    IsBookingOwner,
    CanViewEventBookings,
)


@extend_schema_view(
    list=extend_schema(
        summary="List bookings",
        description="Get bookings. Customers see their own, organizers see their events' bookings, admins see all.",
        tags=["Bookings"],
    ),
    create=extend_schema(
        summary="Create booking",
        description="Book tickets for an event (Customer only).",
        tags=["Bookings"],
    ),
    retrieve=extend_schema(
        summary="Get booking",
        description="Get a single booking by ID.",
        tags=["Bookings"],
    ),
    destroy=extend_schema(
        summary="Cancel booking",
        description="Cancel a booking (customer only, own bookings).",
        tags=["Bookings"],
    ),
)
class BookingViewSet(viewsets.ModelViewSet):
    """ViewSet for bookings with role-based permissions and filtering."""

    queryset = Booking.objects.select_related("customer", "event", "event__organizer")
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = BookingFilter
    search_fields = ["booking_reference", "event__title"]
    ordering_fields = ["booking_date", "total_amount"]
    ordering = ["-booking_date"]

    def get_serializer_class(self):
        if self.action == "list":
            return BookingListSerializer
        if self.action == "create":
            return BookingCreateSerializer
        return BookingSerializer

    def get_queryset(self):
        """Filter bookings based on user role and action."""
        user = self.request.user
        queryset = Booking.objects.all()

        if not user or not user.is_authenticated:
            return queryset.none()

        # For cancel/destroy, only allow access to own bookings (404 not 403)
        if self.action in ["destroy", "cancel"]:
            if user.role == "ADMIN":
                return queryset
            return queryset.filter(customer=user)

        if user.role == "ADMIN":
            return queryset

        if user.role == "ORGANIZER":
            # Organizer: bookings for their own events
            return queryset.filter(event__organizer=user)

        if user.role == "CUSTOMER":
            # Customer: only own bookings
            return queryset.filter(customer=user)

        return queryset.none()

    def get_permissions(self):
        """Role-based permissions per action."""
        if self.action == "create":
            return [IsAuthenticated(), IsCustomer()]
        if self.action in ["update", "partial_update"]:
            return [IsAuthenticated(), IsBookingOwner()]
        if self.action == "destroy":
            return [IsAuthenticated(), IsBookingOwner()]
        if self.action == "cancel":
            return [IsAuthenticated(), IsBookingOwner()]
        if self.action == "my_bookings":
            return [IsAuthenticated(), IsCustomer()]
        # list, retrieve
        return [IsAuthenticated(), CanViewEventBookings()]

    def perform_create(self, serializer):
        """Create booking with customer set from request."""
        serializer.save(customer=self.request.user)

    def create(self, request, *args, **kwargs):
        """Create booking and return full booking details."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        # Return full booking details using BookingSerializer
        booking = serializer.instance
        response_serializer = BookingSerializer(booking, context=self.get_serializer_context())
        headers = self.get_success_headers(response_serializer.data)
        return Response(
            response_serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )

    def perform_destroy(self, instance):
        """Cancel booking and restore tickets."""
        self._cancel_booking(instance)

    def _cancel_booking(self, booking):
        """Cancel an unpaid/future booking once and release reserved inventory."""
        with transaction.atomic():
            locked_booking = Booking.objects.select_for_update().select_related("event").get(pk=booking.pk)
            if locked_booking.status not in [Booking.Status.PENDING, Booking.Status.CONFIRMED]:
                raise ValidationError("Only pending or confirmed bookings can be cancelled.")

            if locked_booking.payments.filter(status="SUCCESS").exists():
                raise ValidationError("Paid bookings cannot be cancelled until a refund is available.")

            starts_at = timezone.make_aware(
                datetime.combine(locked_booking.event.event_date, locked_booking.event.start_time),
                timezone.get_current_timezone(),
            )
            if starts_at <= timezone.now():
                raise ValidationError("Bookings cannot be cancelled after the event has started.")

            event = locked_booking.event.__class__.objects.select_for_update().get(
                pk=locked_booking.event_id
            )

            event.available_tickets = min(
                event.total_tickets, event.available_tickets + locked_booking.quantity
            )
            event.save()

            locked_booking.status = Booking.Status.CANCELLED
            locked_booking.save(update_fields=["status", "updated_at"])

            from tickets.models import Ticket

            Ticket.objects.filter(booking=locked_booking).exclude(
                status=Ticket.Status.CANCELLED
            ).update(status=Ticket.Status.CANCELLED)
            return locked_booking

    @extend_schema(
        summary="Cancel booking",
        description="Cancel a booking and restore tickets (customer only, own bookings).",
        tags=["Bookings"],
    )
    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        """Cancel a booking (customer only)."""
        booking = self._cancel_booking(self.get_object())
        booking.refresh_from_db()

        return Response(
            {
                "message": "Booking cancelled successfully.",
                "status": booking.status,
                "booking_reference": booking.booking_reference,
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        summary="My bookings",
        description="Get bookings for the current customer.",
        tags=["Bookings"],
    )
    @action(detail=False, methods=["get"], url_path="my-bookings")
    def my_bookings(self, request):
        """Get bookings for the current customer."""
        if request.user.role != "CUSTOMER":
            return Response(
                {"error": "Only customers can access this endpoint."},
                status=status.HTTP_403_FORBIDDEN,
            )
        bookings = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(bookings)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(bookings, many=True)
        return Response(serializer.data)
