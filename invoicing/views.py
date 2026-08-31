from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Count, F, Sum
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.mixins import OrganisationScopedMixin
from accounts.models import Store
from catalog.models import Article
from inventory.models import Stock
from parties.models import Customer, Supplier

from .models import Invoice, InvoiceLine
from .serializers import InvoiceSerializer, QuickSaleSerializer


OPEN_STATUSES = ("confirmed", "partial", "paid")


class InvoiceViewSet(OrganisationScopedMixin, viewsets.ModelViewSet):
    queryset = Invoice.objects.select_related(
        "customer", "supplier", "store", "created_by"
    ).prefetch_related("lines__article", "payments")
    serializer_class = InvoiceSerializer
    search_fields = ("number", "customer__name", "supplier__name", "notes")
    filterset_fields = ("kind", "status", "store", "date")
    ordering_fields = ("date", "total_ttc", "number")

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        date_from = params.get("date_from")
        date_to = params.get("date_to")
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)
        due_only = params.get("due")
        if due_only == "1":
            qs = qs.exclude(status__in=["draft", "paid", "cancelled"])
        return qs

    def perform_create(self, serializer):
        user = self.request.user
        store = serializer.validated_data.get("store") or user.store
        serializer.save(organisation=user.organisation, created_by=user, store=store)

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        invoice = self.get_object()
        try:
            invoice.confirm(user=request.user)
            amount = request.data.get("amount_paid")
            if amount not in (None, "",):
                invoice.add_payment(
                    amount,
                    user=request.user,
                    method=request.data.get("payment_method") or "Espèces",
                    notes=request.data.get("payment_notes") or "",
                )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        invoice.refresh_from_db()
        return Response(self.get_serializer(invoice).data)

    @action(detail=True, methods=["post"])
    def add_payment(self, request, pk=None):
        invoice = self.get_object()
        try:
            invoice.add_payment(
                request.data.get("amount"),
                user=request.user,
                method=request.data.get("method") or "Espèces",
                notes=request.data.get("notes") or "",
                date=request.data.get("date") or None,
            )
        except (ValueError, TypeError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        invoice.refresh_from_db()
        return Response(self.get_serializer(invoice).data)

    @action(detail=True, methods=["post"])
    def mark_paid(self, request, pk=None):
        invoice = self.get_object()
        if invoice.status == Invoice.Status.DRAFT:
            return Response(
                {"detail": "Validez d'abord la facture."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            if invoice.amount_due > 0:
                invoice.add_payment(
                    invoice.amount_due,
                    user=request.user,
                    method=request.data.get("method") or "Espèces",
                    notes="Solde",
                )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        invoice.refresh_from_db()
        return Response(self.get_serializer(invoice).data)

    @action(detail=False, methods=["post"], url_path="quick-sale")
    def quick_sale(self, request):
        from .sale import error_or_ok, process_quick_sale

        serializer = QuickSaleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload, created = process_quick_sale(request.user, serializer.validated_data)
        return error_or_ok(payload, created)


class DashboardViewSet(viewsets.ViewSet):
    def list(self, request):
        org = request.user.organisation
        today = timezone.localdate()
        date_from = request.query_params.get("date_from") or today.replace(day=1).isoformat()
        date_to = request.query_params.get("date_to") or today.isoformat()
        store_id = request.query_params.get("store")
        kind = request.query_params.get("kind")

        invoices = Invoice.objects.filter(
            organisation=org, date__gte=date_from, date__lte=date_to
        ).prefetch_related("payments")
        if store_id:
            invoices = invoices.filter(store_id=store_id)
        if kind:
            invoices = invoices.filter(kind=kind)

        posted = invoices.exclude(status__in=["draft", "cancelled"])
        sales = posted.filter(kind=Invoice.Kind.SALE)
        purchases = posted.filter(kind=Invoice.Kind.PURCHASE)

        def money_stats(qs):
            total = qs.aggregate(c=Count("id"), t=Sum("total_ttc"))
            paid = Decimal("0")
            due = Decimal("0")
            for inv in qs:
                paid += inv.amount_paid
                due += inv.amount_due
            return {
                "count": total["c"] or 0,
                "total": total["t"] or 0,
                "paid": paid,
                "due": due,
            }

        daily_map = {}
        for inv in posted:
            key = inv.date.isoformat()
            bucket = daily_map.setdefault(key, {"date": key, "sales": Decimal("0"), "purchases": Decimal("0")})
            if inv.kind == Invoice.Kind.SALE:
                bucket["sales"] += inv.total_ttc
            else:
                bucket["purchases"] += inv.total_ttc

        start = date.fromisoformat(str(date_from))
        end = date.fromisoformat(str(date_to))
        if (end - start).days > 60:
            daily = list(daily_map.values())
        else:
            daily = []
            cursor = start
            while cursor <= end:
                key = cursor.isoformat()
                daily.append(daily_map.get(key, {"date": key, "sales": 0, "purchases": 0}))
                cursor += timedelta(days=1)

        top_articles = (
            InvoiceLine.objects.filter(invoice__in=sales)
            .values("article_id", "article__name", "article__sku")
            .annotate(qty=Sum("quantity"), total=Sum("unit_price"))
            .order_by("-qty")[:6]
        )
        # total above is wrong (sum of unit prices). Compute line totals in python for top 6 by qty is ok-ish.
        # Better: annotate with quantity * unit_price
        top_articles = list(
            InvoiceLine.objects.filter(invoice__in=sales)
            .values("article_id", "article__name", "article__sku")
            .annotate(qty=Sum("quantity"))
            .order_by("-qty")[:6]
        )
        for row in top_articles:
            lines = InvoiceLine.objects.filter(
                invoice__in=sales, article_id=row["article_id"]
            )
            row["total"] = sum((l.quantity * l.unit_price for l in lines), Decimal("0"))

        debtors = []
        for customer in org.customers.filter(is_active=True):
            due = Decimal("0")
            for inv in customer.invoices.filter(kind="sale", status__in=["confirmed", "partial"]):
                due += inv.amount_due
            if due > 0:
                debtors.append({"id": customer.id, "name": customer.name, "due": due})
        debtors.sort(key=lambda x: x["due"], reverse=True)

        low_items = (
            Stock.objects.filter(article__organisation=org, quantity__lte=F("article__min_stock"))
            .select_related("article", "store")[:8]
        )

        return Response(
            {
                "period": {"date_from": date_from, "date_to": date_to},
                "articles": Article.objects.filter(organisation=org, is_active=True).count(),
                "customers": org.customers.filter(is_active=True).count(),
                "suppliers": org.suppliers.filter(is_active=True).count(),
                "low_stock": Stock.objects.filter(
                    article__organisation=org, quantity__lte=F("article__min_stock")
                ).count(),
                "sales": money_stats(sales),
                "purchases": money_stats(purchases),
                "sales_today": Invoice.objects.filter(
                    organisation=org,
                    kind="sale",
                    status__in=OPEN_STATUSES,
                    date=today,
                ).aggregate(count=Count("id"), total=Sum("total_ttc")),
                "daily": daily,
                "top_articles": [
                    {
                        "id": r["article_id"],
                        "name": r["article__name"],
                        "sku": r["article__sku"],
                        "qty": r["qty"],
                        "total": r["total"],
                    }
                    for r in top_articles
                ],
                "top_debtors": debtors[:6],
                "low_items": [
                    {
                        "article_id": s.article_id,
                        "name": s.article.name,
                        "sku": s.article.sku,
                        "quantity": s.quantity,
                        "min_stock": s.article.min_stock,
                        "store": s.store.name,
                    }
                    for s in low_items
                ],
                "recent_invoices": InvoiceSerializer(
                    invoices.order_by("-date", "-id")[:8], many=True
                ).data,
            }
        )
