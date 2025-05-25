import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import Chat, Message

CustomUser = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.chat_id = self.scope['url_route']['kwargs']['chat_id']
        self.chat_group_name = f'chat_{self.chat_id}'

        # Проверяем, что пользователь имеет доступ к чату
        if await self.has_access():
            await self.channel_layer.group_add(
                self.chat_group_name,
                self.channel_name
            )
            await self.accept()
        else:
            await self.close()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.chat_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data['message']
        sender_id = self.scope['user'].id

        # Сохраняем сообщение в базе
        saved_message = await self.save_message(sender_id, message)

        # Отправляем сообщение в группу
        await self.channel_layer.group_send(
            self.chat_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'sender': self.scope['user'].username,
                'timestamp': saved_message.timestamp.isoformat()
            }
        )

    async def chat_message(self, event):
        # Отправляем сообщение всем в группе
        await self.send(text_data=json.dumps({
            'message': event['message'],
            'sender': event['sender'],
            'timestamp': event['timestamp']
        }))

    @database_sync_to_async
    def has_access(self):
        try:
            chat = Chat.objects.get(id=self.chat_id)
            return self.scope['user'].is_authenticated and (
                self.scope['user'] == chat.user or self.scope['user'].is_staff
            )
        except Chat.DoesNotExist:
            return False

    @database_sync_to_async
    def save_message(self, sender_id, content):
        return Message.objects.create(
            chat_id=self.chat_id,
            sender_id=sender_id,
            content=content
        )