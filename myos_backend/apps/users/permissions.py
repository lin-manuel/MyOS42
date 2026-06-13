from apps.common.permissions import IsOwnerObjectPermission


class IsSelfOrAdmin(IsOwnerObjectPermission):
    pass
