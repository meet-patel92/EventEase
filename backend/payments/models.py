from django.db import models


class Payment(models.Model):
    class Status(models.TextChoices):
        CREATED = "CREATED", "Created"
        SUCCESS = "SUCCESS", "Success"
        FAILED = "FAILED", "Failed"
        REFUNDED = "REFUNDED", "Refunded"

    class Provider(models.TextChoices):
        RAZORPAY = "RAZORPAY", "Razorpay"

    booking = models.ForeignKey(
        "bookings.Booking",
        on_delete=models.CASCADE,
        related_name="payments",
    )
    customer = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="payments"
    )
    razorpay_order_id = models.CharField(max_length=100, unique=True, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, unique=True, blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="INR")
    provider = models.CharField(max_length=20, choices=Provider.choices, default=Provider.RAZORPAY)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.CREATED)
    payment_method = models.CharField(max_length=50, blank=True, null=True)
    signature_verified = models.BooleanField(default=False)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "payments"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["razorpay_order_id"]),
            models.Index(fields=["razorpay_payment_id"]),
            models.Index(fields=["customer"]),
            models.Index(fields=["booking"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"Payment {self.razorpay_order_id or self.id} - {self.status}"
