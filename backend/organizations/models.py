"""
Organizations app - Multi-tenancy architecture for CarbonTrail.

This module implements the foundational multi-tenant SaaS model where each
organization (Tenant) has completely isolated data. All other models throughout
the backend reference Tenant via ForeignKey to enforce data isolation.

Multi-tenancy benefits:
- Data isolation: Organization A cannot access Organization B's data
- Scalability: One database instance serves multiple organizations
- Compliance: Each organization's data is completely separate
"""

from django.db import models


class Tenant(models.Model):
    """
    Represents a single client organization in the CarbonTrail platform.

    In a multi-tenant SaaS system, each Tenant is a completely isolated
    customer with their own emissions data, users, and configurations.

    This model is the root for multi-tenancy - every other model has a
    ForeignKey to Tenant to enforce data isolation:
    - ActivityRecord.tenant
    - RawActivityRow.tenant
    - ImportBatch.tenant
    - AuditLog.tenant

    Delete cascades to all related data, so be careful in production.

    Example organizations:
    - Acme Manufacturing Corp
    - Green Industries Ltd
    - Carbon-Neutral Tech Inc
    """

    # Unique constraint ensures no duplicate organization names
    name = models.CharField(max_length=255, unique=True)
    # Track when tenant account was created
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name