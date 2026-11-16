from django.db import transaction

from .models import Ticket


def ensure_booking_tickets(booking, payment=None):
    """Create tickets only for a booking whose payment was verified."""
    if (
        payment is None
        or payment.status != "SUCCESS"
        or not payment.signature_verified
        or payment.booking_id != booking.pk
        or payment.customer_id != booking.customer_id
    ):
        raise ValueError("Tickets require a verified payment for this booking.")

    tickets = []
    with transaction.atomic():
        # Serialize ticket issuance for the booking so repeated/concurrent calls
        # cannot issue more than the booking quantity.
        from bookings.models import Booking

        locked_booking = Booking.objects.select_for_update().get(pk=booking.pk)
        if locked_booking.status != "CONFIRMED":
            raise ValueError("Tickets can only be issued for confirmed bookings.")
        existing_count = Ticket.objects.filter(booking=locked_booking).count()
        for _ in range(max(locked_booking.quantity - existing_count, 0)):
            ticket = Ticket.objects.create(
                booking=locked_booking,
                payment=payment,
                customer=locked_booking.customer,
                event=locked_booking.event,
                status=Ticket.Status.VALID,
            )
            ticket.generate_and_save_qr_code()
            tickets.append(ticket)
    return tickets
