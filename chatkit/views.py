
from __future__ import annotations
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpRequest, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.http import require_POST, require_http_methods
from django.utils import timezone
from django.db import transaction
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db.models import Q
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from datetime import timedelta

from .models import ChatRoom, Message, Attachment, UserSettings, Friendship, FriendRequest, InvitationLink
from .forms import MessageForm, FriendRequestForm, InvitationLinkForm

User = get_user_model()

@login_required
def index(request: HttpRequest) -> HttpResponse:
    # Get user's friends
    friendships = Friendship.objects.filter(
        Q(user1=request.user) | Q(user2=request.user)
    ).select_related('user1', 'user2', 'chat_room')
    
    friends_with_rooms = []
    for friendship in friendships:
        friend = friendship.get_other_user(request.user)
        friends_with_rooms.append({
            'friend': friend,
            'room': friendship.chat_room,
            'friendship': friendship,
        })
    
    # Get pending friend requests
    pending_requests = FriendRequest.objects.filter(
        to_user=request.user,
        status='pending'
    ).select_related('from_user').order_by('-created_at')
    
    # Get sent requests
    sent_requests = FriendRequest.objects.filter(
        from_user=request.user,
        status='pending'
    ).select_related('to_user').order_by('-created_at')
    
    return render(request, "chatkit/index.html", {
        "friends_with_rooms": friends_with_rooms,
        "pending_requests": pending_requests,
        "sent_requests": sent_requests,
    })

@login_required
def room(request: HttpRequest, slug: str) -> HttpResponse:
    room = get_object_or_404(ChatRoom, slug=slug)
    if (room.participants.exists()) and (request.user not in room.participants.all()):
        return HttpResponse("You are not a participant of this room.", status=403)

    messages = room.messages.select_related("sender").prefetch_related("attachments").order_by("-created_at")[:100]
    messages = list(reversed(messages))
    
    # Mark messages as seen (except user's own messages)
    unseen_messages = [msg for msg in messages if msg.sender != request.user and not msg.is_seen]
    for msg in unseen_messages:
        msg.mark_as_seen()
    
    form = MessageForm()
    settings_obj, _ = UserSettings.objects.get_or_create(user=request.user)
    return render(request, "chatkit/room.html", {"room": room, "messages": messages, "form": form, "settings": settings_obj})

@login_required
@require_POST
def api_send_message(request: HttpRequest) -> JsonResponse:
    form = MessageForm(request.POST, request.FILES)
    slug = request.POST.get("room_slug")
    if not slug:
        return HttpResponseBadRequest("Missing room_slug")
    room = get_object_or_404(ChatRoom, slug=slug)

    if (room.participants.exists()) and (request.user not in room.participants.all()):
        return JsonResponse({"error": "not a participant"}, status=403)

    if form.is_valid():
        with transaction.atomic():
            msg = Message.objects.create(chat=room, sender=request.user, content=form.cleaned_data.get("content", ""))
            files = request.FILES.getlist("files")
            for f in files:
                Attachment.objects.create(message=msg, file=f, content_type=getattr(f, "content_type", ""))
        # Broadcast via Channels
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"chat_{room.slug}",
            {"type": "chat.message", "message": msg.to_dict()},
        )
        return JsonResponse({"ok": True, "message": msg.to_dict()})
    return JsonResponse({"errors": form.errors}, status=400)

@login_required
def user_settings(request: HttpRequest):
    settings_obj, _ = UserSettings.objects.get_or_create(user=request.user)
    if request.method == "POST":
        theme = request.POST.get("theme", "system")
        if theme in dict(UserSettings.THEME_CHOICES):
            settings_obj.theme = theme
            settings_obj.save()
        
        # Handle AJAX requests (for smooth theme switching)
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"success": True, "theme": theme})
        
        # Handle HTMX requests (legacy support)
        if request.headers.get("HX-Request"):
            return render(request, "chatkit/_theme_toggle.html", {"settings": settings_obj})
        
        # Regular form submission fallback
        return redirect("chatkit:index")
    
    return render(request, "chatkit/settings.html", {"settings": settings_obj})


@login_required
def friends_list(request: HttpRequest) -> HttpResponse:
    """View to display and manage friends"""
    # Get all friendships
    friendships = Friendship.objects.filter(
        Q(user1=request.user) | Q(user2=request.user)
    ).select_related('user1', 'user2', 'chat_room')
    
    friends = []
    for friendship in friendships:
        friend = friendship.get_other_user(request.user)
        friends.append({
            'user': friend,
            'friendship': friendship,
            'room': friendship.chat_room,
        })
    
    # Get pending requests
    received_requests = FriendRequest.objects.filter(
        to_user=request.user,
        status='pending'
    ).select_related('from_user')
    
    sent_requests = FriendRequest.objects.filter(
        from_user=request.user,
        status='pending'
    ).select_related('to_user')
    
    # Forms
    friend_request_form = FriendRequestForm(current_user=request.user)
    invitation_form = InvitationLinkForm()
    
    # Get user's invitation links
    invitation_links = InvitationLink.objects.filter(
        created_by=request.user,
        is_active=True
    ).order_by('-created_at')
    
    context = {
        'friends': friends,
        'received_requests': received_requests,
        'sent_requests': sent_requests,
        'friend_request_form': friend_request_form,
        'invitation_form': invitation_form,
        'invitation_links': invitation_links,
    }
    
    return render(request, 'chatkit/friends.html', context)


