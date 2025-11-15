"""
WebSocket consumers for chat functionality.
"""
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.utils import timezone
from daydo.models import Conversation, Message, MessageReadStatus

User = get_user_model()


class ChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for chat conversations.
    Handles real-time messaging, typing indicators, and read receipts.
    """
    
    async def connect(self):
        """Handle WebSocket connection"""
        self.user = self.scope["user"]
        if not self.user.is_authenticated:
            await self.close()
            return
        
        # Get conversation ID from URL route
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.room_group_name = f'chat_{self.conversation_id}'
        
        # Verify user has access to conversation
        has_access = await self.verify_conversation_access()
        if not has_access:
            await self.close()
            return
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send recent messages
        await self.send_recent_messages()
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'chat_message':
                await self.handle_chat_message(data)
            elif message_type == 'typing':
                await self.handle_typing(data)
            elif message_type == 'read_receipt':
                await self.handle_read_receipt(data)
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format'
            }))
    
    async def handle_chat_message(self, data):
        """Handle incoming chat message"""
        content = data.get('content', '').strip()
        if not content:
            return
        
        # Save message to database
        message = await self.save_message(content)
        
        # Broadcast to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': {
                    'id': str(message.id),
                    'sender_id': str(message.sender.id),
                    'sender_name': message.sender.get_display_name(),
                    'sender_avatar': message.sender.avatar or '',
                    'sender_color': message.sender.color or '#3b82f6',
                    'content': message.content,
                    'created_at': message.created_at.isoformat(),
                    'message_type': message.message_type,
                    'is_edited': message.is_edited,
                }
            }
        )
    
    async def handle_typing(self, data):
        """Handle typing indicator"""
        # Broadcast typing indicator to other participants
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_indicator',
                'user_id': str(self.user.id),
                'user_name': self.user.get_display_name(),
                'is_typing': data.get('is_typing', True),
            }
        )
    
    async def handle_read_receipt(self, data):
        """Handle read receipt"""
        message_id = data.get('message_id')
        if message_id:
            await self.mark_message_as_read(message_id)
    
    async def chat_message(self, event):
        """Send message to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'message',
            'data': event['message']
        }))
    
    async def typing_indicator(self, event):
        """Send typing indicator to WebSocket"""
        # Don't send typing indicator to the user who is typing
        if str(event['user_id']) != str(self.user.id):
            await self.send(text_data=json.dumps({
                'type': 'typing',
                'data': {
                    'user_id': event['user_id'],
                    'user_name': event['user_name'],
                    'is_typing': event['is_typing'],
                }
            }))
    
    @database_sync_to_async
    def verify_conversation_access(self):
        """Verify that the user has access to this conversation"""
        try:
            conversation = Conversation.objects.get(id=self.conversation_id)
            return self.user in conversation.participants.all()
        except Conversation.DoesNotExist:
            return False
    
    @database_sync_to_async
    def save_message(self, content):
        """Save message to database"""
        conversation = Conversation.objects.get(id=self.conversation_id)
        message = Message.objects.create(
            conversation=conversation,
            sender=self.user,
            content=content,
            message_type='text'
        )
        # Update conversation last_message_at
        conversation.last_message_at = message.created_at
        conversation.save(update_fields=['last_message_at'])
        return message
    
    @database_sync_to_async
    def get_recent_messages(self, limit=50):
        """Get recent messages for the conversation"""
        conversation = Conversation.objects.get(id=self.conversation_id)
        messages = Message.objects.filter(conversation=conversation).order_by('-created_at')[:limit]
        return list(reversed(messages))
    
    @database_sync_to_async
    def mark_message_as_read(self, message_id):
        """Mark a message as read for the current user"""
        try:
            message = Message.objects.get(id=message_id, conversation_id=self.conversation_id)
            MessageReadStatus.objects.get_or_create(
                message=message,
                user=self.user,
                defaults={'read_at': timezone.now()}
            )
        except Message.DoesNotExist:
            pass
    
    async def send_recent_messages(self):
        """Send recent messages to the client on connection"""
        messages = await self.get_recent_messages()
        await self.send(text_data=json.dumps({
            'type': 'recent_messages',
            'data': [
                {
                    'id': str(msg.id),
                    'sender_id': str(msg.sender.id),
                    'sender_name': msg.sender.get_display_name(),
                    'sender_avatar': msg.sender.avatar or '',
                    'sender_color': msg.sender.color or '#3b82f6',
                    'content': msg.content,
                    'created_at': msg.created_at.isoformat(),
                    'message_type': msg.message_type,
                    'is_edited': msg.is_edited,
                }
                for msg in messages
            ]
        }))

