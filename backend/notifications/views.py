from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view
from django.db import transaction
from django.db.models import Count, Q
from accounts.models import User
from bookings.models import Booking
from events.models import Event
from .models import Notification
from .serializers import (
    MarkAllReadResponseSerializer,
    NotificationSerializer,
    SendNotificationOptionsSerializer,
    SendNotificationResponseSerializer,
    SendNotificationSerializer,
    UnreadCountSerializer,
)


class IsAdministrator(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == User.Role.ADMIN
        )


@extend_schema_view(
    list=extend_schema(tags=["Notifications"]),
    retrieve=extend_schema(tags=["Notifications"]),
)
@extend_schema(tags=["Notifications"])
class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action in {"send", "send_options"}:
            return [permissions.IsAuthenticated(), IsAdministrator()]
        return super().get_permissions()

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).exclude(
            title__startswith="[DEMO]", message__startswith="[DEMO DATA]"
        )

    @extend_schema(
        tags=["Notifications"],
        summary="Get recipient options for an administrator notification",
        responses={200: SendNotificationOptionsSerializer},
    )
    @action(detail=False, methods=["get"], url_path="send-options")
    def send_options(self, request):
        customers = User.objects.filter(
            role=User.Role.CUSTOMER, is_active=True
        ).order_by("email")
        events = (
            Event.objects.annotate(
                recipient_count=Count(
                    "bookings__customer",
                    filter=Q(
                        bookings__status__in=[
                            Booking.Status.PENDING,
                            Booking.Status.CONFIRMED,
                        ],
                        bookings__customer__is_active=True,
                        bookings__customer__role=User.Role.CUSTOMER,
                    ),
                    distinct=True,
                )
            )
            .filter(recipient_count__gt=0)
            .order_by("-event_date", "id")
        )
        return Response({
            "customers": [
                {
                    "id": customer.id,
                    "email": customer.email,
                    "name": customer.get_full_name().strip() or customer.username,
                }
                for customer in customers
            ],
            "events": [
                {
                    "id": event.id,
                    "title": event.display_title,
                    "event_date": event.event_date,
                    "status": event.status,
                    "recipient_count": event.recipient_count,
                }
                for event in events
            ],
        })

    @extend_schema(
        tags=["Notifications"],
        summary="Save an in-app notification for selected customers",
        request=SendNotificationSerializer,
        responses={201: SendNotificationResponseSerializer},
    )
    @action(detail=False, methods=["post"], url_path="send")
    def send(self, request):
        serializer = SendNotificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        scope = values["recipient_scope"]
        if scope == "ALL_CUSTOMERS":
            recipients = User.objects.filter(
                role=User.Role.CUSTOMER, is_active=True
            )
        elif scope == "CUSTOMER":
            recipients = User.objects.filter(pk=values["customer"].pk)
        else:
            event = values["event"]
            recipients = User.objects.filter(
                role=User.Role.CUSTOMER,
                is_active=True,
                bookings__event=event,
                bookings__status__in=[Booking.Status.PENDING, Booking.Status.CONFIRMED],
            ).distinct()

        recipient_ids = list(recipients.values_list("id", flat=True))
        if not recipient_ids:
            return Response(
                {"detail": "No active customers match this recipient selection."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            Notification.objects.bulk_create([
                Notification(
                    user_id=user_id,
                    title=values["title"],
                    message=values["message"],
                    type=values["type"],
                    status=Notification.Status.PENDING,
                    sent_at=None,
                )
                for user_id in recipient_ids
            ])
        return Response(
            {
                "recipient_count": len(recipient_ids),
                "status": Notification.Status.PENDING,
                "delivery": "IN_APP_ONLY",
                "message": (
                    f"Notification saved to {len(recipient_ids)} customer inbox(es). "
                    "No external email, SMS, or push message was sent."
                ),
            },
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        tags=["Notifications"],
        summary="Get unread notification count",
        responses={200: UnreadCountSerializer},
    )
    @action(detail=False, methods=["get"], url_path="unread-count")
    def unread_count(self, request):
        count = self.get_queryset().filter(is_read=False).count()
        return Response({"unread_count": count})

    @extend_schema(
        tags=["Notifications"],
        summary="Mark all of the current user's notifications as read",
        request=None,
        responses={200: MarkAllReadResponseSerializer},
    )
    @action(detail=False, methods=["patch", "post"], url_path="mark-all-read")
    def mark_all_read(self, request):
        updated = self.get_queryset().filter(is_read=False).update(is_read=True)
        return Response({"updated": updated, "unread_count": 0})

    @extend_schema(
        tags=["Notifications"],
        summary="Mark one of the current user's notifications as read",
        request=None,
        responses={200: NotificationSerializer},
    )
    @action(detail=True, methods=["patch", "post"], url_path="mark-read")
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        if not notification.is_read:
            notification.is_read = True
            notification.save(update_fields=["is_read"])
        return Response(self.get_serializer(notification).data, status=status.HTTP_200_OK)
