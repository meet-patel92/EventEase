from django.contrib import admin
from .models import Ticket


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = (
        "ticket_number",
        "booking",
        "customer",
        "event",
        "status",
        "issued_at",
    )
    list_filter = ("status", "event", "issued_at")
    search_fields = ("ticket_number", "ticket_token", "customer__email", "booking__booking_reference")
    ordering = ("-issued_at",)
    readonly_fields = ("ticket_number", "ticket_token", "issued_at", "created_at", "updated_at")
    raw_id_fields = ("customer", "event", "booking", "payment")
