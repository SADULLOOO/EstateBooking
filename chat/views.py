from rest_framework import generics, permissions, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ChatRoom, Message, Notification
from .serializers import ChatRoomListSerializer, MessageSerializer, NotificationSerializer


class ChatRoomListCreateView(generics.ListCreateAPIView):
    serializer_class = ChatRoomListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return ChatRoom.objects.all()
        return ChatRoom.objects.filter(participants=user)

    def perform_create(self, serializer):
        room = serializer.save()
        room.participants.add(self.request.user)
        owners = type(self.request.user).objects.filter(
            is_superuser=True
        ) | type(self.request.user).objects.filter(is_staff=True)
        for owner in owners.distinct():
            room.participants.add(owner)


class RoomMessagesView(generics.ListAPIView):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        room_id = self.kwargs["pk"]
        user = self.request.user
        room = ChatRoom.objects.get(pk=room_id)
        if not (user.is_staff or user.is_superuser) and not room.participants.filter(id=user.id).exists():
            return Message.objects.none()
        return Message.objects.filter(room_id=room_id)

    def list(self, request, *args, **kwargs):
        try:
            return super().list(request, *args, **kwargs)
        except ChatRoom.DoesNotExist:
            return Response({"error": "Чат не найден"}, status=status.HTTP_404_NOT_FOUND)


class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)


class NotificationMarkReadView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        return Response({"status": "ok"})
