from django.db.models import Sum
from rest_framework import serializers

from inventory.models import Stock

from .models import Article, Category, PaymentMethod, TaxRate, Unit


class CategorySerializer(serializers.ModelSerializer):
    parent_name = serializers.CharField(source="parent.name", read_only=True)
    children_count = serializers.IntegerField(source="children.count", read_only=True)

    class Meta:
        model = Category
        fields = (
            "id",
            "name",
            "parent",
            "parent_name",
            "is_active",
            "sort_order",
            "children_count",
        )
        read_only_fields = ("id",)


class UnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Unit
        fields = ("id", "name", "symbol", "is_active")
        read_only_fields = ("id",)


class TaxRateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaxRate
        fields = ("id", "name", "rate", "is_active")
        read_only_fields = ("id",)


class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = ("id", "name", "is_active")
        read_only_fields = ("id",)


class ArticleSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    unit_symbol = serializers.CharField(source="unit.symbol", read_only=True)
    tax_rate = serializers.DecimalField(
        source="tax.rate", max_digits=5, decimal_places=2, read_only=True
    )
    stock_quantity = serializers.SerializerMethodField()

    class Meta:
        model = Article
        fields = (
            "id",
            "sku",
            "barcode",
            "name",
            "brand",
            "description",
            "category",
            "category_name",
            "unit",
            "unit_symbol",
            "tax",
            "tax_rate",
            "purchase_price",
            "sale_price",
            "min_stock",
            "location",
            "is_active",
            "stock_quantity",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def get_stock_quantity(self, obj):
        if hasattr(obj, "total_stock"):
            return obj.total_stock
        total = Stock.objects.filter(article=obj).aggregate(s=Sum("quantity"))["s"]
        return total or 0
