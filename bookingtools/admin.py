from django.contrib import admin
from .models import Booking, Building, Review, Room, RoomCategory, Vehicle, VehicleCategory

admin.site.register(Booking)
admin.site.register(Building)
admin.site.register(Review)
admin.site.register(Room)
admin.site.register(RoomCategory)
admin.site.register(VehicleCategory)
admin.site.register(Vehicle)
# Register your models here.
