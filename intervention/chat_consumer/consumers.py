from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from intervention_app.models import Intervention, Message
import json
from channels.layers import get_channel_layer
from django.db import models

class InterventionMixin:
    @database_sync_to_async
    def get_intervention(self):
        try:
            return Intervention.objects.get(id=self.room_name)
        except Intervention.DoesNotExist:
            return None

    @database_sync_to_async
    def save_message(self, content):
        intervention = Intervention.objects.get(id=self.room_name)
        # Set message type based on user type
        if self.user.is_employee():
            message_type = 'employee_message'
        else:
            message_type = 'client_message'
            
        return Message.objects.create(
            intervention=intervention,
            user=self.user,
            content=content,
            message_type=message_type
        )

    @database_sync_to_async
    def get_room_participant_user_ids_excluding_sender(self):
        try:
            intervention = Intervention.objects.get(id=self.room_name)
            # Include both creator and assigned employee
            participant_ids = {intervention.created_by_id}
            if intervention.assigned_to_id:
                participant_ids.add(intervention.assigned_to_id)
            
            # Remove current sender from recipients
            if self.user and self.user.id in participant_ids:
                participant_ids.discard(self.user.id)
                
            return list(participant_ids)
        except Intervention.DoesNotExist:
            return []

class ChatConsumer(AsyncWebsocketConsumer, InterventionMixin):
    @database_sync_to_async
    def can_access_intervention(self):
        try:
            intervention = Intervention.objects.get(id=self.room_name)
            # Allow only the creator or assigned employee/admin to access
            if not self.user.is_authenticated:
                return False
            
            # Check if user is admin or employee
            if self.user.user_type in ['admin', 'employee']:
                return True
                
            # For clients, check if they created the intervention
            allowed_ids = [intervention.created_by_id]
            if intervention.assigned_to_id:
                allowed_ids.append(intervention.assigned_to_id)
            return self.user.id in allowed_ids
        except Intervention.DoesNotExist:
            return False
        
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

        # Get intervention instance
        intervention = await self.get_intervention()

        # Prevent sending messages if intervention is closed
        if intervention and getattr(intervention, 'status', None) == 'closed':
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Chat is closed. No more messages can be sent.'
            }))
            return

        # Handle client rating after chat closed
        if intervention and intervention.status == 'closed' and self.user.user_type == 'client' and data.get('action') == 'rate_chat':
            rating = data.get('rating')
            if rating:
                await self.save_rating(intervention.id, rating)
            await self.send(text_data=json.dumps({
                'type': 'system',
                'message': f'Thank you for rating this chat: {rating} stars.'
            }))
            return

        # Employee can end chat by sending a special command
        if self.user.user_type == 'employee' and data.get('action') == 'end_chat':
            await self.end_chat()
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': 'Chat has been ended by the employee.',
                    'user': self.user.username,
                    'timestamp': '',
                    'user_id': self.user.id,
                    'message_type': 'system_message',
                    'user_type': self.user.user_type
                }
            )
            # Close the WebSocket connection for all users in the group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'close_chat_channel'
                }
            )
            return

        if not message_content:
            return

        # Allow both client and employee to send messages
        if self.user.user_type not in ['client', 'employee']:
            print(f"WebSocket receive - Access denied: User {self.user} (type: {self.user.user_type}) cannot send messages")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Only clients and employees can send messages in the chat.'
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

        # Also send a lightweight notification event to the recipient user's personal group
        try:
            channel_layer = get_channel_layer()
            # Determine target users in this room besides the sender
            recipient_user_ids = await self.get_room_participant_user_ids_excluding_sender()
            for rid in recipient_user_ids:
                await channel_layer.group_send(
                    f"user_{rid}",
                    {
                        'type': 'notify_event',
                        'event': 'new_message',
                        'intervention_id': self.room_name,
                        'from_user': saved_message.user.username,
                        'message': saved_message.content,
                        'timestamp': saved_message.timestamp.isoformat(),
                        'title': (await self.get_intervention()).title if await self.get_intervention() else f"Intervention {self.room_name}",
                    }
                )
        except Exception as e:
            # best-effort; don't disrupt chat
            print(f"Notify event failed: {e}")

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

    async def close_chat_channel(self, event):
        # Send a message to the frontend to trigger rating for client, redirect for employee
        user_type = getattr(self.user, 'user_type', None)
        if user_type == 'client':
            await self.send(text_data=json.dumps({
                'type': 'close_chat_channel',
                'show_rating': True
            }))
        else:
            await self.send(text_data=json.dumps({
                'type': 'close_chat_channel',
                'show_rating': False
            }))
        await self.close()

    @database_sync_to_async
    def get_intervention(self):
        try:
            return Intervention.objects.get(id=self.room_name)
        except Intervention.DoesNotExist:
            return None

class UserNotificationConsumer(AsyncWebsocketConsumer, InterventionMixin):
    async def connect(self):
        self.user = self.scope.get('user', AnonymousUser())
        if not getattr(self.user, 'is_authenticated', False):
            await self.close()
            return
        self.group_name = f"user_{self.user.id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def notify_event(self, event):
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def get_room_participant_user_ids_excluding_sender(self):
        try:
            intervention = Intervention.objects.get(id=self.room_name)
            # Include both creator and assigned employee
            participant_ids = {intervention.created_by_id}
            if intervention.assigned_to_id:
                participant_ids.add(intervention.assigned_to_id)
            
            # Remove current sender from recipients
            if self.user and self.user.id in participant_ids:
                participant_ids.discard(self.user.id)
                
            return list(participant_ids)
        except Intervention.DoesNotExist:
            return []

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
        # Set message type based on user type
        if self.user.is_employee():
            message_type = 'employee_message'
        else:
            message_type = 'client_message'
            
        return Message.objects.create(
            intervention=intervention,
            user=self.user,
            content=content,
            message_type=message_type
        )

    @database_sync_to_async
    def end_chat(self):
        intervention = Intervention.objects.get(id=self.room_name)
        intervention.end_chat_by_employee()
        # Mark intervention as closed after chat ends
        intervention.status = 'closed'
        intervention.save()

    @database_sync_to_async
    def get_intervention(self):
        try:
            return Intervention.objects.get(id=self.room_name)
        except Intervention.DoesNotExist:
            return None

    @database_sync_to_async
    def save_rating(self, intervention_id, rating):
        intervention = Intervention.objects.get(id=intervention_id)
        intervention.chat_rating = rating
        intervention.save()
