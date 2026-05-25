"""庫存服務：FIFO 扣庫存、缺貨估算。"""
from collections import defaultdict

from django.db import transaction
from django.db.models import Sum

from catalog.models import Product
from .models import Stock


def estimate_shortage(records):
    """估算每個商品的缺貨量（基準單位）。

    records: iterable of OrderRecord (已存的，或剛建立的)
    回傳: {Product: missing_base_qty} 只包含缺貨的商品
    """
    need = defaultdict(int)
    for r in records:
        need[r.product_id] += r.quantity * r.conversion_rate
    if not need:
        return {}

    available = {
        row["product_id"]: row["total"] or 0
        for row in Stock.objects.filter(product_id__in=need.keys())
        .values("product_id")
        .annotate(total=Sum("quantity_remaining"))
    }
    shortage = {}
    products = {p.pk: p for p in Product.objects.filter(pk__in=need.keys())}
    for pid, need_qty in need.items():
        avail = available.get(pid, 0)
        if need_qty > avail:
            shortage[products[pid]] = need_qty - avail
    return shortage


@transaction.atomic
def consume_for_order(order, by=None):
    """訂單完成時依 FIFO 扣庫存。允許扣到負值（最後一個批次承擔負量）。

    回傳: {Product: missing_base_qty} 只包含扣完仍不足的商品
    """
    # 彙整：每個 product 需要多少基準單位
    need = defaultdict(int)
    for r in order.records.filter(deleted_at__isnull=True):
        need[r.product_id] += r.quantity * r.conversion_rate

    shortages = {}
    products = {p.pk: p for p in Product.objects.filter(pk__in=need.keys())} if need else {}

    for pid, need_qty in need.items():
        # 依 FIFO 順序取批次，並鎖定避免併發
        batches = list(
            Stock.objects.select_for_update()
            .filter(product_id=pid)
            .order_by("restocked_date", "id")
        )
        remaining_need = need_qty
        last_positive_batch = None

        for batch in batches:
            if batch.quantity_remaining > 0:
                last_positive_batch = batch
            if remaining_need <= 0:
                break
            if batch.quantity_remaining <= 0:
                continue
            deduct = min(batch.quantity_remaining, remaining_need)
            batch.quantity_remaining -= deduct
            batch.save(update_fields=["quantity_remaining"])
            remaining_need -= deduct

        if remaining_need > 0:
            # 仍有缺：扣到「最近一個曾有正餘額的批次」，若沒有則扣到最後一個批次
            target = last_positive_batch or (batches[-1] if batches else None)
            if target is not None:
                target.quantity_remaining -= remaining_need
                target.save(update_fields=["quantity_remaining"])
            shortages[products[pid]] = remaining_need

    return shortages
