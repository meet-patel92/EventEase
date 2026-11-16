import io
import qrcode
from PIL import Image as PILImage
from django.db import models
from django.utils.crypto import get_random_string
from django.utils.text import slugify
from django.core.files.base import ContentFile


class Ticket(models.Model):
    class Status(models.TextChoices):
        VALID = "VALID", "Valid"
        USED = "USED", "Used"
        CANCELLED = "CANCELLED", "Cancelled"

    booking = models.ForeignKey(
        "bookings.Booking",
        on_delete=models.CASCADE,
        related_name="tickets",
        blank=True,
        null=True,
    )
    payment = models.ForeignKey(
        "payments.Payment",
        on_delete=models.CASCADE,
        related_name="tickets",
        blank=True,
        null=True,
    )
    customer = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="tickets",
        blank=True,
        null=True,
    )
    event = models.ForeignKey(
        "events.Event",
        on_delete=models.CASCADE,
        related_name="tickets",
        blank=True,
        null=True,
    )
    ticket_number = models.CharField(max_length=50, unique=True, blank=True)
    ticket_token = models.CharField(max_length=100, unique=True, blank=True)
    qr_code = models.ImageField(upload_to="ticket_qrcodes/", blank=True, null=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.VALID)
    issued_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "tickets"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["ticket_number"]),
            models.Index(fields=["ticket_token"]),
            models.Index(fields=["booking"]),
            models.Index(fields=["customer"]),
            models.Index(fields=["event"]),
            models.Index(fields=["status"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["booking", "ticket_number"],
                name="unique_booking_ticket_number",
            ),
        ]

    def __str__(self):
        return self.ticket_number

    def save(self, *args, **kwargs):
        if not self.ticket_number:
            self.ticket_number = self.generate_ticket_number()
        if not self.ticket_token:
            self.ticket_token = self.generate_ticket_token()
        if not self.issued_at and self.status == self.Status.VALID:
            from django.utils import timezone
            self.issued_at = timezone.now()
        super().save(*args, **kwargs)

    def generate_ticket_number(self):
        """Generate a unique ticket number like TKT-XXXXXXXX"""
        while True:
            ticket_number = "TKT-" + get_random_string(8).upper()
            if not Ticket.objects.filter(ticket_number=ticket_number).exists():
                return ticket_number

    def generate_ticket_token(self):
        """Generate a unique unpredictable token for QR code"""
        while True:
            token = get_random_string(32).upper()
            if not Ticket.objects.filter(ticket_token=token).exists():
                return token

    def get_qr_code_url(self):
        """Return the verification token embedded in QR code."""
        return self.ticket_token

    @property
    def is_valid(self):
        return self.status == self.Status.VALID

    def generate_and_save_qr_code(self):
        """Generate QR code image and save to the qr_code field."""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(self.get_qr_code_url())
        qr.make(fit=True)

        qr_img = qr.make_image(fill_color="black", back_color="white")
        qr_img = qr_img.convert("RGB")

        buffer = io.BytesIO()
        qr_img.save(buffer, format="PNG")
        buffer.seek(0)

        self.qr_code.save(f"qr_{self.ticket_token}.png", ContentFile(buffer.read()), save=False)
        self.save(update_fields=["qr_code"])
