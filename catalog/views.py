from django.db.models import Prefetch, Sum
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.mixins import OrganisationScopedMixin
from inventory.models import Stock

from .models import Article, Category, PaymentMethod, TaxRate, Unit
from .serializers import (
    ArticleSerializer,
    CategorySerializer,
    PaymentMethodSerializer,
    TaxRateSerializer,
    UnitSerializer,
)


class CategoryViewSet(OrganisationScopedMixin, viewsets.ModelViewSet):
    queryset = Category.objects.select_related("parent").prefetch_related("children")
    serializer_class = CategorySerializer
    search_fields = ("name",)
    filterset_fields = ("parent", "is_active")
    pagination_class = None

    @action(detail=False, methods=["get"])
    def tree(self, request):
        roots = self.get_queryset().filter(parent__isnull=True)
        data = []
        for root in roots:
            data.append(
                {
                    **CategorySerializer(root).data,
                    "children": CategorySerializer(root.children.all(), many=True).data,
                }
            )
        return Response(data)


class UnitViewSet(OrganisationScopedMixin, viewsets.ModelViewSet):
    queryset = Unit.objects.all()
    serializer_class = UnitSerializer
    search_fields = ("name", "symbol")


class TaxRateViewSet(OrganisationScopedMixin, viewsets.ModelViewSet):
    queryset = TaxRate.objects.all()
    serializer_class = TaxRateSerializer


class PaymentMethodViewSet(OrganisationScopedMixin, viewsets.ModelViewSet):
    queryset = PaymentMethod.objects.all()
    serializer_class = PaymentMethodSerializer
    pagination_class = None


class ArticleViewSet(OrganisationScopedMixin, viewsets.ModelViewSet):
    queryset = Article.objects.select_related("category", "unit", "tax")
    serializer_class = ArticleSerializer
    search_fields = ("sku", "barcode", "name", "brand")
    filterset_fields = ("category", "is_active", "unit")
    ordering_fields = ("name", "sku", "sale_price", "created_at")

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .annotate(total_stock=Sum("stocks__quantity"))
            .prefetch_related(Prefetch("stocks", queryset=Stock.objects.select_related("store")))
        )

    def perform_create(self, serializer):
        serializer.save(
            organisation=self.request.user.organisation,
            created_by=self.request.user,
        )

    @action(detail=False, methods=["get"])
    def suggest(self, request):
        q = (request.query_params.get("q") or "").strip()
        qs = self.get_queryset().filter(is_active=True)
        if q:
            from django.db.models import Q

            qs = qs.filter(
                Q(name__icontains=q)
                | Q(sku__icontains=q)
                | Q(barcode__icontains=q)
                | Q(brand__icontains=q)
            )
        return Response(self.get_serializer(qs[:8], many=True).data)

    @action(detail=False, methods=["get"], url_path="by-barcode")
    def by_barcode(self, request):
        code = (request.query_params.get("code") or "").strip()
        if not code:
            return Response({"detail": "code requis"}, status=400)
        article = self.get_queryset().filter(barcode=code, is_active=True).first()
        if not article:
            article = self.get_queryset().filter(sku=code, is_active=True).first()
        if not article:
            return Response({"detail": "Article introuvable"}, status=404)
        return Response(self.get_serializer(article).data)
