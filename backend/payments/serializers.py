from rest_framework import serializers
from .models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    """Serializer for payment detail view."""

    customer_email = serializers.ReadOnlyField(source="customer.email")
    booking_reference = serializers.ReadOnlyField(source="booking.booking_reference")

    class Meta:
        model = Payment
        fields = [
            "id",
            "booking",
            "booking_reference",
            "customer",
            "customer_email",
            "razorpay_order_id",
            "razorpay_payment_id",
            "amount",
            "currency",
            "provider",
            "status",
            "payment_method",
            "signature_verified",
            "transaction_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "booking",
            "customer",
            "razorpay_order_id",
            "razorpay_payment_id",
            "amount",
            "currency",
            "provider",
            "status",
            "payment_method",
            "signature_verified",
            "transaction_id",
            "created_at",
            "updated_at",
        ]


class PaymentListSerializer(serializers.ModelSerializer):
    """Serializer for payment list view (optimized)."""

    customer_email = serializers.ReadOnlyField(source="customer.email")
    booking_reference = serializers.ReadOnlyField(source="booking.booking_reference")

    class Meta:
        model = Payment
        fields = [
            "id",
            "booking",
            "booking_reference",
            "customer_email",
            "razorpay_order_id",
            "amount",
            "currency",
            "status",
            "payment_method",
            "created_at",
        ]


class PaymentCreateOrderSerializer(serializers.Serializer):
    """Serializer for creating a Razorpay order."""

    booking_id = serializers.IntegerField(min_value=1)


class PaymentVerifySerializer(serializers.Serializer):
    """Serializer for verifying a Razorpay payment."""

    razorpay_order_id = serializers.CharField(max_length=100)
    razorpay_payment_id = serializers.CharField(max_length=100)
    razorpay_signature = serializers.CharField(max_length=255)
