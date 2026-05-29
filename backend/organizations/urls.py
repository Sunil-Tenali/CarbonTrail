from django.urls import path

from .views import TenantListCreateView


urlpatterns = [
    path("tenants/", TenantListCreateView.as_view(), name="tenant-list-create"),
]