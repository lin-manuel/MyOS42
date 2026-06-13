from rest_framework.permissions import IsAuthenticated


class APIDefaultPermission(IsAuthenticated):
    pass
