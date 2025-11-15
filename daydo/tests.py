from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from .models import (
    Family, Role, User, UserRole, SharingStatus, Location,
    Conversation, Message, MessageReaction, MessageReadStatus
)


SQLITE_TEST_DB = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}


@override_settings(DATABASES=SQLITE_TEST_DB)
class MapboxTokenViewTests(APITestCase):
    def setUp(self):
        self.family = Family.objects.create(name="Test Family")
        self.parent_role = Role.objects.create(key="PARENT", name="Parent")
        self.user = User.objects.create_user(
            username="parent_user",
            email="parent@example.com",
            password="password123",
            first_name="Parent",
            last_name="User",
            family=self.family,
            role="PARENT",
        )
        UserRole.objects.create(user=self.user, role=self.parent_role)
        self.url = reverse("daydo:mapbox-token")

    @override_settings(MAPBOX_PUBLIC_TOKEN="pk.test-token")
    def test_returns_token_for_authenticated_user(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"token": "pk.test-token"})

    @override_settings(MAPBOX_PUBLIC_TOKEN="")
    def test_returns_503_when_token_missing(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(
            response.data.get("detail"),
            "Mapbox token is not configured on the server.",
        )

    def test_requires_authentication(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


@override_settings(DATABASES=SQLITE_TEST_DB)
class FamilyLocationViewTests(APITestCase):
    def setUp(self):
        self.family = Family.objects.create(name="Test Family")
        self.parent_role = Role.objects.create(key="PARENT", name="Parent")
        self.user = User.objects.create_user(
            username="parent_primary",
            email="primary@example.com",
            password="password123",
            first_name="Primary",
            last_name="Parent",
            family=self.family,
            role="PARENT",
        )
        UserRole.objects.create(user=self.user, role=self.parent_role)
        SharingStatus.objects.create(
            user=self.user,
            is_sharing_live=True,
            sharing_type="always",
        )

        self.stale_user = User.objects.create_user(
            username="parent_secondary",
            email="secondary@example.com",
            password="password123",
            first_name="Secondary",
            last_name="Parent",
            family=self.family,
            role="PARENT",
        )
        UserRole.objects.create(user=self.stale_user, role=self.parent_role)
        SharingStatus.objects.create(
            user=self.stale_user,
            is_sharing_live=True,
            sharing_type="always",
        )

        self.url = reverse("daydo:location-family")

    def test_family_locations_include_accuracy_and_stale_flag(self):
        self.client.force_authenticate(user=self.user)

        Location.objects.create(
            sharing_user=self.user,
            latitude=50.1109,
            longitude=8.6821,
            accuracy=5.5,
        )
        stale_timestamp = timezone.now() - timedelta(minutes=20)
        stale_location = Location.objects.create(
            sharing_user=self.stale_user,
            latitude=48.1351,
            longitude=11.5820,
            accuracy=15.2,
        )
        Location.objects.filter(id=stale_location.id).update(timestamp=stale_timestamp)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(isinstance(response.data, list))

        data_by_user = {item["user_id"]: item for item in response.data}
        fresh_entry = data_by_user[str(self.user.id)]
        stale_entry = data_by_user[str(self.stale_user.id)]

        self.assertIn("accuracy", fresh_entry)
        self.assertEqual(float(fresh_entry["accuracy"]), 5.5)
        self.assertFalse(fresh_entry.get("is_stale"))

        self.assertIn("accuracy", stale_entry)
        self.assertEqual(float(stale_entry["accuracy"]), 15.2)
        self.assertTrue(stale_entry.get("is_stale"))


# Chat Model Tests
@override_settings(DATABASES=SQLITE_TEST_DB)
class ConversationModelTests(APITestCase):
    """Tests for Conversation model"""
    
    def setUp(self):
        self.family = Family.objects.create(name="Test Family")
        self.parent_role = Role.objects.create(key="PARENT", name="Parent")
        self.user1 = User.objects.create_user(
            username="user1",
            email="user1@example.com",
            password="password123",
            first_name="User",
            last_name="One",
            family=self.family,
            role="PARENT",
        )
        UserRole.objects.create(user=self.user1, role=self.parent_role)
        
        self.user2 = User.objects.create_user(
            username="user2",
            email="user2@example.com",
            password="password123",
            first_name="User",
            last_name="Two",
            family=self.family,
            role="PARENT",
        )
        UserRole.objects.create(user=self.user2, role=self.parent_role)
    
    def test_create_family_conversation(self):
        """Test creating a family conversation"""
        conversation = Conversation.objects.create(
            family=self.family,
            conversation_type='family'
        )
        conversation.participants.set([self.user1, self.user2])
        
        self.assertEqual(conversation.family, self.family)
        self.assertEqual(conversation.conversation_type, 'family')
        self.assertEqual(conversation.participants.count(), 2)
        self.assertIn(self.user1, conversation.participants.all())
        self.assertIn(self.user2, conversation.participants.all())
    
    def test_create_direct_conversation(self):
        """Test creating a direct message conversation"""
        conversation = Conversation.objects.create(
            family=self.family,
            conversation_type='direct'
        )
        conversation.participants.set([self.user1, self.user2])
        
        self.assertEqual(conversation.family, self.family)
        self.assertEqual(conversation.conversation_type, 'direct')
        self.assertEqual(conversation.participants.count(), 2)


@override_settings(DATABASES=SQLITE_TEST_DB)
class MessageModelTests(APITestCase):
    """Tests for Message model"""
    
    def setUp(self):
        self.family = Family.objects.create(name="Test Family")
        self.parent_role = Role.objects.create(key="PARENT", name="Parent")
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="password123",
            first_name="Test",
            last_name="User",
            family=self.family,
            role="PARENT",
        )
        UserRole.objects.create(user=self.user, role=self.parent_role)
        
        self.conversation = Conversation.objects.create(
            family=self.family,
            conversation_type='family'
        )
        self.conversation.participants.set([self.user])
    
    def test_create_message(self):
        """Test creating a message"""
        message = Message.objects.create(
            conversation=self.conversation,
            sender=self.user,
            content="Test message",
            message_type='text'
        )
        
        self.assertEqual(message.conversation, self.conversation)
        self.assertEqual(message.sender, self.user)
        self.assertEqual(message.content, "Test message")
        self.assertEqual(message.message_type, 'text')
        self.assertFalse(message.is_edited)
    
    def test_message_can_update_conversation_last_message_at(self):
        """Test that we can update conversation's last_message_at when creating a message"""
        initial_time = self.conversation.last_message_at
        
        message = Message.objects.create(
            conversation=self.conversation,
            sender=self.user,
            content="Test message",
            message_type='text'
        )
        
        # Update conversation's last_message_at (this is done in the consumer)
        self.conversation.last_message_at = message.created_at
        self.conversation.save(update_fields=['last_message_at'])
        
        self.conversation.refresh_from_db()
        self.assertIsNotNone(self.conversation.last_message_at)
        if initial_time:
            self.assertGreater(self.conversation.last_message_at, initial_time)


@override_settings(DATABASES=SQLITE_TEST_DB)
class MessageReactionModelTests(APITestCase):
    """Tests for MessageReaction model"""
    
    def setUp(self):
        self.family = Family.objects.create(name="Test Family")
        self.parent_role = Role.objects.create(key="PARENT", name="Parent")
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="password123",
            first_name="Test",
            last_name="User",
            family=self.family,
            role="PARENT",
        )
        UserRole.objects.create(user=self.user, role=self.parent_role)
        
        self.conversation = Conversation.objects.create(
            family=self.family,
            conversation_type='family'
        )
        self.conversation.participants.set([self.user])
        
        self.message = Message.objects.create(
            conversation=self.conversation,
            sender=self.user,
            content="Test message",
            message_type='text'
        )
    
    def test_create_reaction(self):
        """Test creating a message reaction"""
        reaction = MessageReaction.objects.create(
            message=self.message,
            user=self.user,
            emoji="👍"
        )
        
        self.assertEqual(reaction.message, self.message)
        self.assertEqual(reaction.user, self.user)
        self.assertEqual(reaction.emoji, "👍")
    
    def test_unique_reaction_per_user_per_message(self):
        """Test that a user can only have one reaction per emoji per message"""
        MessageReaction.objects.create(
            message=self.message,
            user=self.user,
            emoji="👍"
        )
        
        # Try to create duplicate reaction - should raise IntegrityError
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            MessageReaction.objects.create(
                message=self.message,
                user=self.user,
                emoji="👍"
            )


