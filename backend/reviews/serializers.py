from rest_framework import serializers
from .models import Review
from events.models import Event


class ReviewSerializer(serializers.ModelSerializer):
    user_email = serializers.ReadOnlyField(source="user.email")

    class Meta:
        model = Review
        fields = ("id", "user", "user_email", "event", "rating", "comment", "created_at", "updated_at")
        read_only_fields = ("id", "user", "user_email", "created_at", "updated_at")

    def validate_event(self, event):
        if event.status != Event.Status.APPROVED:
            raise serializers.ValidationError("Reviews are only available for approved events.")
        return event

    def validate(self, attrs):
        request = self.context.get("request")
        user = self.instance.user if self.instance else getattr(request, "user", None)
        event = attrs.get("event", self.instance.event if self.instance else None)
        if user and user.is_authenticated and event:
            duplicate_reviews = Review.objects.filter(user=user, event=event)
            if self.instance:
                duplicate_reviews = duplicate_reviews.exclude(pk=self.instance.pk)
            if duplicate_reviews.exists():
                raise serializers.ValidationError(
                    {"event": "You have already reviewed this event."}
                )
        return attrs
