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
            "floor", "capacity", "has_projector",
            "model_3d_url", "photo", "is_active",
        ]


class BuildingSerializer(serializers.ModelSerializer):
    rooms = RoomSerializer(many=True, read_only=True)

    class Meta:
        model = Building
        fields = [
            "id", "name", "address", "city", "description",
            "model_3d_url", "cover_image", "created_at", "rooms",
        ]

class VehicleCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleCategory
        fields = ["id", "name", "level", "description"]


class VehicleSerializer(serializers.ModelSerializer):
    category = VehicleCategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=VehicleCategory.objects.all(), source="category", write_only=True
    )

    class Meta:
        model = Vehicle
        fields = [
            "id", "category", "category_id", "name", "plate_number", "capacity",
            "price_per_hour", "price_per_day", "model_3d_url", "photo", "is_active",
        ]




class BookingSerializer(serializers.ModelSerializer):


    object_type = serializers.ChoiceField(choices=["room", "vehicle"], write_only=True)
    object_id = serializers.IntegerField(write_only=True)

    booked_object_repr = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Booking
        fields = [
            "id", "object_type", "object_id", "booked_object_repr",
            "start_time", "end_time", "status", "created_at",
        ]
        read_only_fields = ["id", "status", "created_at"]

    def get_booked_object_repr(self, obj):
        return str(obj.booked_object)

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