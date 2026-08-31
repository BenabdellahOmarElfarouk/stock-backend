from django.contrib.auth import get_user_model
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from .mixins import OrganisationScopedMixin
from .models import Organisation, Store
from .permissions import IsOrgAdmin, IsPlatformAdmin
from .serializers import (
    LoginSerializer,
    MeSerializer,
    OrganisationSerializer,
    PlatformOrganisationSerializer,
    RegisterSerializer,
    StoreSerializer,
    UserCreateSerializer,
    UserSerializer,
)

User = get_user_model()


def tokens_for(user):
    refresh = RefreshToken.for_user(user)
    return {"refresh": str(refresh), "access": str(refresh.access_token)}


class RegisterView(generics.CreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {
                "user": MeSerializer(user).data,
                **tokens_for(user),
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        return Response({"user": MeSerializer(user).data, **tokens_for(user)})


class PlatformOrganisationViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsPlatformAdmin]
    serializer_class = PlatformOrganisationSerializer
    queryset = Organisation.objects.all().prefetch_related("users")
    search_fields = ("name", "trade_name", "city")

    def create(self, request, *args, **kwargs):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            PlatformOrganisationSerializer(user.organisation).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def toggle(self, request, pk=None):
        org = self.get_object()
        org.is_active = not org.is_active
        org.save(update_fields=["is_active"])
        return Response(self.get_serializer(org).data)


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = MeSerializer

    def get_object(self):
        return self.request.user


class OrganisationView(generics.RetrieveUpdateAPIView):
    serializer_class = OrganisationSerializer
    permission_classes = [IsAuthenticated, IsOrgAdmin]

    def get_object(self):
        return self.request.user.organisation


class StoreViewSet(OrganisationScopedMixin, viewsets.ModelViewSet):
    queryset = Store.objects.all()
    serializer_class = StoreSerializer
    search_fields = ("name",)
    permission_classes = [IsAuthenticated]


class UserViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsOrgAdmin]
    search_fields = ("username", "first_name", "last_name", "email")

    def get_queryset(self):
        org = self.request.user.organisation
        if org is None:
            return User.objects.none()
        return User.objects.filter(organisation=org).select_related("store").order_by("username")

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return UserCreateSerializer
        return UserSerializer

    @action(detail=True, methods=["post"])
    def reset_password(self, request, pk=None):
        user = self.get_object()
        password = request.data.get("password")
        if not password or len(password) < 6:
            return Response(
                {"password": "Minimum 6 caractères."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.set_password(password)
        user.save()
        return Response({"ok": True})
