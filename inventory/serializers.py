from rest_framework import serializers

from .models import Stock, StockMovement


class StockSerializer(serializers.ModelSerializer):
    article_name = serializers.CharField(source="article.name", read_only=True)
    sku = serializers.CharField(source="article.sku", read_only=True)
    barcode = serializers.CharField(source="article.barcode", read_only=True)
    min_stock = serializers.DecimalField(
        source="article.min_stock", max_digits=12, decimal_places=3, read_only=True
    )
    store_name = serializers.CharField(source="store.name", read_only=True)
    sale_price = serializers.DecimalField(
        source="article.sale_price", max_digits=12, decimal_places=2, read_only=True
    )
    is_low = serializers.SerializerMethodField()

    class Meta:
        model = Stock
        fields = (
            "id",
            "article",
            "article_name",
            "sku",
            "barcode",
            "store",
            "store_name",
            "quantity",
            "min_stock",
            "sale_price",
            "is_low",
        )

    def get_is_low(self, obj):
        return obj.quantity <= obj.article.min_stock


class StockMovementSerializer(serializers.ModelSerializer):
    article_name = serializers.CharField(source="article.name", read_only=True)
    sku = serializers.CharField(source="article.sku", read_only=True)
    store_name = serializers.CharField(source="store.name", read_only=True)
    created_by_name = serializers.CharField(source="created_by.username", read_only=True)

    class Meta:
        model = StockMovement
        fields = (
            "id",
            "article",
            "article_name",
            "sku",
            "store",
            "store_name",
            "kind",
            "quantity",
            "reason",
            "reference",
            "created_by",
            "created_by_name",
            "created_at",
        )
        read_only_fields = ("id", "created_by", "created_at")


class StockAdjustSerializer(serializers.Serializer):
    article = serializers.IntegerField()
    store = serializers.IntegerField()
    kind = serializers.ChoiceField(choices=["in", "out", "adjust"])
    quantity = serializers.DecimalField(max_digits=14, decimal_places=3)
    reason = serializers.CharField(required=False, allow_blank=True)
