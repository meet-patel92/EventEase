from rest_framework import serializers
from .models import Ticket


class TicketSerializer(serializers.ModelSerializer):
    """Serializer for ticket detail view."""

    customer_email = serializers.ReadOnlyField(source="customer.email")
    customer_name = serializers.SerializerMethodField()
    event_title = serializers.ReadOnlyField(source="event.display_title")
    event_date = serializers.ReadOnlyField(source="event.event_date")
    start_time = serializers.ReadOnlyField(source="event.start_time")
    end_time = serializers.ReadOnlyField(source="event.end_time")
    venue = serializers.ReadOnlyField(source="event.venue")
    city = serializers.ReadOnlyField(source="event.city")
    event_poster = serializers.SerializerMethodField()
    booking_reference = serializers.ReadOnlyField(source="booking.booking_reference")
    booking_id = serializers.ReadOnlyField(source="booking.id")
    booking_quantity = serializers.ReadOnlyField(source="booking.quantity")
    booking_total_amount = serializers.ReadOnlyField(source="booking.total_amount")
    booking_status = serializers.ReadOnlyField(source="booking.status")
    qr_code_url = serializers.SerializerMethodField()
    verification_url = serializers.SerializerMethodField()

    class Meta:
        model = Ticket
        fields = [
            "id",
            "ticket_number",
            "ticket_token",
            "booking",
            "payment",
            "customer",
            "customer_email",
            "customer_name",
            "event",
            "event_title",
            "event_date",
            "start_time",
            "end_time",
            "venue",
            "city",
            "event_poster",
            "booking_reference",
            "booking_id",
            "booking_quantity",
            "booking_total_amount",
            "booking_status",
            "qr_code",
            "qr_code_url",
            "verification_url",
            "status",
            "issued_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "ticket_number",
            "ticket_token",
            "booking",
            "payment",
            "customer",
            "event",
            "qr_code",
            "status",
            "issued_at",
            "created_at",
            "updated_at",
        ]

    def get_customer_name(self, obj):
        return f"{obj.customer.first_name} {obj.customer.last_name}".strip() or obj.customer.email

    def get_qr_code_url(self, obj):
        if obj.qr_code:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.qr_code.url)
            return obj.qr_code.url
        return None

    def get_verification_url(self, obj):
        return obj.get_qr_code_url()

    def get_event_poster(self, obj):
        if not obj.event or not obj.event.poster:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(obj.event.poster.url) if request else obj.event.poster.url


class TicketListSerializer(serializers.ModelSerializer):
    """Serializer for ticket list view (optimized)."""

    customer_email = serializers.ReadOnlyField(source="customer.email")
    event_title = serializers.ReadOnlyField(source="event.display_title")
    event_date = serializers.ReadOnlyField(source="event.event_date")
    start_time = serializers.ReadOnlyField(source="event.start_time")
    end_time = serializers.ReadOnlyField(source="event.end_time")
    venue = serializers.ReadOnlyField(source="event.venue")
    city = serializers.ReadOnlyField(source="event.city")
    event_poster = serializers.SerializerMethodField()
    booking_reference = serializers.ReadOnlyField(source="booking.booking_reference")
    booking_id = serializers.ReadOnlyField(source="booking.id")
    booking_quantity = serializers.ReadOnlyField(source="booking.quantity")
    booking_total_amount = serializers.ReadOnlyField(source="booking.total_amount")
    booking_status = serializers.ReadOnlyField(source="booking.status")
    qr_code_url = serializers.SerializerMethodField()

    class Meta:
        model = Ticket
        fields = [
            "id",
            "ticket_number",
            "booking",
            "event",
            "event_title",
            "event_date",
            "start_time",
            "end_time",
            "venue",
            "city",
            "event_poster",
            "booking_reference",
            "booking_id",
            "booking_quantity",
            "booking_total_amount",
            "booking_status",
            "customer_email",
            "qr_code_url",
            "status",
            "issued_at",
        ]

    def get_qr_code_url(self, obj):
        if obj.qr_code:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.qr_code.url)
            return obj.qr_code.url
        return None

    def get_event_poster(self, obj):
        if not obj.event or not obj.event.poster:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(obj.event.poster.url) if request else obj.event.poster.url


class TicketDownloadSerializer(serializers.Serializer):
    """Serializer for ticket download response."""

    ticket_number = serializers.CharField()
    download_url = serializers.CharField()
    content_type = serializers.CharField(default="application/pdf")


class TicketVerifySerializer(serializers.Serializer):
    ticket_token = serializers.CharField(max_length=100, trim_whitespace=True)
    event_id = serializers.IntegerField(min_value=1)
