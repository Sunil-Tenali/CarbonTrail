from django.urls import path

from .views import (
    ImportBatchListView,
    SAPCSVUploadView,
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
        "ingestion/sap/upload/",
        SAPCSVUploadView.as_view(),
        name="sap-csv-upload",
    ),
]