@login_required
@require_POST
def send_friend_request(request: HttpRequest) -> HttpResponse:
    """Send a friend request to another user"""
    form = FriendRequestForm(request.POST, current_user=request.user)
    
    if form.is_valid():
        username = form.cleaned_data['username']
        try:
            to_user = User.objects.get(username=username)
            
            # Check if already friends
            if Friendship.are_friends(request.user, to_user):
                messages.warning(request, f"You are already friends with {to_user.username}.")
                return redirect('chatkit:friends')
            
            # Check if request already exists
            existing_request = FriendRequest.objects.filter(
                from_user=request.user,
                to_user=to_user,
                status='pending'
            ).first()
            
            if existing_request:
                messages.warning(request, f"You have already sent a friend request to {to_user.username}.")
                return redirect('chatkit:friends')
            
            # Check if reverse request exists
            reverse_request = FriendRequest.objects.filter(
                from_user=to_user,
                to_user=request.user,
                status='pending'
            ).first()
            
            if reverse_request:
                # Auto-accept and create friendship
                reverse_request.accept()
                messages.success(request, f"You are now friends with {to_user.username}!")
                return redirect('chatkit:friends')
            
            # Create new request
            FriendRequest.objects.create(
                from_user=request.user,
                to_user=to_user
            )
            messages.success(request, f"Friend request sent to {to_user.username}.")
            
        except User.DoesNotExist:
            messages.error(request, "User not found.")
    else:
        for error in form.errors.values():
            messages.error(request, error)
    
    return redirect('chatkit:friends')


@login_required
@require_POST
def accept_friend_request(request: HttpRequest, request_id: int) -> HttpResponse:
    """Accept a friend request"""
    friend_request = get_object_or_404(
        FriendRequest,
        id=request_id,
        to_user=request.user,
        status='pending'
    )
    
    friend_request.accept()
    messages.success(request, f"You are now friends with {friend_request.from_user.username}!")
    
    return redirect('chatkit:friends')


@login_required
@require_POST
def reject_friend_request(request: HttpRequest, request_id: int) -> HttpResponse:
    """Reject a friend request"""
    friend_request = get_object_or_404(
        FriendRequest,
        id=request_id,
        to_user=request.user,
        status='pending'
    )
    
    friend_request.reject()
    messages.info(request, f"Friend request from {friend_request.from_user.username} rejected.")
    
    return redirect('chatkit:friends')


@login_required
@require_POST
def cancel_friend_request(request: HttpRequest, request_id: int) -> HttpResponse:
    """Cancel a sent friend request"""
    friend_request = get_object_or_404(
        FriendRequest,
        id=request_id,
        from_user=request.user,
        status='pending'
    )
    
    friend_request.delete()
    messages.info(request, "Friend request cancelled.")
    
    return redirect('chatkit:friends')


@login_required
@require_POST
def remove_friend(request: HttpRequest, friendship_id: int) -> HttpResponse:
    """Remove a friend"""
    friendship = get_object_or_404(
        Friendship,
        id=friendship_id
    )
    
    # Ensure user is part of this friendship
    if friendship.user1 != request.user and friendship.user2 != request.user:
        return HttpResponse("Unauthorized", status=403)
    
    friend = friendship.get_other_user(request.user)
    friendship.delete()
    messages.success(request, f"You are no longer friends with {friend.username}.")
    
    return redirect('chatkit:friends')


@login_required
@require_POST
def create_invitation_link(request: HttpRequest) -> HttpResponse:
    """Create a new invitation link"""
    form = InvitationLinkForm(request.POST)
    
    if form.is_valid():
        max_uses = form.cleaned_data['max_uses']
        expires_in_days = form.cleaned_data.get('expires_in_days')
        
        invitation = InvitationLink(
            created_by=request.user,
            max_uses=max_uses
        )
        
        if expires_in_days:
            invitation.expires_at = timezone.now() + timedelta(days=expires_in_days)
        
        invitation.save()
        messages.success(request, "Invitation link created successfully!")
    else:
        messages.error(request, "Error creating invitation link.")
    
    return redirect('chatkit:friends')


@login_required
def accept_invitation(request: HttpRequest, token: str) -> HttpResponse:
    """Accept an invitation link"""
    invitation = get_object_or_404(InvitationLink, token=token)
    
    if not invitation.is_valid():
        messages.error(request, "This invitation link is no longer valid.")
        return redirect('chatkit:index')
    
    if invitation.created_by == request.user:
        messages.warning(request, "You cannot accept your own invitation.")
        return redirect('chatkit:friends')
    
    # Check if already friends
    if Friendship.are_friends(request.user, invitation.created_by):
        messages.warning(request, f"You are already friends with {invitation.created_by.username}.")
        return redirect('chatkit:index')
    
    # Use the invitation
    if invitation.use(request.user):
        messages.success(request, f"You are now friends with {invitation.created_by.username}!")
        return redirect('chatkit:index')
    else:
        messages.error(request, "Failed to accept invitation.")
        return redirect('chatkit:index')


@login_required
@require_POST
def deactivate_invitation(request: HttpRequest, invitation_id: int) -> HttpResponse:
    """Deactivate an invitation link"""
    invitation = get_object_or_404(
        InvitationLink,
        id=invitation_id,
        created_by=request.user
    )
    
    invitation.is_active = False
    invitation.save()
    messages.success(request, "Invitation link deactivated.")
    
    return redirect('chatkit:friends')

