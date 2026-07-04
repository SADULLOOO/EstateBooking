import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken

from channels.layers import get_channel_layer

from .models import ChatRoom, Message

User = get_user_model()

PRESENCE_GROUP = "presence"
ONLINE_USERS: set[int] = set()


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
        self.room_group_name = f"chat_{self.room_id}"

        user = await self.get_user()
        if not user:
            await self.close()
            return

        can_access = await self.can_access_room(user)
        if not can_access:
            await self.close()
            return

        self.user = user
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "room_group_name"):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event))

    async def typing_event(self, event):
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def get_user(self):
        token = None
        query_string = self.scope.get("query_string", b"").decode()
        for param in query_string.split("&"):
            if param.startswith("token="):
                token = param.split("=", 1)[1]
                break
        if not token:
            return None
        try:
            access = AccessToken(token)
            return User.objects.get(id=access["user_id"])
        except Exception:
            return None

    @database_sync_to_async
    def can_access_room(self, user):
        try:
            room = ChatRoom.objects.get(pk=self.room_id)
            if user.is_staff or user.is_superuser:
                return True
            return room.participants.filter(id=user.id).exists()
        except ChatRoom.DoesNotExist:
            return False

    @database_sync_to_async
    def save_message(self, content):
        room = ChatRoom.objects.get(pk=self.room_id)
        return Message.objects.create(room=room, sender=self.user, content=content)

    async def receive(self, text_data):
        data = json.loads(text_data)

        if data.get("type") == "typing":
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "typing_event",
                    "sender": self.user.id,
                    "sender_name": self.user.username,
                    "is_typing": bool(data.get("is_typing")),
                },
            )
            return

        content = data.get("content", "").strip()
        if not content:
            return

        message = await self.save_message(content)
        await self.create_notification(message)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "id": message.id,
                "sender": self.user.id,
                "sender_name": self.user.username,
                "content": message.content,
                "created_at": message.created_at.isoformat(),
            },
        )

    async def create_notification(self, message):
        from .models import Notification

        room = message.room
        participants = await database_sync_to_async(
            lambda: list(room.participants.exclude(id=self.user.id))
        )()

        channel_layer = get_channel_layer()
        for participant in participants:
            notif = await database_sync_to_async(Notification.objects.create)(
                recipient=participant,
                sender=self.user,
                message_preview=message.content[:100],
                chat_room_id=room.id,
            )
            await channel_layer.group_send(
                f"notifications_{participant.id}",
                {
                    "type": "send_notification",
                    "data": {
                        "id": notif.id,
                        "sender": self.user.id,
                        "sender_name": self.user.username,
                        "message_preview": message.content[:100],
                        "chat_room_id": room.id,
                        "is_read": False,
                        "created_at": message.created_at.isoformat(),
                    },
                },
            )


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = await self.get_user()
        if not user:
            await self.close()
            return
        self.user = user
        self.group_name = f"notifications_{user.id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.channel_layer.group_add(PRESENCE_GROUP, self.channel_name)
        await self.accept()

        ONLINE_USERS.add(user.id)
        await self.send(text_data=json.dumps({
            "type": "presence_snapshot",
            "online_user_ids": list(ONLINE_USERS),
        }))
        await self.channel_layer.group_send(
            PRESENCE_GROUP,
            {"type": "presence_change", "user_id": user.id, "is_online": True},
        )

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        if hasattr(self, "user"):
            ONLINE_USERS.discard(self.user.id)
            await self.channel_layer.group_discard(PRESENCE_GROUP, self.channel_name)
            await self.channel_layer.group_send(
                PRESENCE_GROUP,
                {"type": "presence_change", "user_id": self.user.id, "is_online": False},
            )

    async def send_notification(self, event):
        await self.send(text_data=json.dumps(event["data"]))

    async def presence_change(self, event):
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def get_user(self):
        token = None
        query_string = self.scope.get("query_string", b"").decode()
        for param in query_string.split("&"):
            if param.startswith("token="):
                token = param.split("=", 1)[1]
                break
        if not token:
            return None
        try:
            access = AccessToken(token)
            return User.objects.get(id=access["user_id"])
        except Exception:
            return None
