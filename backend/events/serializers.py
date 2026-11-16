from rest_framework import serializers
from django.utils.text import slugify
from .models import EventCategory, Event
from .title_utils import display_event_title


class EventCategorySerializer(serializers.ModelSerializer):
    """Serializer for event categories."""

    class Meta:
        model = EventCategory
        fields = "__all__"
        read_only_fields = ("id", "created_at")

    def validate_name(self, value):
        """Prevent duplicate category names (case-insensitive)."""
        if EventCategory.objects.filter(name__iexact=value).exclude(
            pk=self.instance.pk if self.instance else None
        ).exists():
            raise serializers.ValidationError(
                "A category with this name already exists."
            )
        return value


class EventListSerializer(serializers.ModelSerializer):
    """Serializer for event list view (optimized)."""

    organizer_email = serializers.ReadOnlyField(source="organizer.email")
    organizer = serializers.ReadOnlyField(source="organizer.id")
    category_name = serializers.ReadOnlyField(source="category.name")

    class Meta:
        model = Event
        fields = (
            "id",
            "title",
            "slug",
            "description",
            "category",
            "category_name",
            "organizer",
            "organizer_email",
            "venue",
            "address",
            "city",
            "event_date",
            "start_time",
            "end_time",
            "registration_deadline",
            "ticket_price",
            "total_tickets",
            "available_tickets",
            "poster",
            "status",
            "created_at",
        )

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["title"] = display_event_title(data.get("title"))
        return data


