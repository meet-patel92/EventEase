import django_filters
from .models import Booking


class BookingFilter(django_filters.FilterSet):
    """Filter bookings by event, status, customer."""

    event = django_filters.NumberFilter(field_name="event__id")
    status = django_filters.ChoiceFilter(
        choices=Booking.Status.choices
    )
    booking_date_after = django_filters.DateTimeFilter(
        field_name="booking_date", lookup_expr="gte"
    )
    booking_date_before = django_filters.DateTimeFilter(
        field_name="booking_date", lookup_expr="lte"
    )

    class Meta:
        model = Booking
        fields = ["event", "status"]
