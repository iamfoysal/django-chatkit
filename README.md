
# django-chatkit

A plug-and-play Django app that provides real-time chat (via Channels), multi-file attachments,
Telegram/WhatsApp-inspired UI with light/dark mode, and simple per-user settings.

## Features
- Real-time message streaming (WebSocket) using Django Channels
- Send text plus multiple file attachments per message
- Room-based chats (1:1 or group)
- Clean, responsive UI; light/dark theme toggle and user preference storage
- Drop-in Django app with URLs, templates, static assets
- Minimal dependencies

## Quickstart (dev)

1) Install:
```bash
pip install -e .
```

2) Add to `INSTALLED_APPS`:
```python
INSTALLED_APPS = [
    ...,
    "django.contrib.staticfiles",
    "channels",
    "chatkit",
]
```

3) Channels / ASGI (project `asgi.py`):
```python
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import chatkit.routing

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "yourproject.settings")

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(chatkit.routing.websocket_urlpatterns)
    ),
})
```

4) Channels layer (settings.py). For dev you can leave default in-memory layer.
For production, use Redis:
```python
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [("127.0.0.1", 6379)]},
    }
}
```

5) URLs (project `urls.py`):
```python
from django.urls import path, include

urlpatterns = [
    path("chat/", include("chatkit.urls", namespace="chatkit")),
]
```

6) Media (for attachments) in `settings.py`:
```python
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
```

7) Templates: ensure app templates are discovered:
```python
TEMPLATES = [{
  "BACKEND": "django.template.backends.django.DjangoTemplates",
  "DIRS": [],
  "APP_DIRS": True,
  "OPTIONS": {"context_processors": [
      "django.template.context_processors.debug",
      "django.template.context_processors.request",
      "django.contrib.auth.context_processors.auth",
      "django.contrib.messages.context_processors.messages",
  ]},
}]
```

8) Run migrations:
```bash
python manage.py migrate
```

9) Create a superuser (optional):
```bash
python manage.py createsuperuser
```

10) Start dev server (with daphne or runserver):
```bash
python manage.py runserver
# or
daphne yourproject.asgi:application
```

11) Open: `http://localhost:8000/chat/`

## Notes
- This package is intentionally minimal but production-ready with Channels.
- For group chats, add multiple users to a room via the admin.
- The HTTP endpoint is used to submit messages + files. WebSocket broadcasts updates to connected clients in that room.

## License
MIT
