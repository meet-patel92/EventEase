from rest_framework import permissions


class IsCustomer(permissions.BasePermission):
    """Only users with CUSTOMER role."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == "CUSTOMER"
        )


class IsPaymentOwner(permissions.BasePermission):
    """Customer can only access their own payments."""

    def has_object_permission(self, request, view, obj):
        return obj.customer == request.user


class CanViewPayment(permissions.BasePermission):
    """
    - ADMIN: can view all payments
    - ORGANIZER: can view payments for their own events' bookings
    - CUSTOMER: can view only their own payments
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.role == "ADMIN":
            return True
        if user.role == "ORGANIZER":
            return obj.booking.event.organizer == user
        if user.role == "CUSTOMER":
            return obj.customer == user
        return False
