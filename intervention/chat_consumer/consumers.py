from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from intervention_app.models import Intervention, Message
import json

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f"chat_{self.room_name}"
        
        # Get the user from the scope
        self.user = self.scope.get('user', AnonymousUser())
        print(f"WebSocket connect - User: {self.user}, Room: {self.room_name}")
        
        # Check if intervention exists and user has access
        if not await self.can_access_intervention():
            print(f"WebSocket connect - Access denied for user {self.user} to room {self.room_name}")
            await self.close()
            return
        
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        
        # Send welcome message
        await self.send(text_data=json.dumps({
            'type': 'system',
            'message': f'Connected to intervention #{self.room_name}',
            'user': 'System'
        }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_content = data.get('message', '').strip()
        
        if not message_content:
            return
        
        # Check if user is a client (only clients can send messages)
        if self.user.user_type != 'client':
            print(f"WebSocket receive - Access denied: User {self.user} (type: {self.user.user_type}) cannot send messages")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Only clients can send messages in the chat.'
            }))
            return
        
        # Save message to database
        saved_message = await self.save_message(message_content)
        
        # Send message to group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': saved_message.content,
                'user': saved_message.user.username,
                'timestamp': saved_message.timestamp.isoformat(),
                'user_id': saved_message.user.id,
                'message_type': saved_message.message_type,
                'user_type': saved_message.user.user_type
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat',
            'message': event['message'],
            'user': event['user'],
            'timestamp': event['timestamp'],
            'user_id': event['user_id'],
            'message_type': event['message_type'],
            'user_type': event['user_type']
        }))

    @database_sync_to_async
    def can_access_intervention(self):
        try:
            intervention = Intervention.objects.get(id=self.room_name)
            # For now, allow any authenticated user to access any intervention
            # You can add more specific access control here
            return self.user.is_authenticated
        except Intervention.DoesNotExist:
            return False

    @database_sync_to_async
    def save_message(self, content):
        intervention = Intervention.objects.get(id=self.room_name)
        return Message.objects.create(
            intervention=intervention,
            user=self.user,
            content=content
        )
