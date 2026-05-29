"""
URL configuration for CarbonTrail backend.

Root URL patterns map HTTP requests to app-specific URL configurations.
Django processes patterns in order, matching URL prefixes to included apps.
"""

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # API endpoints under /api/ prefix
    path("api/", include("organizations.urls")),
    path("api/", include("activities.urls")),      # Activity records: list, retrieve, approve, reject
    path("api/", include("ingestion.urls")),       # Data ingestion: upload, batch tracking
    path("api/", include("audit.urls")),           # Audit trail: list, retrieve
]
