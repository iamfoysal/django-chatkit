
from django.contrib import admin
from .models import ChatRoom, Message, Attachment, UserSettings, Friendship, FriendRequest, InvitationLink

@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ("id", "slug", "title")
    search_fields = ("slug", "title")
    filter_horizontal = ("participants",)

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("id", "chat", "sender", "created_at")
    search_fields = ("content",)

@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ("id", "message", "file", "content_type", "size")

@admin.register(UserSettings)
class UserSettingsAdmin(admin.ModelAdmin):
    list_display = ("user", "theme")

@admin.register(Friendship)
class FriendshipAdmin(admin.ModelAdmin):
    list_display = ("id", "user1", "user2", "created_at", "chat_room")
    search_fields = ("user1__username", "user2__username")
    list_filter = ("created_at",)
    raw_id_fields = ("user1", "user2", "chat_room")

@admin.register(FriendRequest)
class FriendRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "from_user", "to_user", "status", "created_at")
    search_fields = ("from_user__username", "to_user__username")
    list_filter = ("status", "created_at")
    raw_id_fields = ("from_user", "to_user")

@admin.register(InvitationLink)
class InvitationLinkAdmin(admin.ModelAdmin):
    list_display = ("id", "created_by", "token_preview", "use_count", "max_uses", "is_active", "created_at", "expires_at")
    search_fields = ("created_by__username", "token")
    list_filter = ("is_active", "created_at")
    raw_id_fields = ("created_by",)
    readonly_fields = ("token",)
    
    def token_preview(self, obj):
        return f"{obj.token[:16]}..."
    token_preview.short_description = "Token"