@override_settings(DATABASES=SQLITE_TEST_DB)
class MessageReadStatusModelTests(APITestCase):
    """Tests for MessageReadStatus model"""
    
    def setUp(self):
        self.family = Family.objects.create(name="Test Family")
        self.parent_role = Role.objects.create(key="PARENT", name="Parent")
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="password123",
            first_name="Test",
            last_name="User",
            family=self.family,
            role="PARENT",
        )
        UserRole.objects.create(user=self.user, role=self.parent_role)
        
        self.conversation = Conversation.objects.create(
            family=self.family,
            conversation_type='family'
        )
        self.conversation.participants.set([self.user])
        
        self.message = Message.objects.create(
            conversation=self.conversation,
            sender=self.user,
            content="Test message",
            message_type='text'
        )
    
    def test_create_read_status(self):
        """Test creating a read status"""
        read_status = MessageReadStatus.objects.create(
            message=self.message,
            user=self.user
        )
        
        self.assertEqual(read_status.message, self.message)
        self.assertEqual(read_status.user, self.user)
        self.assertIsNotNone(read_status.read_at)
    
    def test_unique_read_status_per_user_per_message(self):
        """Test that a user can only have one read status per message"""
        MessageReadStatus.objects.create(
            message=self.message,
            user=self.user
        )
        
        # Try to create duplicate read status - should raise IntegrityError
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            MessageReadStatus.objects.create(
                message=self.message,
                user=self.user
            )


