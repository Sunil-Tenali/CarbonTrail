"""
Admin interface for organizations app.

Manage client organizations (tenants) in the Django admin. This interface
is used by CarbonTrail staff to:
- Create new customer accounts
- View tenant information
- Access organization-level management

RESTRICT ADMIN ACCESS in production to authorized staff only.
"""

from django.contrib import admin
from .models import Tenant


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    """
    Admin interface for managing Tenant organizations.

    Displays the organization list with key fields:
    - id: Database identifier
    - name: Organization name
    - created_at: When the account was created
    """
    list_display = ("id", "name", "created_at")