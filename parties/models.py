from django.db import models

from accounts.models import Organisation


class Party(models.Model):
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE)
    name = models.CharField("Nom", max_length=180)
    phone = models.CharField("Téléphone", max_length=40, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField("Adresse", blank=True)
    city = models.CharField("Ville", max_length=80, blank=True)
    rc = models.CharField("RC", max_length=60, blank=True)
    nif = models.CharField("NIF", max_length=60, blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True
        ordering = ["name"]

    def __str__(self):
        return self.name


class Customer(Party):
    organisation = models.ForeignKey(
        Organisation, on_delete=models.CASCADE, related_name="customers"
    )

    class Meta(Party.Meta):
        verbose_name = "Client"


class Supplier(Party):
    organisation = models.ForeignKey(
        Organisation, on_delete=models.CASCADE, related_name="suppliers"
    )
    contact_name = models.CharField("Contact", max_length=120, blank=True)

    class Meta(Party.Meta):
        verbose_name = "Fournisseur"