# Chat API Tests
@override_settings(DATABASES=SQLITE_TEST_DB)
class ConversationViewSetTests(APITestCase):
    """Tests for ConversationViewSet API endpoints"""
    
    def setUp(self):
        self.family = Family.objects.create(name="Test Family")
        self.parent_role = Role.objects.create(key="PARENT", name="Parent")
        self.user1 = User.objects.create_user(
            username="user1",
            email="user1@example.com",
            password="password123",
            first_name="User",
            last_name="One",
            family=self.family,
            role="PARENT",
        )
        UserRole.objects.create(user=self.user1, role=self.parent_role)
        
        self.user2 = User.objects.create_user(
            username="user2",
            email="user2@example.com",
            password="password123",
            first_name="User",
            last_name="Two",
            family=self.family,
            role="PARENT",
        )
        UserRole.objects.create(user=self.user2, role=self.parent_role)
        
        self.client.force_authenticate(user=self.user1)
    
    def test_list_conversations(self):
        """Test listing conversations"""
        conversation = Conversation.objects.create(
            family=self.family,
            conversation_type='family'
        )
        conversation.participants.set([self.user1, self.user2])
        
        url = reverse("daydo:conversation-list")
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Handle pagination
        data = response.data['results'] if 'results' in response.data else response.data
        self.assertEqual(len(data), 1)
        self.assertEqual(str(data[0]['id']), str(conversation.id))
    
    def test_get_or_create_family_chat(self):
        """Test getting or creating family chat"""
        url = reverse("daydo:conversation-get-or-create-family-chat")
        response = self.client.post(url, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['conversation_type'], 'family')
        self.assertEqual(str(response.data['family']), str(self.family.id))
        
        # Verify all family members are participants
        participants = response.data['participants']
        self.assertEqual(len(participants), 2)
    
    def test_get_or_create_direct_message(self):
        """Test getting or creating direct message conversation"""
        url = reverse("daydo:conversation-get-or-create-direct-message")
        response = self.client.post(url, {'participant_id': str(self.user2.id)}, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['conversation_type'], 'direct')
        
        # Test getting existing conversation
        response2 = self.client.post(url, {'participant_id': str(self.user2.id)}, format='json')
        self.assertEqual(response2.status_code, status.HTTP_200_OK)  # Returns existing, so 200
        self.assertEqual(str(response.data['id']), str(response2.data['id']))
    
    def test_get_or_create_direct_message_missing_participant(self):
        """Test getting or creating direct message with missing participant_id"""
        url = reverse("daydo:conversation-get-or-create-direct-message")
        response = self.client.post(url, {}, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_get_conversation_messages(self):
        """Test getting messages for a conversation"""
        conversation = Conversation.objects.create(
            family=self.family,
            conversation_type='family'
        )
        conversation.participants.set([self.user1, self.user2])
        
        message1 = Message.objects.create(
            conversation=conversation,
            sender=self.user1,
            content="Message 1",
            message_type='text'
        )
        message2 = Message.objects.create(
            conversation=conversation,
            sender=self.user2,
            content="Message 2",
            message_type='text'
        )
        
        url = reverse("daydo:conversation-messages", kwargs={'pk': conversation.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Handle pagination
        data = response.data['results'] if 'results' in response.data else response.data
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]['content'], "Message 1")
        self.assertEqual(data[1]['content'], "Message 2")
    
    def test_mark_messages_as_read(self):
        """Test marking messages as read"""
        conversation = Conversation.objects.create(
            family=self.family,
            conversation_type='family'
        )
        conversation.participants.set([self.user1, self.user2])
        
        message = Message.objects.create(
            conversation=conversation,
            sender=self.user2,
            content="Test message",
            message_type='text'
        )
        
        url = reverse("daydo:conversation-mark-read", kwargs={'pk': conversation.id})
        response = self.client.post(url, {'message_ids': [str(message.id)]}, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(MessageReadStatus.objects.filter(
            message=message,
            user=self.user1
        ).exists())


@override_settings(DATABASES=SQLITE_TEST_DB)
class MessageViewSetTests(APITestCase):
    """Tests for MessageViewSet API endpoints"""
    
    def setUp(self):
        self.family = Family.objects.create(name="Test Family")
        self.parent_role = Role.objects.create(key="PARENT", name="Parent")
        self.user1 = User.objects.create_user(
            username="user1",
            email="user1@example.com",
            password="password123",
            first_name="User",
            last_name="One",
            family=self.family,
            role="PARENT",
        )
        UserRole.objects.create(user=self.user1, role=self.parent_role)
        
        self.user2 = User.objects.create_user(
            username="user2",
            email="user2@example.com",
            password="password123",
            first_name="User",
            last_name="Two",
            family=self.family,
            role="PARENT",
        )
        UserRole.objects.create(user=self.user2, role=self.parent_role)
        
        self.conversation = Conversation.objects.create(
            family=self.family,
            conversation_type='family'
        )
        self.conversation.participants.set([self.user1, self.user2])
        
        self.client.force_authenticate(user=self.user1)
    
    def test_create_message(self):
        """Test creating a message"""
        url = reverse("daydo:message-list")
        response = self.client.post(url, {
            'conversation': str(self.conversation.id),
            'content': 'Test message',
            'message_type': 'text'
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['content'], 'Test message')
        self.assertEqual(str(response.data['sender_id']), str(self.user1.id))
    
    def test_list_messages_with_conversation_id(self):
        """Test listing messages filtered by conversation_id"""
        message1 = Message.objects.create(
            conversation=self.conversation,
            sender=self.user1,
            content="Message 1",
            message_type='text'
        )
        message2 = Message.objects.create(
            conversation=self.conversation,
            sender=self.user2,
            content="Message 2",
            message_type='text'
        )
        
        url = reverse("daydo:message-list")
        response = self.client.get(url, {'conversation_id': str(self.conversation.id)})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Handle pagination
        data = response.data['results'] if 'results' in response.data else response.data
        self.assertEqual(len(data), 2)
    
    def test_list_messages_without_conversation_id(self):
        """Test listing messages without conversation_id returns empty"""
        url = reverse("daydo:message-list")
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Handle pagination
        data = response.data['results'] if 'results' in response.data else response.data
        self.assertEqual(len(data), 0)
    
    def test_cannot_access_messages_from_other_conversation(self):
        """Test that users cannot access messages from conversations they're not in"""
        other_family = Family.objects.create(name="Other Family")
        other_user = User.objects.create_user(
            username="otheruser",
            email="other@example.com",
            password="password123",
            first_name="Other",
            last_name="User",
            family=other_family,
            role="PARENT",
        )
        UserRole.objects.create(user=other_user, role=self.parent_role)
        
        other_conversation = Conversation.objects.create(
            family=other_family,
            conversation_type='family'
        )
        other_conversation.participants.set([other_user])
        
        Message.objects.create(
            conversation=other_conversation,
            sender=other_user,
            content="Private message",
            message_type='text'
        )
        
        url = reverse("daydo:message-list")
        response = self.client.get(url, {'conversation_id': str(other_conversation.id)})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Handle pagination
        data = response.data['results'] if 'results' in response.data else response.data
        self.assertEqual(len(data), 0)  # Should return empty, not error
