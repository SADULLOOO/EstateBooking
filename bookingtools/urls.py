from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from . import views

urlpatterns = [
    # --- JWT ---
    path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    # --- Здания ---
    path("buildings/", views.BuildingListView.as_view(), name="building-list"),
    path("buildings/<int:pk>/", views.BuildingDetailView.as_view(), name="building-detail"),

    # --- Комнаты ---
    path("rooms/", views.RoomListView.as_view(), name="room-list"),              # get_rooms
    path("rooms/<int:pk>/", views.RoomDetailView.as_view(), name="room-detail"),

    # --- Транспорт ---
    path("vehicle-categories/", views.VehicleCategoryListView.as_view(), name="vehicle-category-list"),
    path("vehicles/", views.VehicleListView.as_view(), name="vehicle-list"),
    path("vehicles/<int:pk>/", views.VehicleDetailView.as_view(), name="vehicle-detail"),

    # --- Бронирование ---
    path("bookings/create/", views.CreateBookingView.as_view(), name="create-booking"),   # create_booking
    path("bookings/my/", views.MyBookingsView.as_view(), name="my-bookings"),              # my_bookings
    path("bookings/<int:pk>/cancel/", views.CancelBookingView.as_view(), name="cancel-booking"),

    # --- Отзывы ---
    path("reviews/create/", views.CreateReviewView.as_view(), name="create-review"),
    path("reviews/", views.ReviewListView.as_view(), name="review-list"),
]