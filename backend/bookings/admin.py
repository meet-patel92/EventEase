from django.contrib import admin
from .models import Booking


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "booking_reference",
        "customer",
        "event",
        "quantity",
        "unit_price",
        "total_amount",
        "status",
        "booking_date",
    )
    list_filter = ("status", "event", "booking_date")
    search_fields = (
        "booking_reference",
        "customer__email",
        "event__title",
    )
    ordering = ("-booking_date",)
    readonly_fields = ("booking_reference", "booking_date", "updated_at")
    raw_id_fields = ("customer", "event")
