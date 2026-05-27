"""
WSGI entry point for production web servers (Gunicorn, uWSGI).

Entry point: application
Usage: gunicorn config.wsgi:application --bind 0.0.0.0:8000
"""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
application = get_wsgi_application()
