from django.db.models import Sum
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Store
from catalog.models import Article
from catalog.serializers import ArticleSerializer
from parties.models import Customer
from parties.serializers import CustomerSerializer

from .models import Invoice
from .sale import process_quick_sale
from .serializers import InvoiceSerializer, QuickSaleSerializer


class StoreMiniSerializer:
    @staticmethod
    def many(stores):
        return [
            {
                "id": s.id,
                "name": s.name,
                "address": s.address,
                "phone": s.phone,
                "is_default": s.is_default,
            }
            for s in stores
        ]


class SyncPullView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        org = request.user.organisation
        if org is None:
            return Response({"detail": "Compte plateforme : pas de synchro magasin."}, status=400)
        articles = (
            Article.objects.filter(organisation=org, is_active=True)
            .select_related("category", "unit", "tax")
            .annotate(total_stock=Sum("stocks__quantity"))
        )
        customers = Customer.objects.filter(organisation=org, is_active=True)
        stores = Store.objects.filter(organisation=org)
        invoices = (
            Invoice.objects.filter(organisation=org)
            .exclude(status="draft")
            .select_related("customer", "supplier", "store")
            .prefetch_related("lines__article", "payments")[:80]
        )
        return Response(
            {
                "pulled_at": timezone.now().isoformat(),
                "articles": ArticleSerializer(articles, many=True).data,
                "customers": CustomerSerializer(customers, many=True).data,
                "stores": StoreMiniSerializer.many(stores),
                "invoices": InvoiceSerializer(invoices, many=True).data,
            }
        )


class SyncPushView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        org = request.user.organisation
        if org is None:
            return Response({"detail": "Compte plateforme."}, status=400)

        customer_map = {}
        for item in request.data.get("customers") or []:
            local_id = item.get("local_id")
            customer = Customer.objects.create(
                organisation=org,
                name=item.get("name") or "Client",
                phone=item.get("phone") or "",
                city=item.get("city") or "",
            )
            if local_id is not None:
                customer_map[str(local_id)] = customer.id

        sales_out = []
        for raw in request.data.get("sales") or []:
            payload = dict(raw)
            local_customer = payload.pop("local_customer_id", None)
            if local_customer is not None and not payload.get("customer"):
                payload["customer"] = customer_map.get(str(local_customer))
            serializer = QuickSaleSerializer(data=payload)
            if not serializer.is_valid():
                sales_out.append(
                    {
                        "client_uuid": raw.get("client_uuid"),
                        "ok": False,
                        "detail": serializer.errors,
                    }
                )
                continue
            result, created = process_quick_sale(request.user, serializer.validated_data)
            if created is None:
                sales_out.append(
                    {
                        "client_uuid": raw.get("client_uuid"),
                        "ok": False,
                        "detail": result.get("detail", result),
                    }
                )
            else:
                sales_out.append(
                    {
                        "client_uuid": raw.get("client_uuid"),
                        "ok": True,
                        "created": created,
                        "invoice": result,
                    }
                )

        return Response({"customer_map": customer_map, "sales": sales_out})
