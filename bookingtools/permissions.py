from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsOwnerOrReadOnly(BasePermission):
    """
    Разрешает чтение всем, а изменение/отмену/удаление —
    только владельцу объекта (брони или отзыва).
    """

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return obj.user_id == request.user.id


class IsOwner(BasePermission):
    """Строгая версия: даже читать может только владелец (например, "Мои бронирования")."""

    def has_object_permission(self, request, view, obj):
        return obj.user_id == request.user.id


class IsAdminOrReadOnly(BasePermission):
    """
    Смотреть (GET) может кто угодно.
    Создавать / менять / удалять (POST, PUT, PATCH, DELETE) — только суперадмин (is_superuser).
    Используется для зданий, комнат, категорий транспорта и транспорта —
    обычный пользователь никогда не должен мочь создать/удалить комнату или машину.
    """

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated and request.user.is_superuser)