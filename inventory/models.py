from django.conf import settings
from django.db import models

from accounts.models import Organisation, Store
from catalog.models import Article


class Stock(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name="stocks")
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="stocks")
    quantity = models.DecimalField(max_digits=14, decimal_places=3, default=0)

    class Meta:
        unique_together = ("article", "store")

    def __str__(self):
        return f"{self.article} @ {self.store}: {self.quantity}"


class StockMovement(models.Model):
    class Kind(models.TextChoices):
        IN = "in", "Entrée"
        OUT = "out", "Sortie"
        ADJUST = "adjust", "Ajustement"
        TRANSFER = "transfer", "Transfert"

    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE)
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name="movements")
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="movements")
    kind = models.CharField(max_length=20, choices=Kind.choices)
    quantity = models.DecimalField(max_digits=14, decimal_places=3)
    reason = models.CharField("Motif", max_length=200, blank=True)
    reference = models.CharField("Référence", max_length=80, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
