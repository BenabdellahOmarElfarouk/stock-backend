from django.utils import timezone
from rest_framework.response import Response

from accounts.models import Store
from catalog.models import Article
from parties.models import Customer, Supplier

from .models import Invoice, InvoiceLine
from .serializers import InvoiceSerializer


def process_quick_sale(user, data):
    org = user.organisation
    client_uuid = (data.get("client_uuid") or "").strip()
    if client_uuid:
        existing = Invoice.objects.filter(organisation=org, client_uuid=client_uuid).first()
        if existing:
            return InvoiceSerializer(existing).data, False

    store_id = data.get("store") or user.store_id
    try:
        store = Store.objects.get(pk=store_id, organisation=org)
    except Store.DoesNotExist:
        return {"detail": "Magasin introuvable."}, None

    kind = data.get("kind") or Invoice.Kind.SALE
    customer = None
    supplier = None
    if data.get("customer"):
        customer = Customer.objects.filter(pk=data["customer"], organisation=org).first()
    if data.get("supplier"):
        supplier = Supplier.objects.filter(pk=data["supplier"], organisation=org).first()

    invoice = Invoice.objects.create(
        organisation=org,
        store=store,
        kind=kind,
        customer=customer,
        supplier=supplier,
        date=data.get("date") or timezone.localdate(),
        notes=data.get("notes") or "",
        created_by=user,
        client_uuid=client_uuid,
    )
    for item in data["lines"]:
        article = Article.objects.filter(pk=item["article"], organisation=org).first()
        if not article:
            invoice.delete()
            return {"detail": "Article introuvable."}, None
        price = item.get("unit_price")
        if price is None:
            price = article.sale_price if kind == Invoice.Kind.SALE else article.purchase_price
        InvoiceLine.objects.create(
            invoice=invoice,
            article=article,
            designation=article.name,
            quantity=item["quantity"],
            unit_price=price,
            tax_rate=article.tax.rate if article.tax else 0,
        )
    invoice.recalc()
    try:
        invoice.confirm(user=user)
        paid = data.get("amount_paid")
        if paid is not None:
            invoice.add_payment(
                paid,
                user=user,
                method=data.get("payment_method") or "Espèces",
            )
    except ValueError as exc:
        return {"detail": str(exc)}, None
    invoice.refresh_from_db()
    return InvoiceSerializer(invoice).data, True


def error_or_ok(payload, created):
    if created is None:
        return Response(payload, status=400)
    return Response(payload, status=201 if created else 200)
