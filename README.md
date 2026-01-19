
# Django ChatKit

[![Django](https://img.shields.io/badge/Django-3.2%2B-green.svg)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-BSD%203--Clause-blue.svg)](LICENSE)
[![Channels](https://img.shields.io/badge/Django%20Channels-4.0%2B-orange.svg)](https://channels.readthedocs.io/)

A production-ready, plug-and-play Django application that provides real-time chat functionality with WebSocket support, multi-file attachments, and a modern Telegram/WhatsApp-inspired user interface.

## Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Production Deployment](#production-deployment)
- [Advanced Features](#advanced-features)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## Overview

Django ChatKit is a comprehensive real-time messaging solution built on Django Channels. It seamlessly integrates into your existing Django project, providing a complete chat system with minimal configuration. The application features a responsive, modern UI with light/dark theme support and handles both individual and group conversations.

## Features

### Core Functionality
- **Real-time Messaging**: WebSocket-based message streaming using Django Channels
- **Multi-file Attachments**: Send multiple files alongside text messages
- **Room-based Architecture**: Support for both 1:1 and group conversations
- **Message Status**: Read receipts and message seen indicators

### User Experience
- **Modern UI**: Clean, responsive interface inspired by popular messaging apps
- **Theme Support**: Light/dark mode with persistent user preferences
- **User Settings**: Customizable per-user configuration
- **Responsive Design**: Optimized for desktop and mobile devices

### Technical Features
- **Drop-in Integration**: Minimal setup required
- **Production Ready**: Designed for deployment with Redis backend
- **Minimal Dependencies**: Lightweight and efficient
- **Django Admin Integration**: Manage rooms and messages through admin interface

## Requirements

- Python 3.8 or higher
- Django 3.2 or higher
- Django Channels 4.0 or higher
- Redis (for production deployment)
- PostgreSQL, MySQL, or SQLite (database)

## Installation

### Step 1: Install the Package

Install django-chatkit using pip:

```bash
pip install django-chatkit
```

### Step 2: Configure Django Settings

Add the required applications to your `INSTALLED_APPS` in `settings.py`:

```python
INSTALLED_APPS = [
    # ... your other apps
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "channels",
    "chatkit",
]
```

## Configuration

### Step 3: Configure ASGI Application

Update your project's `asgi.py` file to include WebSocket routing:
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

### Step 4: Configure Channel Layers

Add channel layer configuration to your `settings.py`.

**For Development** (in-memory, default):
```python
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer"
    }
}
```

**For Production** (Redis recommended):

```python
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [("127.0.0.1", 6379)]},
    }
}
```

**Note**: For production Redis setup, install `channels-redis`:
```bash
pip install channels-redis
```

### Step 5: Configure URL Routing

Include ChatKit URLs in your project's `urls.py`:
```python
from django.urls import path, include

urlpatterns = [
    path("chat/", include("chatkit.urls", namespace="chatkit")),
]
```

### Step 6: Configure Static and Media Files

Configure static and media file settings in `settings.py` for handling file attachments:

```python
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / "staticfiles"

# Additional locations of static files
STATICFILES_DIRS = []

# WhiteNoise configuration for serving static files with ASGI/Daphne
WHITENOISE_USE_FINDERS = True
WHITENOISE_AUTOREFRESH = True  # Auto-refresh in development
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
```

**Update Middleware** for WhiteNoise:

```python
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    # ... other middleware
]
```

**Install WhiteNoise** (if not already installed):
```bash
pip install whitenoise
```

For more information on WhiteNoise configuration, refer to the [official documentation](https://whitenoise.evans.io/en/stable/django.html).

### Step 7: Configure Template Settings

Ensure template discovery is properly configured in `settings.py`:

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

### Step 8: Initialize Database

Run migrations to create the necessary database tables:

```bash
python manage.py migrate
```

### Step 9: Create Administrative User (Optional)

Create a superuser to access the Django admin interface:

```bash
python manage.py createsuperuser
```

### Step 10: Collect Static Files

Collect all static files for production:

```bash
python manage.py collectstatic --noinput
```

## Usage

### Starting the Development Server

You can run the application using Django's development server or Daphne:

**Using Django's runserver:**
```bash
python manage.py runserver
```

**Using Daphne (recommended for WebSocket support):**
```bash
pip install daphne
daphne yourproject.asgi:application
```

### Accessing the Application

Once the server is running, navigate to:
```
http://localhost:8000/chat/
```

### Creating Chat Rooms

1. Log in to the Django admin interface: `http://localhost:8000/admin/`
2. Navigate to the ChatKit section
3. Create rooms and add participants
4. Users can now access their conversations through the chat interface

## Production Deployment

### Recommended Configuration

1. **Use Redis** for channel layers (as shown in Step 4)
2. **Use Daphne or Uvicorn** as ASGI server
3. **Configure HTTPS** for secure WebSocket connections (wss://)
4. **Set DEBUG = False** in production settings
5. **Use a production database** (PostgreSQL or MySQL recommended)
6. **Configure ALLOWED_HOSTS** appropriately

### Example Production Stack

- **Web Server**: Nginx
- **ASGI Server**: Daphne or Uvicorn
- **Channel Layer**: Redis
- **Database**: PostgreSQL
- **Static Files**: WhiteNoise or CDN

## Advanced Features

### Friend Requests and Invitations

The application includes a friend system where users can:
- Send and receive friend requests
- Generate and share invitation links
- Manage their friend list

### Message Attachments

Users can attach multiple files to messages. Supported file types and size limits can be configured in your Django settings.

### Theme Customization

Users can toggle between light and dark modes. Theme preferences are stored per-user and persist across sessions.

## Troubleshooting

### WebSocket Connection Issues

- Ensure your ASGI server (Daphne/Uvicorn) is running
- Check that channel layers are properly configured
- Verify Redis is running if using Redis backend
- Check browser console for WebSocket errors

### Static Files Not Loading

- Run `python manage.py collectstatic`
- Verify `STATIC_URL` and `STATIC_ROOT` settings
- Check that WhiteNoise is properly configured

### Messages Not Appearing in Real-time

- Verify WebSocket connection is established
- Check Redis connection if using Redis backend
- Review channel layer configuration

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

## Support

For issues, questions, or contributions, please visit the [GitHub repository](https://github.com/iamfoysal/django-chatkit).

## License

This project is licensed under the BSD 3-Clause License. See the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with [Django](https://www.djangoproject.com/)
- Real-time functionality powered by [Django Channels](https://channels.readthedocs.io/)
- UI inspired by modern messaging applications

---


