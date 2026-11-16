from rest_framework import serializers
from django.utils import timezone
from django.db import transaction
from .models import Booking
from events.models import Event


class BookingSerializer(serializers.ModelSerializer):
    """Serializer for booking detail view."""

    customer_email = serializers.ReadOnlyField(source="customer.email")
    event_title = serializers.ReadOnlyField(source="event.display_title")
    event_date = serializers.ReadOnlyField(source="event.event_date")

    class Meta:
        model = Booking
        fields = "__all__"
        read_only_fields = (
            "id",
            "booking_reference",
            "customer",
            "event",
            "unit_price",
            "total_amount",
            "status",
            "booking_date",
            "updated_at",
        )


class BookingListSerializer(serializers.ModelSerializer):
    """Serializer for booking list view (optimized)."""

    customer_email = serializers.ReadOnlyField(source="customer.email")
    event_title = serializers.ReadOnlyField(source="event.display_title")
    event_date = serializers.ReadOnlyField(source="event.event_date")
    start_time = serializers.ReadOnlyField(source="event.start_time")
    end_time = serializers.ReadOnlyField(source="event.end_time")
    venue = serializers.ReadOnlyField(source="event.venue")
    city = serializers.ReadOnlyField(source="event.city")
    event_poster = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = (
            "id",
            "booking_reference",
            "customer",
            "customer_email",
            "event",
            "event_title",
            "event_date",
            "start_time",
            "end_time",
            "venue",
            "city",
            "event_poster",
            "quantity",
            "unit_price",
            "total_amount",
            "status",
            "booking_date",
        )

    def get_event_poster(self, obj):
        if not obj.event.poster:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(obj.event.poster.url) if request else obj.event.poster.url


class BookingCreateSerializer(serializers.Serializer):
    """Serializer for booking creation with validation."""

    event = serializers.PrimaryKeyRelatedField(queryset=Event.objects.all())
    quantity = serializers.IntegerField(min_value=1)

    def validate_event(self, value):
        """Only APPROVED and upcoming events can be booked."""
        from django.utils import timezone

        if value.status != "APPROVED":
            raise serializers.ValidationError(
                "Only approved events can be booked."
            )

        # Check event date is not in the past
        event_datetime = timezone.datetime.combine(
            value.event_date, value.start_time
        )
        event_datetime = timezone.make_aware(event_datetime)
        if event_datetime <= timezone.now():
            raise serializers.ValidationError(
                "Cannot book past events."
            )

        # Check registration deadline
        if value.registration_deadline:
            deadline = value.registration_deadline
            if timezone.is_naive(deadline):
                deadline = timezone.make_aware(deadline)
            if timezone.now() > deadline:
                raise serializers.ValidationError(
                    "Registration deadline has passed for this event."
                )

        return value

    def validate_quantity(self, value):
        """Quantity must be greater than zero."""
        if value < 1:
            raise serializers.ValidationError(
                "Quantity must be greater than zero."
            )
        return value

    def validate(self, attrs):
        """Cross-field validation."""
        event = attrs.get("event")
        quantity = attrs.get("quantity")

        if event and quantity:
            if quantity > event.available_tickets:
                raise serializers.ValidationError(
                    {
                        "quantity": f"Only {event.available_tickets} tickets available."
                    }
                )

        return attrs

    def create(self, validated_data):
        """Create booking with atomic inventory update."""
        request = self.context.get("request")
        event = validated_data["event"]
        quantity = validated_data["quantity"]
        with transaction.atomic():
            # Lock the event row to prevent overselling
            event = Event.objects.select_for_update().get(pk=event.pk)

            # Re-check availability after lock
            if quantity > event.available_tickets:
                raise serializers.ValidationError(
                    {
                        "quantity": f"Only {event.available_tickets} tickets available."
                    }
                )

            # Calculate the price from the locked, current event row.
            unit_price = event.ticket_price
            total_amount = unit_price * quantity

            # Decrease available tickets
            event.available_tickets -= quantity
            event.save()

            # Create booking
            booking = Booking.objects.create(
                customer=request.user,
                event=event,
                quantity=quantity,
                unit_price=unit_price,
                total_amount=total_amount,
                status=Booking.Status.PENDING,
            )

        return booking
