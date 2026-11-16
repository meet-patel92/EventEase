import io
import qrcode
from io import BytesIO
from PIL import Image as PILImage
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from datetime import datetime
from django.http import FileResponse
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from drf_spectacular.utils import extend_schema, extend_schema_view
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Image as RLImage,
    Table,
    TableStyle,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER

from .models import Ticket
from .serializers import (
    TicketSerializer,
    TicketListSerializer,
    TicketDownloadSerializer,
    TicketVerifySerializer,
)
from .permissions import IsCustomer, IsTicketOwner, CanViewTicket


# Brand colors
EVENTEASE_PRIMARY = HexColor("#1a3a5c")
EVENTEASE_SECONDARY = HexColor("#2e5a84")
EVENTEASE_ACCENT = HexColor("#e8f4fd")


def display_booking_reference(value):
    return value[5:] if value and value.upper().startswith("DEMO-") else value


@extend_schema_view(
    list=extend_schema(
        summary="List tickets",
        description="Get tickets. Customers see their own, organizers see their events' tickets, admins see all.",
        tags=["Tickets"],
    ),
    retrieve=extend_schema(
        summary="Get ticket",
        description="Get a single ticket by ID.",
        tags=["Tickets"],
    ),
    download=extend_schema(
        summary="Download ticket PDF",
        description="Download a single ticket as PDF.",
        tags=["Tickets"],
    ),
    download_all=extend_schema(
        summary="Download all tickets for a booking",
        description="Download all tickets for a booking as a single PDF.",
        tags=["Tickets"],
    ),
    my_tickets=extend_schema(
        summary="My tickets",
        description="Get tickets for the current customer.",
        tags=["Tickets"],
    ),
    verify=extend_schema(
        summary="Verify and check in a ticket",
        description="Validate a QR token for an owned event and mark the ticket USED.",
        tags=["Tickets"],
    ),
)
class TicketViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for tickets with QR code and PDF generation."""

    queryset = Ticket.objects.all()
    serializer_class = TicketSerializer
    http_method_names = ["get", "post"]

    def get_serializer_class(self):
        if self.action in ["list", "my_tickets"]:
            return TicketListSerializer
        if self.action in ["download", "download_all"]:
            return TicketDownloadSerializer
        if self.action == "verify":
            return TicketVerifySerializer
        return TicketSerializer

    def get_queryset(self):
        """Filter tickets based on user role."""
        user = self.request.user
        queryset = Ticket.objects.select_related(
            "booking", "payment", "customer", "event", "event__organizer"
        )

        if not user or not user.is_authenticated:
            return queryset.none()

        if user.role == "ADMIN":
            return queryset

        if user.role == "ORGANIZER":
            return queryset.filter(event__organizer=user)

        if user.role == "CUSTOMER":
            return queryset.filter(customer=user)

        return queryset.none()

    def get_permissions(self):
        """Role-based permissions per action."""
        if self.action == "verify":
            return [IsAuthenticated()]
        if self.action in ["list", "retrieve", "download", "download_all", "my_tickets"]:
            return [IsAuthenticated(), CanViewTicket()]
        return [IsAuthenticated()]

    @extend_schema(
        summary="My tickets",
        description="Get tickets for the current customer.",
        tags=["Tickets"],
    )
    @action(detail=False, methods=["get"], url_path="my-tickets")
    def my_tickets(self, request):
        """Get tickets for the current customer."""
        if request.user.role != "CUSTOMER":
            return Response(
                {"error": "Only customers can access this endpoint."},
                status=status.HTTP_403_FORBIDDEN,
            )
        # Use the role-scoped queryset so owner and role filtering stay aligned
        # with the list/detail endpoints while retaining related data efficiently.
        tickets = self.get_queryset().filter(customer=request.user)
        page = self.paginate_queryset(tickets)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(tickets, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["post"], url_path="verify")
    def verify(self, request):
        """Validate and atomically check in a ticket owned by the event staff."""
        if request.user.role not in ["ADMIN", "ORGANIZER"]:
            return Response(
                {"error": "Only admins and organizers can verify tickets."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = TicketVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ticket_token = serializer.validated_data["ticket_token"]
        event_id = serializer.validated_data["event_id"]

        try:
            with transaction.atomic():
                ticket = (
                    Ticket.objects.select_for_update()
                    .select_related("event", "event__organizer", "booking")
                    .get(ticket_token=ticket_token)
                )
                if not ticket.event:
                    return Response({"error": "Ticket is not linked to an event."}, status=status.HTTP_400_BAD_REQUEST)
                if request.user.role == "ORGANIZER" and ticket.event.organizer_id != request.user.id:
                    return Response({"error": "Ticket not found."}, status=status.HTTP_404_NOT_FOUND)
                if ticket.event_id != event_id:
                    return Response({"error": "Ticket belongs to a different event."}, status=status.HTTP_400_BAD_REQUEST)
                if ticket.event.status != "APPROVED":
                    return Response({"error": "Tickets can only be scanned for approved events."}, status=status.HTTP_400_BAD_REQUEST)
                if ticket.status != Ticket.Status.VALID:
                    return Response(
                        {"error": f"Ticket is {ticket.status.lower()} and cannot be checked in."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                if (
                    not ticket.booking
                    or ticket.booking.status != "CONFIRMED"
                    or not ticket.payment
                    or ticket.payment.status != "SUCCESS"
                    or not ticket.payment.signature_verified
                ):
                    return Response(
                        {"error": "Ticket does not have a verified payment."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                event_end = timezone.make_aware(
                    datetime.combine(ticket.event.event_date, ticket.event.end_time),
                    timezone.get_current_timezone(),
                )
                if timezone.now() > event_end:
                    return Response({"error": "This ticket has expired."}, status=status.HTTP_400_BAD_REQUEST)

                ticket.status = Ticket.Status.USED
                ticket.save(update_fields=["status", "updated_at"])
                return Response(
                    {
                        "ticket_number": ticket.ticket_number,
                        "event_title": ticket.event.display_title,
                        "event_date": ticket.event.event_date,
                        "venue": ticket.event.venue,
                        "ticket_status": ticket.status,
                    },
                    status=status.HTTP_200_OK,
                )
        except Ticket.DoesNotExist:
            return Response({"error": "Ticket not found."}, status=status.HTTP_404_NOT_FOUND)

    @extend_schema(
        summary="Download ticket PDF",
        description="Download a single ticket as PDF.",
        tags=["Tickets"],
    )
    @action(detail=True, methods=["get"], url_path="download")
    def download(self, request, pk=None):
        """Download a single ticket as PDF."""
        ticket = self.get_object()
        try:
            pdf_buffer = self.generate_ticket_pdf(ticket)
        except Exception as e:
            return Response(
                {"error": f"Failed to generate PDF: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        response = FileResponse(
            pdf_buffer,
            content_type="application/pdf",
            as_attachment=True,
            filename=f"ticket_{ticket.ticket_number}.pdf",
        )
        return response

    @extend_schema(
        summary="Download all tickets for a booking",
        description="Download all tickets for a booking as a single PDF.",
        tags=["Tickets"],
    )
    @action(detail=False, methods=["get"], url_path="booking/(?P<booking_id>[^/.]+)/download-all")
    def download_all(self, request, booking_id=None):
        """Download all tickets for a booking as a single PDF."""
        from bookings.models import Booking

        try:
            booking = Booking.objects.get(id=booking_id)
        except Booking.DoesNotExist:
            return Response(
                {"error": "Booking not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        is_admin = request.user.role == "ADMIN"
        is_own_event_organizer = (
            request.user.role == "ORGANIZER"
            and booking.event.organizer_id == request.user.id
        )
        if booking.customer_id != request.user.id and not is_admin and not is_own_event_organizer:
            return Response(
                {"error": "You can only download tickets for your own bookings."},
                status=status.HTTP_403_FORBIDDEN,
            )

        tickets = Ticket.objects.filter(booking=booking)
        if not tickets.exists():
            return Response(
                {"error": "No tickets found for this booking."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            pdf_buffer = self.generate_tickets_pdf(tickets, booking)
        except Exception as e:
            return Response(
                {"error": f"Failed to generate PDF: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        response = FileResponse(
            pdf_buffer,
            content_type="application/pdf",
            as_attachment=True,
            filename=f"booking_{booking.booking_reference}_tickets.pdf",
        )
        return response

    # ------------------------------------------------------------------
    # PDF Generation
    # ------------------------------------------------------------------

    def generate_ticket_pdf(self, ticket):
        """Generate a PDF for a single ticket."""
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=0.75 * inch,
            leftMargin=0.75 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch,
            title=f"Ticket {ticket.ticket_number}",
            author="EventEase",
        )

        styles = getSampleStyleSheet()
        elements = []

        elements.append(
            Paragraph(
                "EventEase",
                ParagraphStyle(
                    "HeaderTitle",
                    parent=styles["Title"],
                    fontSize=24,
                    textColor=EVENTEASE_PRIMARY,
                    alignment=TA_CENTER,
                    spaceAfter=5,
                ),
            )
        )
        elements.append(
            Paragraph(
                "Event Ticket",
                ParagraphStyle(
                    "TicketTitle",
                    parent=styles["Heading2"],
                    fontSize=18,
                    textColor=EVENTEASE_SECONDARY,
                    alignment=TA_CENTER,
                    spaceAfter=15,
                ),
            )
        )

        ticket_data = [
            ["Ticket Number (reference):", ticket.ticket_number],
            ["Booking Reference:", display_booking_reference(ticket.booking.booking_reference)],
            ["Check-in Code:", ticket.ticket_token],
            ["Event:", ticket.event.display_title],
            ["Date:", str(ticket.event.event_date)],
            ["Time:", f"{ticket.event.start_time} - {ticket.event.end_time}"],
            ["Venue:", ticket.event.venue],
            ["City:", ticket.event.city],
            ["Customer:", ticket.customer.email],
            ["Status:", ticket.status],
            ["Price:", f"INR {ticket.booking.unit_price}"],
        ]

        ticket_table = Table(ticket_data, colWidths=[2.2 * inch, 4.3 * inch])
        ticket_table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#cccccc")),
                    ("BACKGROUND", (0, 0), (0, -1), EVENTEASE_ACCENT),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        elements.append(ticket_table)
        elements.append(Spacer(1, 20))

        if ticket.qr_code:
            qr_image = RLImage(ticket.qr_code.path, width=2 * inch, height=2 * inch)
            qr_image.hAlign = "CENTER"
            elements.append(qr_image)
            elements.append(Spacer(1, 10))

        elements.append(
            Paragraph(
                "Scan QR code to verify ticket",
                ParagraphStyle(
                    "QRNote",
                    parent=styles["Normal"],
                    fontSize=9,
                    textColor=HexColor("#666666"),
                    alignment=TA_CENTER,
                ),
            )
        )
        elements.append(Spacer(1, 20))

        elements.append(
            Paragraph(
                "This ticket is valid for one entry only. Please present at the venue entrance.",
                ParagraphStyle(
                    "Footer",
                    parent=styles["Normal"],
                    fontSize=8,
                    textColor=HexColor("#999999"),
                    alignment=TA_CENTER,
                ),
            )
        )

        doc.build(elements)
        buffer_value = buffer.getvalue()
        buffer.close()
        return BytesIO(buffer_value)

    def generate_tickets_pdf(self, tickets, booking):
        """Generate a PDF with multiple tickets for a booking."""
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=0.75 * inch,
            leftMargin=0.75 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch,
            title=f"Tickets - {display_booking_reference(booking.booking_reference)}",
            author="EventEase",
        )

        styles = getSampleStyleSheet()
        elements = []

        elements.append(
            Paragraph(
                "EventEase",
                ParagraphStyle(
                    "HeaderTitle",
                    parent=styles["Title"],
                    fontSize=24,
                    textColor=EVENTEASE_PRIMARY,
                    alignment=TA_CENTER,
                    spaceAfter=5,
                ),
            )
        )
        elements.append(
            Paragraph(
                "Event Tickets",
                ParagraphStyle(
                    "HeaderSubtitle",
                    parent=styles["Heading2"],
                    fontSize=18,
                    textColor=EVENTEASE_SECONDARY,
                    alignment=TA_CENTER,
                    spaceAfter=10,
                ),
            )
        )

        elements.append(
            Paragraph(
                f"Booking Reference: {display_booking_reference(booking.booking_reference)}",
                ParagraphStyle(
                    "BookingRef",
                    parent=styles["Normal"],
                    fontSize=12,
                    textColor=EVENTEASE_PRIMARY,
                    alignment=TA_CENTER,
                    spaceAfter=5,
                ),
            )
        )
        elements.append(
            Paragraph(
                f"Event: {tickets.first().event.display_title} | {tickets.first().event.event_date} | {tickets.first().event.venue}",
                ParagraphStyle(
                    "EventInfo",
                    parent=styles["Normal"],
                    fontSize=11,
                    textColor=EVENTEASE_SECONDARY,
                    alignment=TA_CENTER,
                    spaceAfter=15,
                ),
            )
        )

        for ticket in tickets:
            ticket_elements = []

            ticket_elements.append(
                Paragraph(
                    f"Ticket #{ticket.ticket_number}",
                    ParagraphStyle(
                        "TicketHeader",
                        parent=styles["Heading3"],
                        fontSize=14,
                        textColor=EVENTEASE_PRIMARY,
                        spaceAfter=5,
                    ),
                )
            )

            ticket_info = [
                ["Customer:", ticket.customer.email],
                ["Check-in Code:", ticket.ticket_token],
                ["Status:", ticket.status],
                ["Price:", f"INR {ticket.booking.unit_price}"],
            ]
            info_table = Table(ticket_info, colWidths=[1.5 * inch, 3.5 * inch])
            info_table.setStyle(
                TableStyle(
                    [
                        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 9),
                        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#cccccc")),
                        ("BACKGROUND", (0, 0), (0, -1), EVENTEASE_ACCENT),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ]
                )
            )
            ticket_elements.append(info_table)
            ticket_elements.append(Spacer(1, 8))

            if ticket.qr_code:
                qr_img = RLImage(ticket.qr_code.path, width=1.5 * inch, height=1.5 * inch)
                qr_img.hAlign = "CENTER"
                ticket_elements.append(qr_img)
                ticket_elements.append(Spacer(1, 5))

            # Wrap ticket in a table for visual separation
            ticket_wrapper = Table([[ticket_elements]], colWidths=[6.5 * inch])
            ticket_wrapper.setStyle(
                TableStyle(
                    [
                        ("BOX", (0, 0), (-1, -1), 0.5, HexColor("#cccccc")),
                        ("BACKGROUND", (0, 0), (-1, -1), HexColor("#fafafa")),
                        ("TOPPADDING", (0, 0), (-1, -1), 8),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                        ("LEFTPADDING", (0, 0), (-1, -1), 8),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ]
                )
            )
            elements.append(ticket_wrapper)
            elements.append(Spacer(1, 15))

            if ticket != tickets.last():
                elements.append(
                    Paragraph(
                        "-" * 50,
                        ParagraphStyle(
                            "Divider",
                            parent=styles["Normal"],
                            fontSize=8,
                            textColor=HexColor("#cccccc"),
                            alignment=TA_CENTER,
                        ),
                    )
                )
                elements.append(Spacer(1, 10))

        doc.build(elements)
        buffer_value = buffer.getvalue()
        buffer.close()
        return BytesIO(buffer_value)
