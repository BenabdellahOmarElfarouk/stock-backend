from decimal import Decimal

from django.conf import settings
from django.db import models, transaction

from accounts.models import Organisation, Store
from catalog.models import Article
from inventory.models import StockMovement
from inventory.services import apply_stock_change
from parties.models import Customer, Supplier


class Invoice(models.Model):
    class Kind(models.TextChoices):
        SALE = "sale", "Vente"
        PURCHASE = "purchase", "Achat"

    class Status(models.TextChoices):
        DRAFT = "draft", "Brouillon"
        CONFIRMED = "confirmed", "Validée"
        PARTIAL = "partial", "Acompte"
        PAID = "paid", "Payée"
        CANCELLED = "cancelled", "Annulée"

    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name="invoices")
    store = models.ForeignKey(Store, on_delete=models.PROTECT, related_name="invoices")
    number = models.CharField("N°", max_length=40, blank=True)
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.SALE)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    customer = models.ForeignKey(
        Customer, on_delete=models.SET_NULL, null=True, blank=True, related_name="invoices"
    )
    supplier = models.ForeignKey(
        Supplier, on_delete=models.SET_NULL, null=True, blank=True, related_name="invoices"
    )
    date = models.DateField()
    notes = models.TextField(blank=True)
    total_ht = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_tax = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_ttc = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    client_uuid = models.CharField(
        "Identifiant hors-ligne",
        max_length=64,
        blank=True,
        db_index=True,
        help_text="UUID généré sur la caisse pour éviter les doublons à la synchro.",
    )

    class Meta:
        ordering = ["-date", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["organisation", "number"],
                condition=~models.Q(number=""),
                name="uniq_org_invoice_number",
            ),
            models.UniqueConstraint(
                fields=["organisation", "client_uuid"],
                condition=~models.Q(client_uuid=""),
                name="uniq_org_invoice_client_uuid",
            ),
        ]

    def __str__(self):
        return self.number or f"Brouillon #{self.pk}"

    def recalc(self):
        ht = Decimal("0")
        tax = Decimal("0")
        for line in self.lines.all():
            ht += line.line_ht
            tax += line.line_tax
        self.total_ht = ht
        self.total_tax = tax
        self.total_ttc = ht + tax
        self.save(update_fields=["total_ht", "total_tax", "total_ttc"])

    def assign_number(self):
        if self.number:
            return
        org = Organisation.objects.select_for_update().get(pk=self.organisation_id)
        org.invoice_counter += 1
        org.save(update_fields=["invoice_counter"])
        year = self.date.year
        self.number = f"{org.invoice_prefix}-{year}-{org.invoice_counter:04d}"
        self.save(update_fields=["number"])

    @transaction.atomic
    def confirm(self, user=None):
        if self.status not in (self.Status.DRAFT,):
            raise ValueError("Seule une facture brouillon peut être validée.")
        if not self.lines.exists():
            raise ValueError("Ajoutez au moins une ligne.")
        self.assign_number()
        kind = (
            StockMovement.Kind.OUT
            if self.kind == self.Kind.SALE
            else StockMovement.Kind.IN
        )
        for line in self.lines.select_related("article"):
            apply_stock_change(
                organisation=self.organisation,
                article=line.article,
                store=self.store,
                kind=kind,
                quantity=line.quantity,
                user=user,
                reason=f"Facture {self.number}",
                reference=self.number,
            )
        from django.utils import timezone

        self.status = self.Status.CONFIRMED
        self.confirmed_at = timezone.now()
        self.save(update_fields=["status", "confirmed_at"])
        return self

    @property
    def amount_paid(self):
        paid = self.payments.aggregate(s=models.Sum("amount"))["s"] or Decimal("0")
        if paid == 0 and self.status == self.Status.PAID:
            return self.total_ttc
        return paid

    @property
    def amount_due(self):
        if self.status in (self.Status.DRAFT, self.Status.CANCELLED):
            return Decimal("0") if self.status == self.Status.CANCELLED else self.total_ttc
        due = self.total_ttc - self.amount_paid
        return due if due > 0 else Decimal("0")

    def refresh_payment_status(self):
        if self.status in (self.Status.DRAFT, self.Status.CANCELLED):
            return
        if self.amount_due <= 0:
            self.status = self.Status.PAID
        elif self.amount_paid > 0:
            self.status = self.Status.PARTIAL
        else:
            self.status = self.Status.CONFIRMED
        self.save(update_fields=["status"])

    def add_payment(self, amount, user=None, method="Espèces", notes="", date=None):
        from django.utils import timezone as tz

        amount = Decimal(amount)
        if amount <= 0:
            raise ValueError("Le montant doit être positif.")
        if self.status == self.Status.DRAFT:
            raise ValueError("Validez d'abord la facture.")
        if self.status == self.Status.CANCELLED:
            raise ValueError("Facture annulée.")
        due = self.amount_due
        if amount > due:
            amount = due
        if amount <= 0:
            raise ValueError("Cette facture est déjà soldée.")
        payment = Payment.objects.create(
            organisation=self.organisation,
            invoice=self,
            amount=amount,
            method=method or "Espèces",
            notes=notes,
            date=date or tz.localdate(),
            created_by=user,
        )
        self.refresh_payment_status()
        return payment


class Payment(models.Model):
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name="payments")
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    method = models.CharField("Mode", max_length=80, default="Espèces")
    date = models.DateField()
    notes = models.CharField(max_length=200, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-id"]


class InvoiceLine(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="lines")
    article = models.ForeignKey(Article, on_delete=models.PROTECT)
    designation = models.CharField(max_length=200)
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    class Meta:
        ordering = ["id"]

    @property
    def line_ht(self):
        return (self.quantity * self.unit_price).quantize(Decimal("0.01"))

    @property
    def line_tax(self):
        return (self.line_ht * self.tax_rate / Decimal("100")).quantize(Decimal("0.01"))

    @property
    def line_ttc(self):
        return self.line_ht + self.line_tax
