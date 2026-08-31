from django.contrib.auth.models import AbstractUser
from django.db import models


class Organisation(models.Model):
    name = models.CharField("Raison sociale", max_length=180)
    trade_name = models.CharField("Enseigne", max_length=180, blank=True)
    phone = models.CharField("Téléphone", max_length=40, blank=True)
    email = models.EmailField("Email", blank=True)
    address = models.TextField("Adresse", blank=True)
    city = models.CharField("Ville", max_length=80, blank=True)
    rc = models.CharField("Registre de commerce", max_length=60, blank=True)
    nif = models.CharField("NIF", max_length=60, blank=True)
    nis = models.CharField("NIS", max_length=60, blank=True)
    ai = models.CharField("Article d'imposition", max_length=60, blank=True)
    invoice_prefix = models.CharField("Préfixe facture", max_length=10, default="FAC")
    invoice_counter = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField("Accès actif", default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Store(models.Model):
    organisation = models.ForeignKey(
        Organisation, on_delete=models.CASCADE, related_name="stores"
    )
    name = models.CharField("Magasin", max_length=120)
    address = models.CharField("Adresse", max_length=255, blank=True)
    phone = models.CharField("Téléphone", max_length=40, blank=True)
    is_default = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", "Administrateur"
        MANAGER = "manager", "Gérant"
        CASHIER = "cashier", "Vendeur"

    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.CASCADE,
        related_name="users",
        null=True,
        blank=True,
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.ADMIN)
    phone = models.CharField("Téléphone", max_length=40, blank=True)
    store = models.ForeignKey(
        Store, on_delete=models.SET_NULL, null=True, blank=True, related_name="users"
    )
    is_platform_admin = models.BooleanField(
        "Admin plateforme",
        default=False,
        help_text="Éditeur de l'application : crée et active les entreprises clientes.",
    )

    def is_org_admin(self):
        return self.role == self.Role.ADMIN
