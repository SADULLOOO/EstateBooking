from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers

from .models import (
    Building,
    RoomCategory,
    Room,
    VehicleCategory,
    Vehicle,
    Booking,
    Review,
)

User = get_user_model()


class BuildingOwnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "phone_number"]




class RoomCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomCategory
        fields = ["id", "name"]


class RoomSerializer(serializers.ModelSerializer):
    category = RoomCategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=RoomCategory.objects.all(), source="category", write_only=True, required=False
    )

    class Meta:
        model = Room
        fields = [
            "id", "building", "name", "category", "category_id",
            "floor", "capacity", "has_projector", "price_per_night",
            "model_3d_url", "photo", "is_active", "booking_status",
        ]


class BuildingSerializer(serializers.ModelSerializer):
    rooms = RoomSerializer(many=True, read_only=True)
    owner = BuildingOwnerSerializer(read_only=True)
    average_rating = serializers.FloatField(read_only=True, allow_null=True)
    reviews_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Building
        fields = [
            "id", "name", "address", "city", "description", "owner",
            "cover_image", "created_at", "rooms",
            "average_rating", "reviews_count",
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['rooms_count'] = instance.rooms.filter(is_active=True).count()
        return data

class VehicleCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleCategory
        fields = ["id", "name", "level", "description"]


class VehicleSerializer(serializers.ModelSerializer):
    category = VehicleCategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=VehicleCategory.objects.all(), source="category", write_only=True
    )
    average_rating = serializers.FloatField(read_only=True, allow_null=True)
    reviews_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Vehicle
        fields = [
            "id", "category", "category_id", "name", "brand", "plate_number", "capacity",
            "transmission", "location",
            "price_per_hour", "price_per_day", "photo", "is_active", "booking_status",
            "average_rating", "reviews_count",
        ]




class BookingSerializer(serializers.ModelSerializer):

    object_type = serializers.ChoiceField(choices=["room", "vehicle"], write_only=True)
    object_id = serializers.IntegerField(write_only=True)

    booked_object_repr = serializers.SerializerMethodField(read_only=True)
    booked_object_type = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Booking
        fields = [
            "id", "object_type", "object_id",
            "booked_object_repr", "booked_object_type",
            "start_time", "end_time", "status", "created_at",
        ]
        read_only_fields = ["id", "status", "created_at"]

    def get_booked_object_repr(self, obj):
        return str(obj.booked_object)

    def get_booked_object_type(self, obj):
        model_class = obj.content_type.model_class()
        if model_class == Room:
            return "room"
        if model_class == Vehicle:
            return "vehicle"
        return None

    def validate(self, attrs):
        object_type = attrs.get("object_type")
        object_id = attrs.get("object_id")

        model_map = {"room": Room, "vehicle": Vehicle}
        model_class = model_map[object_type]

        if not model_class.objects.filter(id=object_id, is_active=True).exists():
            raise serializers.ValidationError("Объект не найден или недоступен.")

        if attrs["start_time"] >= attrs["end_time"]:
            raise serializers.ValidationError("Время начала должно быть раньше времени окончания.")

        attrs["_content_type"] = ContentType.objects.get_for_model(model_class)
        return attrs

    def create(self, validated_data):
        validated_data.pop("object_type")
        object_id = validated_data.pop("object_id")
        content_type = validated_data.pop("_content_type")

        return Booking.objects.create(
            content_type=content_type,
            object_id=object_id,
            **validated_data,
        )


class ReviewSerializer(serializers.ModelSerializer):
    object_type = serializers.ChoiceField(choices=["building", "room", "vehicle"], write_only=True)
    object_id = serializers.IntegerField(write_only=True)
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Review
        fields = ["id", "object_type", "object_id", "user", "rating", "comment", "created_at"]
        read_only_fields = ["id", "user", "created_at"]

    def validate(self, attrs):
        model_map = {"building": Building, "room": Room, "vehicle": Vehicle}
        model_class = model_map[attrs["object_type"]]

        if not model_class.objects.filter(id=attrs["object_id"]).exists():
            raise serializers.ValidationError("Объект для отзыва не найден.")

        if not (1 <= attrs["rating"] <= 5):
            raise serializers.ValidationError("Рейтинг должен быть от 1 до 5.")

        attrs["_content_type"] = ContentType.objects.get_for_model(model_class)
        return attrs

    def create(self, validated_data):
        validated_data.pop("object_type")
        object_id = validated_data.pop("object_id")
        content_type = validated_data.pop("_content_type")

        return Review.objects.create(
            user=self.context["request"].user,
            content_type=content_type,
            object_id=object_id,
            **validated_data,
        )