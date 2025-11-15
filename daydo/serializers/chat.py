"""
Serializers for chat functionality.
"""
from rest_framework import serializers
from daydo.models import Conversation, Message, MessageReaction, MessageReadStatus


class MessageSerializer(serializers.ModelSerializer):
    """Serializer for Message model"""
    sender_name = serializers.CharField(source='sender.get_display_name', read_only=True)
    sender_avatar = serializers.CharField(source='sender.avatar', read_only=True)
    sender_id = serializers.UUIDField(source='sender.id', read_only=True)
    sender_color = serializers.CharField(source='sender.color', read_only=True)
    
    class Meta:
        model = Message
        fields = [
            'id', 'conversation', 'sender_id', 'sender_name', 'sender_avatar', 
            'sender_color', 'content', 'message_type', 'image_url', 'created_at', 
            'updated_at', 'is_edited'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'is_edited']


class ConversationSerializer(serializers.ModelSerializer):
    """Serializer for Conversation model"""
    participants = serializers.SerializerMethodField()
    last_message = MessageSerializer(read_only=True)
    unread_count = serializers.SerializerMethodField()
    other_participant = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = [
            'id', 'conversation_type', 'family', 'participants', 
            'created_at', 'updated_at', 'last_message_at', 'last_message', 
            'unread_count', 'other_participant'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'last_message_at']
    
    def get_participants(self, obj):
        """Get list of participants with their details"""
        return [
            {
                'id': str(p.id),
                'name': p.get_display_name(),
                'avatar': p.avatar or '',
                'color': p.color or '#3b82f6',
            }
            for p in obj.participants.all()
        ]
    
    def get_unread_count(self, obj):
        """Count unread messages for the current user"""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return 0
        
        user = request.user
        # Count unread messages for this user
        last_read = MessageReadStatus.objects.filter(
            user=user,
            message__conversation=obj
        ).order_by('-read_at').first()
        
        if last_read:
            unread = Message.objects.filter(
                conversation=obj,
                created_at__gt=last_read.read_at
            ).exclude(sender=user).count()
        else:
            unread = Message.objects.filter(conversation=obj).exclude(sender=user).count()
        
        return unread
    
    def get_other_participant(self, obj):
        """For direct messages, return the other participant"""
        if obj.conversation_type != 'direct':
            return None
        
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        
        user = request.user
        other = obj.participants.exclude(id=user.id).first()
        if other:
            return {
                'id': str(other.id),
                'display_name': other.get_display_name(),
                'avatar': other.avatar or '',
                'color': other.color or '#3b82f6',
            }
        return None

