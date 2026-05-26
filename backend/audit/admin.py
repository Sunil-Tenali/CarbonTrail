from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("id", "tenant", "action", "entity_type", "entity_id", "created_at")
    list_filter = ("action", "entity_type")