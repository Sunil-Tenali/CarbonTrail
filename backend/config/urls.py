"""
URL configuration for CarbonTrail backend.

This is the ROOT URL configuration - all API routes are defined here.
Django processes requests by matching URL patterns in order.

URL ROUTING FLOW:
1. Request comes in: GET /api/activity-records/?tenant_id=1
2. Django matches 'api/' prefix and includes activities.urls
3. activities.urls router handles 'activity-records/'
4. ActivityRecordViewSet.list() method is called

HIERARCHY:
config/urls.py (this file)
    └── activities/urls.py (includes router with all activity endpoints)

MAIN ENDPOINTS:
- /admin/                  - Django admin interface (staff only)
- /api/activity-records/   - List, retrieve, approve, reject emissions data
"""

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # Django admin interface: /admin/
    # Allows staff to manage organizations, view audit logs, etc.
    # SECURITY: Restrict access in production (use allowlist of staff IPs)
    path('admin/', admin.site.urls),
    
    # API routes: All REST endpoints are under /api/ prefix
    # Includes the activities app router with all endpoints
    path("api/", include("activities.urls")),
]
