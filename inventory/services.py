from decimal import Decimal

from django.db import transaction
from django.db.models import F

from .models import Stock, StockMovement


@transaction.atomic
def apply_stock_change(
    *,
    organisation,
    article,
    store,
    kind,
    quantity,
    user=None,
    reason="",
    reference="",
):
    quantity = Decimal(quantity)
    stock, _ = Stock.objects.select_for_update().get_or_create(
        article=article, store=store, defaults={"quantity": 0}
    )
    if kind == StockMovement.Kind.OUT:
        stock.quantity = F("quantity") - quantity
    elif kind == StockMovement.Kind.IN:
        stock.quantity = F("quantity") + quantity
    else:
        stock.quantity = quantity
    stock.save(update_fields=["quantity"])
    stock.refresh_from_db()

    return StockMovement.objects.create(
        organisation=organisation,
        article=article,
        store=store,
        kind=kind,
        quantity=quantity,
        reason=reason,
        reference=reference,
        created_by=user,
    )
