from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .sync_views import SyncPullView, SyncPushView
from .views import DashboardViewSet, InvoiceViewSet

router = DefaultRouter()
router.register("invoices", InvoiceViewSet, basename="invoices")
router.register("dashboard", DashboardViewSet, basename="dashboard")

urlpatterns = [
    path("sync/pull/", SyncPullView.as_view(), name="sync-pull"),
    path("sync/push/", SyncPushView.as_view(), name="sync-push"),
    path("", include(router.urls)),
]
