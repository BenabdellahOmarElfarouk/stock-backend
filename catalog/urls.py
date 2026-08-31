from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ArticleViewSet,
    CategoryViewSet,
    PaymentMethodViewSet,
    TaxRateViewSet,
    UnitViewSet,
)

router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="categories")
router.register("units", UnitViewSet, basename="units")
router.register("taxes", TaxRateViewSet, basename="taxes")
router.register("payment-methods", PaymentMethodViewSet, basename="payment-methods")
router.register("articles", ArticleViewSet, basename="articles")

urlpatterns = [path("", include(router.urls))]
