from django.db import models
from django.utils.crypto import get_random_string


class Booking(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        CONFIRMED = "CONFIRMED", "Confirmed"
        CANCELLED = "CANCELLED", "Cancelled"
        EXPIRED = "EXPIRED", "Expired"

    booking_reference = models.CharField(max_length=20, unique=True, blank=True)
    customer = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="bookings"
    )
    event = models.ForeignKey(
        "events.Event", on_delete=models.CASCADE, related_name="bookings"
    )
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    booking_date = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "bookings"
        ordering = ("-booking_date",)
        indexes = [
            models.Index(fields=["customer"]),
            models.Index(fields=["event"]),
            models.Index(fields=["status"]),
            models.Index(fields=["booking_reference"]),
        ]

    def __str__(self):
        return f"Booking {self.booking_reference} - {self.customer.email}"

    def save(self, *args, **kwargs):
        if not self.booking_reference:
            self.booking_reference = "BM" + get_random_string(8).upper()
        super().save(*args, **kwargs)
