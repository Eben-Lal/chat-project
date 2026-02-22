import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from .models import Message
from accounts.models import User

class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.user = self.scope["user"]

        if not self.user.is_authenticated:
            await self.close()
            return

        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
        self.room_group_name = self.room_name

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        # Get receiver id from room
        user1_id = int(self.room_name.split("_")[1])
        user2_id = int(self.room_name.split("_")[2])

        receiver_id = user2_id if self.user.id == user1_id else user1_id
         
        receiver = await database_sync_to_async(User.objects.get)(id=receiver_id)

        # Mark messages as read
        await database_sync_to_async(
            Message.objects.filter(
                sender_id=receiver_id,
                receiver=self.user,
                is_read=False
            ).update
        )(is_read=True)

        await self.channel_layer.group_send(
            f"user_{self.user.id}",
            {
            "type": "unread_update",
            "sender_id": receiver_id,
            "count": 0,
            }
        )

        # Notify sender that messages are read
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "read_update",
                "reader_id": self.user.id,
            }
        )

        await self.update_online_status(True)

    async def disconnect(self, close_code):
        await self.update_online_status(False)

        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    async def receive(self, text_data):
        data = json.loads(text_data)
        message_text = data["message"]

        # FIXED receiver logic
        user1_id = int(self.room_name.split("_")[1])
        user2_id = int(self.room_name.split("_")[2])

        receiver_id = user2_id if self.user.id == user1_id else user1_id

        receiver = await database_sync_to_async(User.objects.get)(id=receiver_id)

        # Save message
        message_obj = await database_sync_to_async(Message.objects.create)(
            sender=self.user,
            receiver=receiver,
            content=message_text,
            is_read=False
        )

        # Count unread from THIS sender only
        unread_count = await database_sync_to_async(
            Message.objects.filter(
                sender=self.user,
                receiver=receiver,
                is_read=False
            ).count
        )()

        # Send message to chat room
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "message": message_obj.content,
                "sender": self.user.username,
                "sender_id": self.user.id,
                "message_id": message_obj.id,
                "is_read": False,
            }
        )

        # Send unread update ONLY to receiver
        await self.channel_layer.group_send(
            f"user_{receiver_id}",
            {
                "type": "unread_update",
                "sender_id": self.user.id,
                "count": unread_count,
            }
        )
    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            "type": "chat_message",
            "message": event["message"],
            "sender": event["sender"],
            "is_sender": self.user.id == event["sender_id"],
            "is_read": event["is_read"],
        }))

    async def read_update(self, event):
        await self.send(text_data=json.dumps({
            "type": "read_update",
            "reader_id": event["reader_id"]
        }))

    @database_sync_to_async
    def update_online_status(self, status):
        self.user.is_online = status
        self.user.last_seen = timezone.now()
        self.user.save()

class NotificationConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.user = self.scope["user"]

        if self.user.is_anonymous:
            await self.close()
            return

        self.group_name = f"user_{self.user.id}"

        # Personal group (for unread)
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        # Global group (for online status)
        await self.channel_layer.group_add(
            "global_users",
            self.channel_name
        )

        await self.accept()

        # Mark online
        await self.update_online_status(True)

    async def disconnect(self, close_code):

        # Mark offline
        await self.update_online_status(False)

        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

        await self.channel_layer.group_discard(
            "global_users",
            self.channel_name
        )

    async def update_online_status(self, is_online):
        await database_sync_to_async(
            User.objects.filter(id=self.user.id).update
        )(is_online=is_online)

        await self.channel_layer.group_send(
            "global_users",
            {
                "type": "status_update",
                "user_id": self.user.id,
                "is_online": is_online,
            }
        )

    async def unread_update(self, event):
        await self.send(text_data=json.dumps({
            "type": "unread_update",
            "sender_id": event["sender_id"],
            "count": event["count"]
        }))

    async def status_update(self, event):
        await self.send(text_data=json.dumps({
            "type": "status_update",
            "user_id": event["user_id"],
            "is_online": event["is_online"]
        }))