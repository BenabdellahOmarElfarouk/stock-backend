from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    LoginView,
    MeView,
    OrganisationView,
    PlatformOrganisationViewSet,
    RegisterView,
    StoreViewSet,
    UserViewSet,
)

router = DefaultRouter()
router.register("users", UserViewSet, basename="users")
router.register("stores", StoreViewSet, basename="stores")
router.register("platform/organisations", PlatformOrganisationViewSet, basename="platform-orgs")

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("me/", MeView.as_view(), name="me"),
    path("organisation/", OrganisationView.as_view(), name="organisation"),
    path("", include(router.urls)),
]
