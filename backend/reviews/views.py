from rest_framework import permissions, viewsets
from django.db import IntegrityError, transaction
from rest_framework import serializers
from .models import Review
from .serializers import ReviewSerializer


class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        event_id = self.request.query_params.get("event")
        if self.action == "list" and event_id:
            if not event_id.isdecimal():
                return queryset.none()
            return queryset.filter(event_id=event_id)
        return queryset

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [permissions.AllowAny()]
        if self.action == "create":
            return [permissions.IsAuthenticated(), IsCustomer()]
        return [permissions.IsAuthenticated(), IsReviewOwner()]

    def perform_create(self, serializer):
        self._save_review(serializer)

    def perform_update(self, serializer):
        self._save_review(serializer)

    def _save_review(self, serializer):
        user = self.request.user
        event = serializer.validated_data.get(
            "event", serializer.instance.event if serializer.instance else None
        )
        try:
            # Keep the model's unique constraint as the final race-safe guard.
            with transaction.atomic():
                serializer.save(user=user)
        except IntegrityError as error:
            duplicate = Review.objects.filter(user=user, event=event)
            if serializer.instance:
                duplicate = duplicate.exclude(pk=serializer.instance.pk)
            if duplicate.exists():
                raise serializers.ValidationError(
                    {"event": "You have already reviewed this event."}
                ) from error
            raise


class IsCustomer(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == "CUSTOMER")


class IsReviewOwner(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        return obj.user_id == request.user.id
