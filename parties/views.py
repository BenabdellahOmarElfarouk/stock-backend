from decimal import Decimal

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.mixins import OrganisationScopedMixin
from invoicing.models import Invoice

from .models import Customer, Supplier
from .serializers import CustomerSerializer, SupplierSerializer


def apply_party_payment(party, kind, amount, user, method="Espèces", notes=""):
    remaining = Decimal(amount)
    if remaining <= 0:
        raise ValueError("Le montant doit être positif.")
    invoices = party.invoices.filter(kind=kind, status__in=["confirmed", "partial"]).order_by(
        "date", "id"
    )
    applied = []
    for invoice in invoices:
        if remaining <= 0:
            break
        due = invoice.amount_due
        if due <= 0:
            continue
        take = due if remaining > due else remaining
        invoice.add_payment(take, user=user, method=method, notes=notes)
        applied.append({"invoice": invoice.number, "amount": take})
        remaining -= take
    return applied, remaining


class CustomerViewSet(OrganisationScopedMixin, viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    search_fields = ("name", "phone", "nif", "city")
    filterset_fields = ("is_active", "city")

    @action(detail=True, methods=["post"])
    def pay(self, request, pk=None):
        customer = self.get_object()
        try:
            applied, leftover = apply_party_payment(
                customer,
                Invoice.Kind.SALE,
                request.data.get("amount"),
                request.user,
                request.data.get("method") or "Espèces",
                request.data.get("notes") or "Règlement client",
            )
        except (ValueError, TypeError, Exception) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {
                "applied": applied,
                "leftover": leftover,
                "customer": self.get_serializer(customer).data,
            }
        )


class SupplierViewSet(OrganisationScopedMixin, viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    search_fields = ("name", "phone", "contact_name", "nif")
    filterset_fields = ("is_active",)

    @action(detail=True, methods=["post"])
    def pay(self, request, pk=None):
        supplier = self.get_object()
        try:
            applied, leftover = apply_party_payment(
                supplier,
                Invoice.Kind.PURCHASE,
                request.data.get("amount"),
                request.user,
                request.data.get("method") or "Espèces",
                request.data.get("notes") or "Règlement fournisseur",
            )
        except (ValueError, TypeError, Exception) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {
                "applied": applied,
                "leftover": leftover,
                "supplier": self.get_serializer(supplier).data,
            }
        )
