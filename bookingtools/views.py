from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from groq import Groq
from dotenv import load_dotenv
import os

load_dotenv()
groq_api = os.getenv("GROQ_API_KEY")

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

from dotenv import load_dotenv
import os
load_dotenv()
groq_api = os.getenv("GROQ_API_KEY")

class BuildingListView(generics.ListCreateAPIView):
    queryset = Building.objects.all().order_by("name")
    serializer_class = BuildingSerializer
    permission_classes = [IsAdminOrReadOnly]


class BuildingDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Building.objects.all()
    serializer_class = BuildingSerializer
    permission_classes = [IsAdminOrReadOnly]


class RoomListView(generics.ListCreateAPIView):
    serializer_class = RoomSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        qs = Room.objects.filter(is_active=True).select_related("building", "category")
        building_id = self.request.query_params.get("building")
        if building_id:
            qs = qs.filter(building_id=building_id)
        return qs


class RoomDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Room.objects.filter(is_active=True)
    serializer_class = RoomSerializer
    permission_classes = [IsAdminOrReadOnly]




class VehicleCategoryListView(generics.ListCreateAPIView):
    queryset = VehicleCategory.objects.all().order_by("level")
    serializer_class = VehicleCategorySerializer
    permission_classes = [IsAdminOrReadOnly]


class VehicleListView(generics.ListCreateAPIView):
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
    queryset = Vehicle.objects.filter(is_active=True)
    serializer_class = VehicleSerializer
    permission_classes = [IsAdminOrReadOnly]




class CreateBookingView(APIView):
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
        
        booked_object = model_map[object_type].objects.get(id=object_id)
        booked_object.booking_status = "booked"
        booked_object.save(update_fields=["booking_status"])
        
        return Response(
            {
                "message": "Успешно забронировано!",
                "booking": BookingSerializer(booking).data,
            },
            status=status.HTTP_201_CREATED,
        )


class MyBookingsView(generics.ListAPIView):
    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Booking.objects.filter(user=self.request.user).order_by("-start_time")


class CancelBookingView(APIView):
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]

    def post(self, request, pk):
        try:
            booking = Booking.objects.get(pk=pk)
        except Booking.DoesNotExist:
            return Response({"error": "Бронь не найдена"}, status=status.HTTP_404_NOT_FOUND)

        self.check_object_permission(request, booking)

        booking.status = "cancelled"
        booking.save(update_fields=["status"])
        
        booked_object = booking.booked_object
        booked_object.booking_status = "available"
        booked_object.save(update_fields=["booking_status"])
        
        return Response({"message": "Бронь отменена"}, status=status.HTTP_200_OK)

    def check_object_permission(self, request, obj):
        if obj.user_id != request.user.id:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Это не твоя бронь.")



class CreateReviewView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ReviewSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        review = serializer.save()
        return Response(ReviewSerializer(review).data, status=status.HTTP_201_CREATED)


class ReviewListView(APIView):

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



class AIRecommendationView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):
        user_query = request.data.get("query", "").strip()
        
        if not user_query:
            return Response({"error": "Введите вопрос"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            buildings = Building.objects.all()
            rooms = Room.objects.filter(is_active=True).select_related('building', 'category')
            vehicles = Vehicle.objects.filter(is_active=True).select_related('category')
            
            buildings_info = []
            for building in buildings:
                buildings_info.append({
                    'name': building.name,
                    'address': building.address,
                    'city': building.city,
                    'description': building.description,
                    'rooms_count': building.rooms.count()
                })
            
            rooms_info = []
            for room in rooms:
                rooms_info.append({
                    'name': room.name,
                    'building': room.building.name,
                    'floor': room.floor,
                    'capacity': room.capacity,
                    'has_projector': room.has_projector,
                    'booking_status': room.booking_status
                })
            
            vehicles_info = []
            for vehicle in vehicles:
                vehicles_info.append({
                    'name': vehicle.name,
                    'category': vehicle.category.name,
                    'capacity': vehicle.capacity,
                    'price_per_hour': float(vehicle.price_per_hour),
                    'plate_number': vehicle.plate_number,
                    'booking_status': vehicle.booking_status
                })

            system_prompt = f"""
You are EstateBooking AI assistant. 
Help users choose the best rooms, buildings, and vehicles for rent based on their needs.

AVAILABLE BUILDINGS:
{buildings_info}

AVAILABLE ROOMS:
{rooms_info}

AVAILABLE VEHICLES:
{vehicles_info}

Rules:
1. Speak friendly and explain simply in Russian.
2. Always use emojis elegantly.
3. Recommend ONLY from the available rooms, buildings, and vehicles listed above.
4. Consider booking status - only recommend available items.
5. If user asks about capacity, price, or features, provide specific details.
6. Help users choose based on their needs (meetings, events, transportation, etc.)
"""

            client = Groq(api_key=groq_api)
            
            response = client.chat.completions.create(
                model="llama3-8b-8192",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_query}
                ]
            )
            
            ai_response = response.choices[0].message.content
            
            return Response({
                "query": user_query,
                "response": ai_response
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                "error": "⚠️ Извините, ИИ-помощник сейчас недоступен. Попробуйте позже.",
                "details": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)