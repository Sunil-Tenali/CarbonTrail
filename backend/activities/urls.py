from django.urls import include, path

from rest_framework.routers import DefaultRouter

from .views import ActivityRecordViewSet


router = DefaultRouter()
router.register(
    "activity-records",
    ActivityRecordViewSet,
    basename="activity-record",
)

urlpatterns = [
    path("", include(router.urls)),
]