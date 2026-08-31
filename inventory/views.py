from django.db.models import F
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.models import Store
from catalog.models import Article

from .models import Stock, StockMovement
from .serializers import StockAdjustSerializer, StockMovementSerializer, StockSerializer
from .services import apply_stock_change


class StockViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = StockSerializer
    search_fields = ("article__name", "article__sku", "article__barcode")
    filterset_fields = ("store",)

    def get_queryset(self):
        org = self.request.user.organisation
        qs = Stock.objects.filter(article__organisation=org).select_related(
            "article", "store"
        )
        if self.request.query_params.get("low") == "1":
            qs = qs.filter(quantity__lte=F("article__min_stock"))
        return qs

    @action(detail=False, methods=["post"])
    def adjust(self, request):
        serializer = StockAdjustSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        org = request.user.organisation
        try:
            article = Article.objects.get(pk=data["article"], organisation=org)
            store = Store.objects.get(pk=data["store"], organisation=org)
        except (Article.DoesNotExist, Store.DoesNotExist):
            return Response({"detail": "Article ou magasin introuvable."}, status=400)
        movement = apply_stock_change(
            organisation=org,
            article=article,
            store=store,
            kind=data["kind"],
            quantity=data["quantity"],
            user=request.user,
            reason=data.get("reason", ""),
        )
        return Response(StockMovementSerializer(movement).data, status=status.HTTP_201_CREATED)


class StockMovementViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = StockMovementSerializer
    filterset_fields = ("kind", "store", "article")
    search_fields = ("article__name", "article__sku", "reference")

    def get_queryset(self):
        return StockMovement.objects.filter(
            organisation=self.request.user.organisation
        ).select_related("article", "store", "created_by")
