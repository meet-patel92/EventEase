from django.contrib import admin
from .models import EventCategory, Event


@admin.register(EventCategory)
class EventCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at")
    list_filter = ("created_at",)
    search_fields = ("name", "description")
    ordering = ("name",)


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = (
        "display_title",
        "organizer",
        "category",
        "city",
        "event_date",
        "status",
        "ticket_price",
        "total_tickets",
        "available_tickets",
        "created_at",
    )
    list_filter = ("status", "category", "city", "event_date", "organizer")
    search_fields = ("title", "description", "venue", "city", "organizer__email")
    ordering = ("-created_at",)
    readonly_fields = ("slug", "created_at", "updated_at")
    raw_id_fields = ("organizer", "category")

    @admin.display(description="title", ordering="title")
    def display_title(self, event):
        return event.display_title
