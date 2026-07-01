from django.urls import path

from . import views

urlpatterns = [
    path("rooms/", views.ChatRoomListCreateView.as_view(), name="chat-rooms"),
    path("rooms/<int:pk>/messages/", views.RoomMessagesView.as_view(), name="chat-messages"),
    path("notifications/", views.NotificationListView.as_view(), name="notification-list"),
    path("notifications/mark-read/", views.NotificationMarkReadView.as_view(), name="notification-mark-read"),
]
