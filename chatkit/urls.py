
from django.urls import path
from . import views

app_name = "chatkit"

urlpatterns = [
    path("", views.index, name="index"),
    path("room/<slug:slug>/", views.room, name="room"),
    path("api/send/", views.api_send_message, name="api_send_message"),
    path("settings/", views.user_settings, name="user_settings"),
    
    # Friend system URLs
    path("friends/", views.friends_list, name="friends"),
    path("friends/request/send/", views.send_friend_request, name="send_friend_request"),
    path("friends/request/<int:request_id>/accept/", views.accept_friend_request, name="accept_friend_request"),
    path("friends/request/<int:request_id>/reject/", views.reject_friend_request, name="reject_friend_request"),
    path("friends/request/<int:request_id>/cancel/", views.cancel_friend_request, name="cancel_friend_request"),
    path("friends/<int:friendship_id>/remove/", views.remove_friend, name="remove_friend"),
    
    # Invitation link URLs
    path("invitation/create/", views.create_invitation_link, name="create_invitation"),
    path("invitation/<str:token>/accept/", views.accept_invitation, name="accept_invitation"),
    path("invitation/<int:invitation_id>/deactivate/", views.deactivate_invitation, name="deactivate_invitation"),
]

