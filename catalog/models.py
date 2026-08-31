from django.conf import settings
from django.db import models

from accounts.models import Organisation


class OrganisationOwned(models.Model):
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE)

    class Meta:
        abstract = True


class Category(OrganisationOwned):
    name = models.CharField("Nom", max_length=120)
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
    )
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name_plural = "categories"
        unique_together = ("organisation", "parent", "name")

    def __str__(self):
        return self.name


class Unit(OrganisationOwned):
    name = models.CharField("Nom", max_length=60)
    symbol = models.CharField("Symbole", max_length=12)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        unique_together = ("organisation", "name")

    def __str__(self):
        return self.symbol


class TaxRate(OrganisationOwned):
    name = models.CharField("Nom", max_length=60)
    rate = models.DecimalField("Taux %", max_digits=5, decimal_places=2)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["rate"]

    def __str__(self):
        return f"{self.name} ({self.rate}%)"


class PaymentMethod(OrganisationOwned):
    name = models.CharField("Nom", max_length=80)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Article(OrganisationOwned):
    sku = models.CharField("Référence", max_length=60)
    barcode = models.CharField("Code-barres", max_length=64, blank=True)
    name = models.CharField("Désignation", max_length=200)
    brand = models.CharField("Marque", max_length=80, blank=True)
    description = models.TextField("Description", blank=True)
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="articles"
    )
    unit = models.ForeignKey(
        Unit, on_delete=models.SET_NULL, null=True, blank=True, related_name="articles"
    )
    tax = models.ForeignKey(
        TaxRate, on_delete=models.SET_NULL, null=True, blank=True, related_name="articles"
    )
    purchase_price = models.DecimalField("Prix d'achat", max_digits=12, decimal_places=2, default=0)
    sale_price = models.DecimalField("Prix de vente", max_digits=12, decimal_places=2, default=0)
    min_stock = models.DecimalField("Seuil d'alerte", max_digits=12, decimal_places=3, default=0)
    location = models.CharField("Emplacement", max_length=80, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        ordering = ["name"]
        unique_together = ("organisation", "sku")

    def __str__(self):
        return f"{self.sku} — {self.name}"