class EventSerializer(serializers.ModelSerializer):
    """Serializer for event detail view."""

    organizer_email = serializers.ReadOnlyField(source="organizer.email")
    category_name = serializers.ReadOnlyField(source="category.name")
    is_organizer = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = "__all__"
        read_only_fields = ("id", "organizer", "slug", "created_at", "updated_at")

    def get_is_organizer(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return obj.organizer == request.user
        return False

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["title"] = display_event_title(data.get("title"))
        return data

    def validate_event_date(self, value):
        """Event date must not be in the past."""
        from django.utils import timezone

        if value < timezone.now().date():
            raise serializers.ValidationError(
                "Event date cannot be in the past."
            )
        return value

    def validate(self, attrs):
        """Cross-field validation."""
        # End time must be later than start time
        start_time = attrs.get("start_time")
        end_time = attrs.get("end_time")
        if start_time and end_time and end_time <= start_time:
            raise serializers.ValidationError(
                {"end_time": "End time must be later than start time."}
            )

        # Registration deadline must not be after event date
        registration_deadline = attrs.get("registration_deadline")
        event_date = attrs.get("event_date")
        if registration_deadline and event_date:
            from datetime import time

            deadline_date = registration_deadline.date()
            if deadline_date > event_date:
                raise serializers.ValidationError(
                    {
                        "registration_deadline": "Registration deadline cannot be after event date."
                    }
                )

        # Available tickets cannot exceed total tickets
        total_tickets = attrs.get("total_tickets")
        available_tickets = attrs.get("available_tickets")
        if total_tickets is not None and available_tickets is not None:
            if available_tickets > total_tickets:
                raise serializers.ValidationError(
                    {
                        "available_tickets": "Available tickets cannot exceed total tickets."
                    }
                )

        # Ticket price cannot be negative
        ticket_price = attrs.get("ticket_price")
        if ticket_price is not None and ticket_price < 0:
            raise serializers.ValidationError(
                {"ticket_price": "Ticket price cannot be negative."}
            )

        return attrs

    def validate_poster(self, value):
        """Validate uploaded image files."""
        if value:
            if value.size > 5 * 1024 * 1024:
                raise serializers.ValidationError(
                    "Image file size cannot exceed 5MB."
                )
            try:
                from PIL import Image
                image = Image.open(value)
                if image.format not in {"JPEG", "PNG", "WEBP", "GIF"}:
                    raise ValueError("unsupported image type")
                image.verify()
                value.seek(0)
            except Exception as exc:
                raise serializers.ValidationError(
                    "Upload a valid JPEG, PNG, WebP or GIF image."
                ) from exc
        return value

    def create(self, validated_data):
        """Set organizer from authenticated user (never from client)."""
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["organizer"] = request.user
        # Auto-generate slug from title
        title = validated_data.get("title", "")
        if not validated_data.get("slug"):
            validated_data["slug"] = slugify(title)
        return super().create(validated_data)


class EventCreateSerializer(serializers.ModelSerializer):
    """Serializer for event creation (organizer set from request)."""

    organizer = serializers.ReadOnlyField(source="organizer.id")
    status = serializers.ReadOnlyField()

    class Meta:
        model = Event
        fields = (
            "id",
            "organizer",
            "status",
            "title",
            "description",
            "category",
            "venue",
            "address",
            "city",
            "event_date",
            "start_time",
            "end_time",
            "registration_deadline",
            "ticket_price",
            "total_tickets",
            "available_tickets",
            "poster",
        )
        read_only_fields = ("id", "organizer", "status")

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["title"] = display_event_title(data.get("title"))
        return data

    def validate_event_date(self, value):
        """Event date must not be in the past."""
        from django.utils import timezone

        if value < timezone.now().date():
            raise serializers.ValidationError(
                "Event date cannot be in the past."
            )
        return value

    def validate(self, attrs):
        """Cross-field validation."""
        # End time must be later than start time
        start_time = attrs.get("start_time")
        end_time = attrs.get("end_time")
        if start_time and end_time and end_time <= start_time:
            raise serializers.ValidationError(
                {"end_time": "End time must be later than start time."}
            )

        # Registration deadline must not be after event date
        registration_deadline = attrs.get("registration_deadline")
        event_date = attrs.get("event_date")
        if registration_deadline and event_date:
            from datetime import time

            deadline_date = registration_deadline.date()
            if deadline_date > event_date:
                raise serializers.ValidationError(
                    {
                        "registration_deadline": "Registration deadline cannot be after event date."
                    }
                )

        # Available tickets cannot exceed total tickets
        total_tickets = attrs.get("total_tickets")
        available_tickets = attrs.get("available_tickets")
        if total_tickets is not None and available_tickets is not None:
            if available_tickets > total_tickets:
                raise serializers.ValidationError(
                    {
                        "available_tickets": "Available tickets cannot exceed total tickets."
                    }
                )

        # Ticket price cannot be negative
        ticket_price = attrs.get("ticket_price")
        if ticket_price is not None and ticket_price < 0:
            raise serializers.ValidationError(
                {"ticket_price": "Ticket price cannot be negative."}
            )

        return attrs

    def validate_poster(self, value):
        """Validate uploaded image files."""
        if value:
            # Check file size (max 5MB)
            if value.size > 5 * 1024 * 1024:
                raise serializers.ValidationError(
                    "Image file size cannot exceed 5MB."
                )
            try:
                from PIL import Image
                image = Image.open(value)
                if image.format not in {"JPEG", "PNG", "WEBP", "GIF"}:
                    raise ValueError("unsupported image type")
                image.verify()
                value.seek(0)
            except Exception as exc:
                raise serializers.ValidationError(
                    "Upload a valid JPEG, PNG, WebP or GIF image."
                ) from exc
        return value

    def create(self, validated_data):
        """Set organizer from authenticated user."""
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["organizer"] = request.user
        title = validated_data.get("title", "")
        if not validated_data.get("slug"):
            validated_data["slug"] = slugify(title)
        return super().create(validated_data)


class EventStatusUpdateSerializer(serializers.Serializer):
    """Serializer for approve/reject actions."""

    status = serializers.ChoiceField(choices=["APPROVED", "REJECTED"])
    rejection_reason = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        status = attrs.get("status")
        rejection_reason = attrs.get("rejection_reason", "")
        if status == "REJECTED" and not rejection_reason:
            raise serializers.ValidationError(
                {"rejection_reason": "Rejection reason is required when rejecting an event."}
            )
        if status == "APPROVED" and rejection_reason:
            attrs.pop("rejection_reason", None)
        return attrs
