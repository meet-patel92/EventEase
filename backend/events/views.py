from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from drf_spectacular.utils import extend_schema, extend_schema_view
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from .models import EventCategory, Event
from .serializers import (
    EventCategorySerializer,
    EventSerializer,
    EventListSerializer,
    EventCreateSerializer,
    EventStatusUpdateSerializer,
)
from .filters import EventFilter
from .permissions import (
    IsOrganizer,
    IsAdmin,
    IsCustomer,
    IsEventOwner,
    CanDeleteEvent,
    CanApproveOrReject,
    CanViewEvent,
)


@extend_schema_view(
    list=extend_schema(
        summary="List event categories",
        description="Get all event categories.",
        tags=["Events"],
    ),
    create=extend_schema(
        summary="Create event category",
        description="Create a new event category (Admin only).",
        tags=["Events"],
    ),
    retrieve=extend_schema(
        summary="Get event category",
        description="Get a single event category by ID.",
        tags=["Events"],
    ),
    update=extend_schema(
        summary="Update event category",
        description="Update an event category (Admin only).",
        tags=["Events"],
    ),
    destroy=extend_schema(
        summary="Delete event category",
        description="Delete an event category (Admin only).",
        tags=["Events"],
    ),
)
class EventCategoryViewSet(viewsets.ModelViewSet):
    """ViewSet for event categories."""

    queryset = EventCategory.objects.all()
    serializer_class = EventCategorySerializer
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["name", "description"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsAdmin()]
        return [AllowAny()]

    def perform_create(self, serializer):
        serializer.save()


@extend_schema_view(
    list=extend_schema(
        summary="List events",
        description="Get all events. Customers and unauthenticated users see only APPROVED events.",
        tags=["Events"],
    ),
    create=extend_schema(
        summary="Create event",
        description="Create a new event (Organizer only).",
        tags=["Events"],
    ),
    retrieve=extend_schema(
        summary="Get event",
        description="Get a single event by ID.",
        tags=["Events"],
    ),
    update=extend_schema(
        summary="Update event",
        description="Update an event (organizer only, own events).",
        tags=["Events"],
    ),
    partial_update=extend_schema(
        summary="Partial update event",
        description="Partially update an event (organizer only, own events).",
        tags=["Events"],
    ),
    destroy=extend_schema(
        summary="Delete event",
        description="Delete an event (organizer only, own PENDING/REJECTED events).",
        tags=["Events"],
    ),
)
class EventViewSet(viewsets.ModelViewSet):
    """ViewSet for events with role-based permissions and filtering."""

    queryset = Event.objects.all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = EventFilter
    search_fields = ["title", "description", "venue"]
    ordering_fields = ["event_date", "ticket_price", "created_at"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return EventListSerializer
        if self.action == "create":
            return EventCreateSerializer
        if self.action in ["approve", "reject"]:
            return EventStatusUpdateSerializer
        return EventSerializer

    def get_queryset(self):
        """Filter events based on user role."""
        user = self.request.user
        queryset = Event.objects.all()

        if not user or not user.is_authenticated:
            # Unauthenticated: only approved events
            return queryset.filter(status="APPROVED")

        if user.role == "ADMIN":
            # Admin: see all events
            return queryset

        if user.role == "ORGANIZER":
            # Organizer: own events + approved events
            return queryset.filter(organizer=user) | queryset.filter(
                status="APPROVED"
            )

        if user.role == "CUSTOMER":
            # Customer: only approved events
            return queryset.filter(status="APPROVED")

        return queryset.filter(status="APPROVED")

    def get_permissions(self):
        """Role-based permissions per action."""
        if self.action == "create":
            return [IsAuthenticated(), IsOrganizer()]
        if self.action in ["update", "partial_update"]:
            return [IsAuthenticated(), IsEventOwner()]
        if self.action == "destroy":
            return [IsAuthenticated(), CanDeleteEvent()]
        if self.action in ["approve", "reject"]:
            return [IsAuthenticated(), IsAdmin(), CanApproveOrReject()]
        if self.action == "my_events":
            return [IsAuthenticated(), IsOrganizer()]
        # list, retrieve: AllowAny (public can view approved events)
        return [AllowAny()]

    def perform_create(self, serializer):
        """Set organizer from authenticated user (never from client)."""
        serializer.save(organizer=self.request.user)

    def perform_update(self, serializer):
        """Ensure organizer cannot be changed."""
        serializer.save(organizer=self.get_object().organizer)

    @extend_schema(
        summary="Approve event",
        description="Approve a pending event (Admin only).",
        tags=["Events"],
    )
    @action(detail=True, methods=["patch"], url_path="approve")
    def approve(self, request, pk=None):
        """Approve an event (Admin only)."""
        event = self.get_object()
        if event.status != "PENDING":
            return Response(
                {"error": "Only pending events can be approved."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        event.status = "APPROVED"
        event.rejection_reason = None
        event.save()
        return Response(
            {"message": "Event approved successfully.", "status": event.status},
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        summary="Reject event",
        description="Reject a pending event with a reason (Admin only).",
        tags=["Events"],
    )
    @action(detail=True, methods=["patch"], url_path="reject")
    def reject(self, request, pk=None):
        """Reject an event (Admin only)."""
        event = self.get_object()
        if event.status != "PENDING":
            return Response(
                {"error": "Only pending events can be rejected."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = EventStatusUpdateSerializer(data=request.data)
        if serializer.is_valid():
            event.status = "REJECTED"
            event.rejection_reason = serializer.validated_data.get(
                "rejection_reason", ""
            )
            event.save()
            return Response(
                {
                    "message": "Event rejected successfully.",
                    "status": event.status,
                    "rejection_reason": event.rejection_reason,
                },
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="My events",
        description="Get events organized by the current organizer.",
        tags=["Events"],
    )
    @action(detail=False, methods=["get"], url_path="my-events")
    def my_events(self, request):
        """Get events organized by the current user."""
        if request.user.role != "ORGANIZER":
            return Response(
                {"error": "Only organizers can access this endpoint."},
                status=status.HTTP_403_FORBIDDEN,
            )
        events = Event.objects.filter(organizer=request.user)
        page = self.paginate_queryset(events)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(events, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="attendance")
    def attendance(self, request, pk=None):
        """Return paid ticket attendance for an event owned by this organizer."""
        if request.user.role != "ORGANIZER":
            return Response({"error": "Only organizers can view attendance."}, status=status.HTTP_403_FORBIDDEN)
        event = Event.objects.filter(pk=pk, organizer=request.user, status=Event.Status.APPROVED).first()
        if not event:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        from tickets.models import Ticket
        paid_tickets = Ticket.objects.filter(
            event=event,
            booking__status="CONFIRMED",
            payment__status="SUCCESS",
            payment__signature_verified=True,
        )
        total = paid_tickets.count()
        checked_in = paid_tickets.filter(status=Ticket.Status.USED).count()
        return Response({
            "event_id": event.id,
            "event_title": event.display_title,
            "total_paid_tickets": total,
            "checked_in_tickets": checked_in,
            "remaining_tickets": total - checked_in,
            "attendance_percentage": round(checked_in * 100 / total, 1) if total else 0,
        })
