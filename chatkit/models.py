
from __future__ import annotations
from django.conf import settings
from django.db import models
from django.utils.text import slugify
from django.utils import timezone
import secrets
import hashlib

class ChatRoom(models.Model):
    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=120, blank=True)
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="chat_rooms", blank=True)

    def __str__(self):
        return self.title or self.slug

    @staticmethod
    def get_or_create_dm(user_a, user_b):
        base = f"dm-{min(user_a.id, user_b.id)}-{max(user_a.id, user_b.id)}"
        slug = slugify(base)
        room, _ = ChatRoom.objects.get_or_create(slug=slug, defaults={"title": f"DM {user_a} & {user_b}"})
        room.participants.add(user_a, user_b)
        return room

class Message(models.Model):
    chat = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="messages")
    content = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_seen = models.BooleanField(default=False)
    seen_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at"]

    def mark_as_seen(self):
        """Mark message as seen"""
        if not self.is_seen:
            self.is_seen = True
            self.seen_at = timezone.now()
            self.save(update_fields=['is_seen', 'seen_at'])

    def to_dict(self):
        return {
            "id": self.id,
            "chat": self.chat.slug,
            "sender": getattr(self.sender, "username", str(self.sender)),
            "content": self.content,
            "created_at": self.created_at.isoformat(),
            "attachments": [a.to_dict() for a in self.attachments.all()],
            "is_seen": self.is_seen,
            "seen_at": self.seen_at.isoformat() if self.seen_at else None,
        }

class Attachment(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to="chat_attachments/%Y/%m/%d/")
    content_type = models.CharField(max_length=120, blank=True)
    size = models.PositiveIntegerField(default=0)

    def save(self, *args, **kwargs):
        if self.file and hasattr(self.file, "size"):
            self.size = self.file.size
        super().save(*args, **kwargs)

    def to_dict(self):
        return {
            "url": self.file.url if self.file else "",
            "name": getattr(self.file, "name", ""),
            "content_type": self.content_type,
            "size": self.size,
        }

class UserSettings(models.Model):
    THEME_CHOICES = [("system", "System"), ("light", "Light"), ("dark", "Dark")]
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="chatkit_settings")
    theme = models.CharField(max_length=12, choices=THEME_CHOICES, default="system")
    profile_image = models.ImageField(upload_to="profile_images/", null=True, blank=True)

    def __str__(self):
        return f"{self.user} settings"
    
    def get_profile_image_url(self):
        """Get profile image URL or None"""
        if self.profile_image:
            return self.profile_image.url
        return None
    
    def get_initial(self):
        """Get first letter of username"""
        return self.user.username[:1].upper() if self.user.username else "U"


class Friendship(models.Model):
    """Represents a mutual friendship between two users"""
    user1 = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="friendships_as_user1")
    user2 = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="friendships_as_user2")
    created_at = models.DateTimeField(auto_now_add=True)
    chat_room = models.OneToOneField(ChatRoom, on_delete=models.SET_NULL, null=True, blank=True, related_name="friendship")

    class Meta:
        unique_together = [["user1", "user2"]]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user1} & {self.user2}"

    @classmethod
    def are_friends(cls, user_a, user_b):
        """Check if two users are friends"""
        if user_a == user_b:
            return False
        return cls.objects.filter(
            models.Q(user1=user_a, user2=user_b) | models.Q(user1=user_b, user2=user_a)
        ).exists()

    @classmethod
    def get_friendship(cls, user_a, user_b):
        """Get friendship object between two users"""
        return cls.objects.filter(
            models.Q(user1=user_a, user2=user_b) | models.Q(user1=user_b, user2=user_a)
        ).first()

    @classmethod
    def create_friendship(cls, user_a, user_b):
        """Create a new friendship and associated chat room"""
        if user_a == user_b:
            return None
        
        # Ensure consistent ordering to avoid duplicates
        if user_a.id > user_b.id:
            user_a, user_b = user_b, user_a
        
        # Create chat room for this friendship
        room = ChatRoom.get_or_create_dm(user_a, user_b)
        
        # Create friendship
        friendship, created = cls.objects.get_or_create(
            user1=user_a, 
            user2=user_b,
            defaults={"chat_room": room}
        )
        
        if created and not friendship.chat_room:
            friendship.chat_room = room
            friendship.save()
        
        return friendship

    def get_other_user(self, user):
        """Get the other user in the friendship"""
        return self.user2 if self.user1 == user else self.user1


class FriendRequest(models.Model):
    """Represents a friend request from one user to another"""
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("rejected", "Rejected"),
    ]
    
    from_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_friend_requests")
    to_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="received_friend_requests")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [["from_user", "to_user"]]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.from_user} → {self.to_user} ({self.status})"

    def accept(self):
        """Accept the friend request and create friendship"""
        self.status = "accepted"
        self.save()
        Friendship.create_friendship(self.from_user, self.to_user)

    def reject(self):
        """Reject the friend request"""
        self.status = "rejected"
        self.save()


class InvitationLink(models.Model):
    """Invitation links that users can share to invite friends"""
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="invitation_links")
    token = models.CharField(max_length=64, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    max_uses = models.PositiveIntegerField(default=1, help_text="Maximum number of times this link can be used")
    use_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Invitation by {self.created_by} - {self.token[:8]}..."

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = self.generate_token()
        super().save(*args, **kwargs)

    @staticmethod
    def generate_token():
        """Generate a unique secure token"""
        random_string = secrets.token_urlsafe(32)
        return hashlib.sha256(random_string.encode()).hexdigest()

    def is_valid(self):
        """Check if the invitation link is still valid"""
        if not self.is_active:
            return False
        if self.use_count >= self.max_uses:
            return False
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        return True

    def use(self, user):
        """Mark the invitation as used by a user and create friendship"""
        if not self.is_valid():
            return False
        
        self.use_count += 1
        self.save()
        
        # Create friendship between inviter and invitee
        Friendship.create_friendship(self.created_by, user)
        return True

