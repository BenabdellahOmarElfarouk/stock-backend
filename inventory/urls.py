from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import StockMovementViewSet, StockViewSet

router = DefaultRouter()
router.register("stock", StockViewSet, basename="stock")
router.register("movements", StockMovementViewSet, basename="movements")

urlpatterns = [path("", include(router.urls))]
