"""
Organizations app - Multi-tenant data isolation.

Every model throughout the backend references Tenant via ForeignKey to ensure
that Organization A cannot access Organization B's data.
"""

from django.db import models


class Tenant(models.Model):
    """
    A client organization in the CarbonTrail platform.

    Each Tenant is completely isolated: their emissions data, users, and
    configurations are separate. The multi-tenant design enables one database
    instance to serve multiple customers.
    """

    name = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name