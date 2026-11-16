from rest_framework.permissions import BasePermission


class RoleBasedPermission(BasePermission):
    """
    Custom permission to check user roles.
    Usage:
        permission_classes = [RoleBasedPermission]
        role_based_permission = {'ADMIN': [...], 'ORGANIZER': [...], 'CUSTOMER': [...]}
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        role = getattr(request.user, "role", None)
        allowed_roles = getattr(view, "role_based_permission", {})

        if not allowed_roles:
            return True

        return role in allowed_roles


class IsAdmin(RoleBasedPermission):
    def has_permission(self, request, view):
        return (
            super().has_permission(request, view)
            and request.user.role == "ADMIN"
        )


class IsOrganizer(RoleBasedPermission):
    def has_permission(self, request, view):
        return (
            super().has_permission(request, view)
            and request.user.role == "ORGANIZER"
        )


class IsCustomer(RoleBasedPermission):
    def has_permission(self, request, view):
        return (
            super().has_permission(request, view)
            and request.user.role == "CUSTOMER"
        )


class IsAdminOrOrganizer(RoleBasedPermission):
    def has_permission(self, request, view):
        return (
            super().has_permission(request, view)
            and request.user.role in ("ADMIN", "ORGANIZER")
        )


class IsOwnerOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.role == "ADMIN":
            return True
        return obj == request.user or getattr(obj, "user", None) == request.user
