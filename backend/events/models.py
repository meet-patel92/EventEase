from django.db import models
from django.utils.text import slugify
from django.core.validators import MinValueValidator
from .title_utils import display_event_title


class EventCategory(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "event_categories"
        verbose_name = "Event Category"
        verbose_name_plural = "Event Categories"
        indexes = [
            models.Index(fields=["name"]),
        ]

    def __str__(self):
        return self.name


class Event(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    description = models.TextField()
    category = models.ForeignKey(
        EventCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="events",
    )
    organizer = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="organized_events",
    )
    venue = models.CharField(max_length=200)
    address = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100)
    event_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    registration_deadline = models.DateTimeField(blank=True, null=True)
    ticket_price = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)]
    )
    total_tickets = models.PositiveIntegerField(default=0)
    available_tickets = models.PositiveIntegerField(default=0)
    poster = models.ImageField(upload_to="event_posters/", blank=True, null=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    rejection_reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "events"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["organizer"]),
            models.Index(fields=["category"]),
            models.Index(fields=["event_date"]),
            models.Index(fields=["status"]),
            models.Index(fields=["slug"]),
            models.Index(fields=["city"]),
        ]

    def __str__(self):
        return self.display_title

    @property
    def display_title(self):
        return display_event_title(self.title)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)
