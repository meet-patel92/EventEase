from rest_framework import permissions


class IsOrganizer(permissions.BasePermission):
    """Only users with ORGANIZER role."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == "ORGANIZER"
        )


class IsAdmin(permissions.BasePermission):
    """Only users with ADMIN role."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == "ADMIN"
        )


class IsCustomer(permissions.BasePermission):
    """Only users with CUSTOMER role."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == "CUSTOMER"
        )


class IsEventOwner(permissions.BasePermission):
    """Organizer can only access their own events."""

    def has_object_permission(self, request, view, obj):
        return obj.organizer == request.user


class CanDeleteEvent(permissions.BasePermission):
    """Organizer can delete only their own PENDING or REJECTED events."""

    def has_object_permission(self, request, view, obj):
        if obj.organizer != request.user:
            return False
        return obj.status in ("PENDING", "REJECTED")


class CanApproveOrReject(permissions.BasePermission):
    """Only ADMIN can approve or reject events."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == "ADMIN"
        )


class CanViewEvent(permissions.BasePermission):
    """
    - ADMIN: can view all events
    - ORGANIZER: can view their own events + approved events
    - CUSTOMER: can view only APPROVED events
    - Unauthenticated: can view only APPROVED events (if public access allowed)
    """

    def has_permission(self, request, view):
        # Allow unauthenticated access to list/retrieve (handled in get_queryset)
        return True

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return obj.status == "APPROVED"
        if user.role == "ADMIN":
            return True
        if user.role == "ORGANIZER":
            return obj.organizer == user or obj.status == "APPROVED"
        if user.role == "CUSTOMER":
            return obj.status == "APPROVED"
        return False
