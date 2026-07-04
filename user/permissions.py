from rest_framework.permissions import BasePermission


class IsStaffOrSuperuser(BasePermission):
    """
    Доступ только для is_staff/is_superuser — используется для админских
    разделов (управление пользователями и т.п.).
    """

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (request.user.is_staff or request.user.is_superuser)
        )
