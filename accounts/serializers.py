from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers

from .models import Organisation, Store

User = get_user_model()


class OrganisationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organisation
        fields = (
            "id",
            "name",
            "trade_name",
            "phone",
            "email",
            "address",
            "city",
            "rc",
            "nif",
            "nis",
            "ai",
            "invoice_prefix",
            "locale",
            "is_active",
            "created_at",
        )
        read_only_fields = ("created_at", "is_active")


class StoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Store
        fields = ("id", "name", "address", "phone", "is_default")
        read_only_fields = ("id",)


class UserSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source="store.name", read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "phone",
            "role",
            "store",
            "store_name",
            "is_active",
            "date_joined",
        )
        read_only_fields = ("id", "date_joined")


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "password",
            "first_name",
            "last_name",
            "email",
            "phone",
            "role",
            "store",
            "is_active",
        )

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.organisation = self.context["request"].user.organisation
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for key, value in validated_data.items():
            setattr(instance, key, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class RegisterSerializer(serializers.Serializer):
    organisation_name = serializers.CharField(max_length=180)
    trade_name = serializers.CharField(max_length=180, required=False, allow_blank=True)
    city = serializers.CharField(max_length=80, required=False, allow_blank=True)
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, min_length=6)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    phone = serializers.CharField(max_length=40, required=False, allow_blank=True)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Ce nom d'utilisateur existe déjà.")
        return value

    @transaction.atomic
    def create(self, validated_data):
        org = Organisation.objects.create(
            name=validated_data["organisation_name"],
            trade_name=validated_data.get("trade_name", ""),
            city=validated_data.get("city", ""),
            email=validated_data.get("email", ""),
            phone=validated_data.get("phone", ""),
        )
        store = Store.objects.create(
            organisation=org,
            name=validated_data.get("trade_name") or "Magasin principal",
            is_default=True,
        )
        user = User.objects.create(
            username=validated_data["username"],
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
            email=validated_data.get("email", ""),
            phone=validated_data.get("phone", ""),
            organisation=org,
            store=store,
            role=User.Role.ADMIN,
        )
        user.set_password(validated_data["password"])
        user.save()
        self._seed_defaults(org)
        return user

    def _seed_defaults(self, org):
        from catalog.models import Category, PaymentMethod, TaxRate, Unit

        units = [
            ("Pièce", "pce"),
            ("Boîte", "bte"),
            ("Paquet", "paq"),
            ("Mètre", "m"),
            ("Kilogramme", "kg"),
            ("Litre", "L"),
            ("Sac", "sac"),
            ("Rouleau", "rlx"),
        ]
        for name, symbol in units:
            Unit.objects.create(organisation=org, name=name, symbol=symbol)

        for name, rate in (("TVA 19%", 19), ("TVA 9%", 9), ("Exonéré", 0)):
            TaxRate.objects.create(organisation=org, name=name, rate=rate)

        for method in ("Espèces", "Virement", "Chèque"):
            PaymentMethod.objects.create(organisation=org, name=method)

        tree = {
            "Quincaillerie": ["Vis & boulons", "Chevilles", "Ferrures", "Chaînes & câbles"],
            "Outillage": ["Outils à main", "Outils électriques", "Mesure"],
            "Plomberie": ["Tubes & raccords", "Robinets", "Évacuation"],
            "Électricité": ["Câbles", "Interrupteurs", "Éclairage"],
            "Peinture": ["Peintures", "Rouleaux & pinceaux", "Enduits"],
            "Serrurerie": ["Serrures", "Cadenas", "Cylindres"],
            "Jardin & extérieur": ["Arrosage", "Clôture"],
        }
        for parent_name, children in tree.items():
            parent = Category.objects.create(organisation=org, name=parent_name)
            for child in children:
                Category.objects.create(organisation=org, name=child, parent=parent)


class MeSerializer(serializers.ModelSerializer):
    organisation = OrganisationSerializer(read_only=True)
    store_name = serializers.CharField(source="store.name", read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "phone",
            "role",
            "store",
            "store_name",
            "organisation",
            "is_platform_admin",
        )
        read_only_fields = ("is_platform_admin",)


class PlatformOrganisationSerializer(serializers.ModelSerializer):
    users_count = serializers.IntegerField(source="users.count", read_only=True)
    owner_username = serializers.SerializerMethodField()

    class Meta:
        model = Organisation
        fields = (
            "id",
            "name",
            "trade_name",
            "city",
            "phone",
            "email",
            "is_active",
            "users_count",
            "owner_username",
            "created_at",
        )

    def get_owner_username(self, obj):
        owner = obj.users.filter(role=User.Role.ADMIN).order_by("id").first()
        return owner.username if owner else None


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()

    def validate(self, attrs):
        from django.contrib.auth import authenticate

        user = authenticate(
            username=attrs["username"], password=attrs["password"]
        )
        if not user:
            raise serializers.ValidationError("Identifiants incorrects.")
        if not user.is_active:
            raise serializers.ValidationError("Ce compte est désactivé.")
        if user.organisation_id and not user.organisation.is_active:
            raise serializers.ValidationError(
                "L'accès de cette entreprise est suspendu. Contactez l'éditeur."
            )
        attrs["user"] = user
        return attrs
