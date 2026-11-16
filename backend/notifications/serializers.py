from rest_framework import serializers
from accounts.models import User
from events.models import Event
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ("id", "user", "title", "message", "type", "status", "is_read", "created_at", "sent_at")
        read_only_fields = fields


class UnreadCountSerializer(serializers.Serializer):
    unread_count = serializers.IntegerField()


class MarkAllReadResponseSerializer(serializers.Serializer):
    updated = serializers.IntegerField()
    unread_count = serializers.IntegerField()


class SendNotificationSerializer(serializers.Serializer):
    RECIPIENT_SCOPES = (
        ("ALL_CUSTOMERS", "All customers"),
        ("CUSTOMER", "Specific customer"),
        ("EVENT_CUSTOMERS", "Customers with bookings for an event"),
    )

    title = serializers.CharField(max_length=200, allow_blank=False, trim_whitespace=True)
    message = serializers.CharField(allow_blank=False, trim_whitespace=True)
    type = serializers.ChoiceField(choices=Notification.Type.choices)
    recipient_scope = serializers.ChoiceField(choices=RECIPIENT_SCOPES)
    customer = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role=User.Role.CUSTOMER, is_active=True),
        required=False,
    )
    event = serializers.PrimaryKeyRelatedField(
        queryset=Event.objects.all(), required=False
    )

    def validate(self, attrs):
        scope = attrs["recipient_scope"]
        customer = attrs.get("customer")
        event = attrs.get("event")
        if scope == "ALL_CUSTOMERS" and (customer or event):
            raise serializers.ValidationError(
                "Do not select a customer or event when notifying all customers."
            )
        if scope == "CUSTOMER" and (not customer or event):
            raise serializers.ValidationError(
                {"customer": "Select one customer and leave event empty."}
            )
        if scope == "EVENT_CUSTOMERS" and (not event or customer):
            raise serializers.ValidationError(
                {"event": "Select an event and leave customer empty."}
            )
        return attrs


class SendNotificationResponseSerializer(serializers.Serializer):
    recipient_count = serializers.IntegerField()
    status = serializers.ChoiceField(choices=Notification.Status.choices)
    delivery = serializers.ChoiceField(choices=[("IN_APP_ONLY", "In-app only")])
    message = serializers.CharField()


class NotificationCustomerOptionSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    email = serializers.EmailField()
    name = serializers.CharField()


class NotificationEventOptionSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    event_date = serializers.DateField()
    status = serializers.ChoiceField(choices=Event.Status.choices)
    recipient_count = serializers.IntegerField()


class SendNotificationOptionsSerializer(serializers.Serializer):
    customers = NotificationCustomerOptionSerializer(many=True)
    events = NotificationEventOptionSerializer(many=True)
