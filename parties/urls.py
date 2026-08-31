from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CustomerViewSet, SupplierViewSet

router = DefaultRouter()
router.register("customers", CustomerViewSet, basename="customers")
router.register("suppliers", SupplierViewSet, basename="suppliers")

urlpatterns = [path("", include(router.urls))]
