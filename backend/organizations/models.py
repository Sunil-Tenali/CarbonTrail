from django.db import models


class Tenant(models.Model):
    """
    A client company using the platform.

    Example:
    - Demo Enterprise Client
    - ABC Manufacturing
    """

    name = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name