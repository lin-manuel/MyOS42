from rest_framework.permissions import BasePermission


class IsOwnerObjectPermission(BasePermission):
    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        owner = getattr(obj, "user", None)
        if owner is None and hasattr(obj, "category"):
            owner = getattr(obj.category, "user", None)
        return owner == user or user.is_superuser
