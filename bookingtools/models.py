from django.conf import settings
from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType


class Building(models.Model):
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=500)
    city = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)

    model_3d_url = models.URLField(blank=True, null=True)
    cover_image = models.ImageField(upload_to="buildings/", blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    reviews = GenericRelation("Review")  
    def __str__(self):
        return self.name


class RoomCategory(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Room(models.Model):
    building = models.ForeignKey(Building, on_delete=models.CASCADE, related_name="rooms")
    category = models.ForeignKey(RoomCategory, on_delete=models.SET_NULL, null=True, blank=True)

    name = models.CharField(max_length=255)              
    floor = models.PositiveIntegerField(default=1)
    capacity = models.PositiveIntegerField()
    has_projector = models.BooleanField(default=False)

    model_3d_url = models.URLField(blank=True, null=True)
    photo = models.ImageField(upload_to="rooms/", blank=True, null=True)
    is_active = models.BooleanField(default=True)

    reviews = GenericRelation("Review")

    def __str__(self):
        return f"{self.name} ({self.building.name})"




class VehicleCategory(models.Model):
    name = models.CharField(max_length=100)   
    level = models.PositiveSmallIntegerField(default=1)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name} (уровень {self.level})"


class Vehicle(models.Model):
    category = models.ForeignKey(VehicleCategory, on_delete=models.CASCADE, related_name="vehicles")

    name = models.CharField(max_length=255)             
    plate_number = models.CharField(max_length=20, unique=True)
    capacity = models.PositiveIntegerField()

    price_per_hour = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    price_per_day = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    model_3d_url = models.URLField(blank=True, null=True)
    photo = models.ImageField(upload_to="vehicles/", blank=True, null=True)
    is_active = models.BooleanField(default=True)

    reviews = GenericRelation("Review")

    def __str__(self):
        return self.name




class Booking(models.Model):

    STATUS_CHOICES = [
        ("active", "Активна"),
        ("cancelled", "Отменена"),
        ("completed", "Завершена"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bookings")

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    booked_object = GenericForeignKey("content_type", "object_id")  

    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-start_time"]
        indexes = [
            models.Index(fields=["content_type", "object_id", "start_time", "end_time"]),
        ]

    def __str__(self):
        return f"{self.user} -> {self.booked_object} ({self.start_time} - {self.end_time})"




class Review(models.Model):

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews")

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    rating = models.PositiveSmallIntegerField() 
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} - {self.rating} stars"