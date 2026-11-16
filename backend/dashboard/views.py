from django.db.models import Count, Q, Sum
from django.utils import timezone
from rest_framework import permissions, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from bookings.models import Booking
from events.models import Event
from payments.models import Payment
from tickets.models import Ticket
from .models import DashboardStat
from .serializers import DashboardStatSerializer


class IsAdminRole(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == "ADMIN")


class DashboardStatViewSet(viewsets.ModelViewSet):
    """Keep legacy stats maintenance available only to admins."""

    queryset = DashboardStat.objects.all()
    serializer_class = DashboardStatSerializer
    permission_classes = [IsAdminRole]


class DashboardOverviewView(APIView):
    """Return live, role-scoped aggregates for the signed-in user."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        today = timezone.localdate()

        if user.role == User.Role.CUSTOMER:
            bookings = Booking.objects.filter(customer=user)
            confirmed = bookings.filter(status=Booking.Status.CONFIRMED)
            upcoming = confirmed.filter(event__event_date__gte=today).select_related("event").order_by("event__event_date")
            recent = bookings.select_related("event").order_by("-booking_date")[:6]
            return Response({
                "role": user.role,
                "cards": [
                    {"key": "bookings", "label": "Total bookings", "value": bookings.count()},
                    {"key": "confirmed", "label": "Confirmed bookings", "value": confirmed.count()},
                    {"key": "upcoming", "label": "Upcoming events", "value": upcoming.count()},
                    {"key": "tickets", "label": "Tickets", "value": Ticket.objects.filter(customer=user).count()},
                ],
                "upcoming_events": [
                    {"booking_id": item.id, "reference": item.booking_reference, "event": item.event.display_title,
                     "date": item.event.event_date, "venue": item.event.venue, "quantity": item.quantity}
                    for item in upcoming[:8]
                ],
                "recent_bookings": [
                    {"id": item.id, "reference": item.booking_reference, "event": item.event.display_title,
                     "status": item.status, "quantity": item.quantity, "total": item.total_amount,
                     "date": item.booking_date}
                    for item in recent
                ],
            })

        if user.role == User.Role.ORGANIZER:
            events = Event.objects.filter(organizer=user)
            bookings = Booking.objects.filter(event__organizer=user)
            successful_payments = Payment.objects.filter(
                booking__event__organizer=user,
                status=Payment.Status.SUCCESS,
                signature_verified=True,
            )
            event_rows = events.annotate(
                booking_count=Count("bookings", distinct=True),
                confirmed_count=Count("bookings", filter=Q(bookings__status=Booking.Status.CONFIRMED), distinct=True),
                issued_tickets=Count("tickets", distinct=True),
            ).order_by("event_date")
            revenue_by_event = dict(
                successful_payments.values("booking__event_id")
                .annotate(total=Sum("amount"))
                .values_list("booking__event_id", "total")
            )
            return Response({
                "role": user.role,
                "cards": [
                    {"key": "events", "label": "Total events", "value": events.count()},
                    {"key": "pending", "label": "Pending events", "value": events.filter(status=Event.Status.PENDING).count()},
                    {"key": "approved", "label": "Approved events", "value": events.filter(status=Event.Status.APPROVED).count()},
                    {"key": "bookings", "label": "Bookings", "value": bookings.count()},
                    {"key": "confirmed", "label": "Confirmed bookings", "value": bookings.filter(status=Booking.Status.CONFIRMED).count()},
                    {"key": "tickets", "label": "Tickets issued", "value": Ticket.objects.filter(event__organizer=user).count()},
                    {"key": "revenue", "label": "Verified revenue (INR)", "value": successful_payments.aggregate(total=Sum("amount"))["total"] or 0},
                    {"key": "upcoming", "label": "Upcoming events", "value": events.filter(event_date__gte=today).count()},
                ],
                "event_bookings": [
                    {"id": item.id, "title": item.title, "date": item.event_date, "status": item.status,
                     "bookings": item.booking_count, "confirmed": item.confirmed_count,
                     "tickets": item.issued_tickets, "revenue": revenue_by_event.get(item.id, 0)}
                    for item in event_rows[:20]
                ],
            })

        if user.role == User.Role.ADMIN:
            verified_payments = Payment.objects.filter(
                status=Payment.Status.SUCCESS,
                signature_verified=True,
            )
            recent_bookings = Booking.objects.select_related("customer", "event").order_by("-booking_date")[:6]
            return Response({
                "role": user.role,
                "cards": [
                    {"key": "users", "label": "Total users", "value": User.objects.count()},
                    {"key": "customers", "label": "Customers", "value": User.objects.filter(role=User.Role.CUSTOMER).count()},
                    {"key": "organizers", "label": "Organizers", "value": User.objects.filter(role=User.Role.ORGANIZER).count()},
                    {"key": "events", "label": "Total events", "value": Event.objects.count()},
                    {"key": "pending_events", "label": "Pending events", "value": Event.objects.filter(status=Event.Status.PENDING).count()},
                    {"key": "approved_events", "label": "Approved events", "value": Event.objects.filter(status=Event.Status.APPROVED).count()},
                    {"key": "rejected_events", "label": "Rejected events", "value": Event.objects.filter(status=Event.Status.REJECTED).count()},
                    {"key": "bookings", "label": "Total bookings", "value": Booking.objects.count()},
                    {"key": "confirmed_bookings", "label": "Confirmed bookings", "value": Booking.objects.filter(status=Booking.Status.CONFIRMED).count()},
                    {"key": "payments", "label": "Total payments", "value": Payment.objects.count()},
                    {"key": "revenue", "label": "Verified revenue (INR)", "value": verified_payments.aggregate(total=Sum("amount"))["total"] or 0},
                ],
                "recent_bookings": [
                    {"id": item.id, "reference": item.booking_reference, "customer": item.customer.email,
                     "event": item.event.display_title, "status": item.status, "total": item.total_amount,
                     "date": item.booking_date}
                    for item in recent_bookings
                ],
            })

        return Response({"detail": "This account has no dashboard role."}, status=403)
