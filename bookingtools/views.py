from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Building, Room, VehicleCategory, Vehicle, Booking, Review
from .permissions import IsOwnerOrReadOnly, IsAdminOrReadOnly
from .serializers import (
    BuildingSerializer,
    RoomSerializer,
    VehicleCategorySerializer,
    VehicleSerializer,
    BookingSerializer,
    ReviewSerializer,
)


# ---------------------------------------------------------------------------
# ЗДАНИЯ / КОМНАТЫ — доступны без авторизации (просмотр)
# ---------------------------------------------------------------------------

class BuildingListView(generics.ListCreateAPIView):
    """
    Список всех зданий — смотреть может любой.
    Создавать новое здание — только админ (is_staff).
    """
    queryset = Building.objects.all().order_by("name")
    serializer_class = BuildingSerializer
    permission_classes = [IsAdminOrReadOnly]


class BuildingDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Детали здания — смотреть может любой.
    Менять / удалять — только админ.
    """
    queryset = Building.objects.all()
    serializer_class = BuildingSerializer
    permission_classes = [IsAdminOrReadOnly]


class RoomListView(generics.ListCreateAPIView):
    """
    get_rooms — список всех комнат, смотреть может любой.
    Создавать новую комнату — только админ.
    Фильтр: /api/rooms/?building=1
    """
    serializer_class = RoomSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        qs = Room.objects.filter(is_active=True).select_related("building", "category")
        building_id = self.request.query_params.get("building")
        if building_id:
            qs = qs.filter(building_id=building_id)
        return qs


class RoomDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Смотреть может любой, менять/удалять — только админ."""
    queryset = Room.objects.filter(is_active=True)
    serializer_class = RoomSerializer
    permission_classes = [IsAdminOrReadOnly]


# ---------------------------------------------------------------------------
# ТРАНСПОРТ — тоже доступен без авторизации (просмотр)
# ---------------------------------------------------------------------------

class VehicleCategoryListView(generics.ListCreateAPIView):
    """Смотреть может любой, создавать новую категорию транспорта — только админ."""
    queryset = VehicleCategory.objects.all().order_by("level")
    serializer_class = VehicleCategorySerializer
    permission_classes = [IsAdminOrReadOnly]


class VehicleListView(generics.ListCreateAPIView):
    """
    Список транспорта. Смотреть может любой, создавать — только админ.
    Фильтры:
    /api/vehicles/?category=2  (по id категории)
    /api/vehicles/?level=2     (по уровню комфорта)
    """
    serializer_class = VehicleSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        qs = Vehicle.objects.filter(is_active=True).select_related("category")
        category_id = self.request.query_params.get("category")
        level = self.request.query_params.get("level")
        if category_id:
            qs = qs.filter(category_id=category_id)
        if level:
            qs = qs.filter(category__level=level)
        return qs


class VehicleDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Смотреть может любой, менять/удалять — только админ."""
    queryset = Vehicle.objects.filter(is_active=True)
    serializer_class = VehicleSerializer
    permission_classes = [IsAdminOrReadOnly]


# ---------------------------------------------------------------------------
# БРОНИРОВАНИЕ
# ---------------------------------------------------------------------------

class CreateBookingView(APIView):
    """
    create_booking — создать бронь на комнату ИЛИ на транспорт.
    Body: { "object_type": "room", "object_id": 1, "start_time": "...", "end_time": "..." }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = BookingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        object_type = serializer.validated_data["object_type"]
        object_id = serializer.validated_data["object_id"]
        start_time = serializer.validated_data["start_time"]
        end_time = serializer.validated_data["end_time"]

        model_map = {"room": Room, "vehicle": Vehicle}
        content_type = ContentType.objects.get_for_model(model_map[object_type])

        # Проверка пересечения по времени с уже активными бронями
        overlapping = Booking.objects.filter(
            content_type=content_type,
            object_id=object_id,
            status="active",
        ).filter(
            Q(start_time__lt=end_time) & Q(end_time__gt=start_time)
        )

        if overlapping.exists():
            return Response(
                {"error": "Извини, этот час уже занят"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        booking = serializer.save(user=request.user)
        return Response(
            {
                "message": "Успешно забронировано!",
                "booking": BookingSerializer(booking).data,
            },
            status=status.HTTP_201_CREATED,
        )


class MyBookingsView(generics.ListAPIView):
    """my_bookings — список бронирований текущего пользователя."""
    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Booking.objects.filter(user=self.request.user).order_by("-start_time")


class CancelBookingView(APIView):
    """Отмена своей брони."""
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]

    def post(self, request, pk):
        try:
            booking = Booking.objects.get(pk=pk)
        except Booking.DoesNotExist:
            return Response({"error": "Бронь не найдена"}, status=status.HTTP_404_NOT_FOUND)

        self.check_object_permission(request, booking)

        booking.status = "cancelled"
        booking.save(update_fields=["status"])
        return Response({"message": "Бронь отменена"}, status=status.HTTP_200_OK)

    def check_object_permission(self, request, obj):
        if obj.user_id != request.user.id:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Это не твоя бронь.")


# ---------------------------------------------------------------------------
# ОТЗЫВЫ
# ---------------------------------------------------------------------------

class CreateReviewView(APIView):
    """Оставить отзыв на здание / комнату / транспорт."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ReviewSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        review = serializer.save()
        return Response(ReviewSerializer(review).data, status=status.HTTP_201_CREATED)


class ReviewListView(APIView):
    """
    Список отзывов на конкретный объект.
    /api/reviews/?object_type=room&object_id=3
    """
    permission_classes = [AllowAny]

    def get(self, request):
        object_type = request.query_params.get("object_type")
        object_id = request.query_params.get("object_id")

        model_map = {"building": Building, "room": Room, "vehicle": Vehicle}
        model_class = model_map.get(object_type)
        if not model_class or not object_id:
            return Response({"error": "Укажи object_type и object_id"}, status=400)

        content_type = ContentType.objects.get_for_model(model_class)
        reviews = Review.objects.filter(content_type=content_type, object_id=object_id).order_by("-created_at")
        return Response(ReviewSerializer(reviews, many=True).data)