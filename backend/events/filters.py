import django_filters
from .models import Event


class EventFilter(django_filters.FilterSet):
    """Filter events by category, city, and event date."""

    category = django_filters.NumberFilter(field_name="category__id")
    city = django_filters.CharFilter(field_name="city", lookup_expr="iexact")
    event_date = django_filters.DateFilter(field_name="event_date")
    event_date_after = django_filters.DateFilter(
        field_name="event_date", lookup_expr="gte"
    )
    event_date_before = django_filters.DateFilter(
        field_name="event_date", lookup_expr="lte"
    )
    min_price = django_filters.NumberFilter(
        field_name="ticket_price", lookup_expr="gte"
    )
    max_price = django_filters.NumberFilter(
        field_name="ticket_price", lookup_expr="lte"
    )

    class Meta:
        model = Event
        fields = ["category", "city", "event_date"]
