from django.urls import path

from .views import (
    CSVUploadView,
    ImportBatchListView,
    SourceSystemListView,
)


urlpatterns = [
    path(
        "source-systems/",
        SourceSystemListView.as_view(),
        name="source-system-list",
    ),
    path(
        "import-batches/",
        ImportBatchListView.as_view(),
        name="import-batch-list",
    ),
    path(
        "ingestion/upload/",
        CSVUploadView.as_view(),
        name="csv-upload",
    ),
]