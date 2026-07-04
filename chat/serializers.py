from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import ChatRoom, Message, Notification

User = get_user_model()


class ChatParticipantSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username"]


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source="sender.username", read_only=True)

    class Meta:
        model = Message
        fields = ["id", "sender", "sender_name", "content", "created_at"]


class ChatRoomListSerializer(serializers.ModelSerializer):
    last_message = serializers.SerializerMethodField()
    participant_names = serializers.SerializerMethodField()
    participants = ChatParticipantSerializer(many=True, read_only=True)

    class Meta:
        model = ChatRoom
        fields = ["id", "participants", "participant_names", "last_message", "created_at"]

    def get_last_message(self, obj):
        msg = obj.messages.order_by("-created_at").first()
        if msg:
            return MessageSerializer(msg).data
        return None

    def get_participant_names(self, obj):
        return [p.username for p in obj.participants.all()]


class NotificationSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source="sender.username", read_only=True, allow_null=True)

    class Meta:
        model = Notification
        fields = [
            "id", "recipient", "sender", "sender_name", "notification_type",
            "message_preview", "chat_room_id", "is_read", "created_at",
        ]
