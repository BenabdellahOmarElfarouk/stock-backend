from rest_framework import serializers

from .models import Invoice, InvoiceLine, Payment


class PaymentSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source="created_by.username", read_only=True)

    class Meta:
        model = Payment
        fields = (
            "id",
            "amount",
            "method",
            "date",
            "notes",
            "created_by",
            "created_by_name",
            "created_at",
        )
        read_only_fields = ("id", "created_by", "created_at")


class InvoiceLineSerializer(serializers.ModelSerializer):
    line_ht = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    line_tax = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    line_ttc = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    sku = serializers.CharField(source="article.sku", read_only=True)

    class Meta:
        model = InvoiceLine
        fields = (
            "id",
            "article",
            "sku",
            "designation",
            "quantity",
            "unit_price",
            "tax_rate",
            "line_ht",
            "line_tax",
            "line_ttc",
        )
        read_only_fields = ("id",)


class InvoiceSerializer(serializers.ModelSerializer):
    lines = InvoiceLineSerializer(many=True)
    payments = PaymentSerializer(many=True, read_only=True)
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)
    store_name = serializers.CharField(source="store.name", read_only=True)
    created_by_name = serializers.CharField(source="created_by.username", read_only=True)
    amount_paid = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    amount_due = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = Invoice
        fields = (
            "id",
            "number",
            "kind",
            "status",
            "store",
            "store_name",
            "customer",
            "customer_name",
            "supplier",
            "supplier_name",
            "date",
            "notes",
            "total_ht",
            "total_tax",
            "total_ttc",
            "amount_paid",
            "amount_due",
            "lines",
            "payments",
            "created_by",
            "created_by_name",
            "created_at",
            "confirmed_at",
            "client_uuid",
        )
        read_only_fields = (
            "id",
            "number",
            "status",
            "total_ht",
            "total_tax",
            "total_ttc",
            "amount_paid",
            "amount_due",
            "created_by",
            "created_at",
            "confirmed_at",
            "client_uuid",
        )

    def _save_lines(self, invoice, lines_data):
        invoice.lines.all().delete()
        org = invoice.organisation
        for item in lines_data:
            article = item["article"]
            if article.organisation_id != org.id:
                raise serializers.ValidationError("Article hors organisation.")
            default_price = (
                article.sale_price if invoice.kind == Invoice.Kind.SALE else article.purchase_price
            )
            InvoiceLine.objects.create(
                invoice=invoice,
                article=article,
                designation=item.get("designation") or article.name,
                quantity=item["quantity"],
                unit_price=item.get("unit_price", default_price),
                tax_rate=item.get("tax_rate")
                if item.get("tax_rate") is not None
                else (article.tax.rate if article.tax else 0),
            )
        invoice.recalc()

    def create(self, validated_data):
        lines = validated_data.pop("lines", [])
        invoice = Invoice.objects.create(**validated_data)
        self._save_lines(invoice, lines)
        return invoice

    def update(self, instance, validated_data):
        if instance.status != Invoice.Status.DRAFT:
            raise serializers.ValidationError("Impossible de modifier une facture validée.")
        lines = validated_data.pop("lines", None)
        for key, value in validated_data.items():
            setattr(instance, key, value)
        instance.save()
        if lines is not None:
            self._save_lines(instance, lines)
        return instance


class QuickSaleLineSerializer(serializers.Serializer):
    article = serializers.IntegerField()
    quantity = serializers.DecimalField(max_digits=12, decimal_places=3)
    unit_price = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)


class QuickSaleSerializer(serializers.Serializer):
    store = serializers.IntegerField(required=False)
    customer = serializers.IntegerField(required=False, allow_null=True)
    supplier = serializers.IntegerField(required=False, allow_null=True)
    kind = serializers.ChoiceField(choices=["sale", "purchase"], default="sale")
    date = serializers.DateField(required=False)
    notes = serializers.CharField(required=False, allow_blank=True)
    amount_paid = serializers.DecimalField(max_digits=14, decimal_places=2, required=False)
    payment_method = serializers.CharField(required=False, allow_blank=True)
    client_uuid = serializers.CharField(required=False, allow_blank=True)
    lines = QuickSaleLineSerializer(many=True)
