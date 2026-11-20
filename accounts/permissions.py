from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework.permissions import BasePermission


# BasicAuthentication comes first so unauthenticated API requests receive 401.
# SessionAuthentication keeps same-site browser clients compatible.
API_AUTH = (BasicAuthentication, SessionAuthentication)


class IsPemilik(BasePermission):
    """Allow authenticated users whose account role is pemilik lahan."""

    message = "Hanya pemilik lahan yang dapat mengakses endpoint ini."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and getattr(user, "is_owner", False)
        )
