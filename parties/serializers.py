from decimal import Decimal

from rest_framework import serializers

from invoicing.models import Invoice

from .models import Customer, Supplier


def party_balance(party, kind):
    due = Decimal("0")
    invoices = party.invoices.filter(kind=kind, status__in=["confirmed", "partial"])
    for inv in invoices:
        due += inv.amount_due
    return due


class CustomerSerializer(serializers.ModelSerializer):
    balance_due = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = (
            "id",
            "name",
            "phone",
            "email",
            "address",
            "city",
            "rc",
            "nif",
            "notes",
            "is_active",
            "balance_due",
            "created_at",
        )
        read_only_fields = ("id", "created_at", "balance_due")

    def get_balance_due(self, obj):
        return party_balance(obj, Invoice.Kind.SALE)


class SupplierSerializer(serializers.ModelSerializer):
    balance_due = serializers.SerializerMethodField()

    class Meta:
        model = Supplier
        fields = (
            "id",
            "name",
            "contact_name",
            "phone",
            "email",
            "address",
            "city",
            "rc",
            "nif",
            "notes",
            "is_active",
            "balance_due",
            "created_at",
        )
        read_only_fields = ("id", "created_at", "balance_due")

    def get_balance_due(self, obj):
        return party_balance(obj, Invoice.Kind.PURCHASE)
