import json
from decimal import Decimal
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.forms import formset_factory
from django.http import JsonResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View

from .forms import OrderForm, OrderStatusForm, NewRecordForm
from .models import Order, OrderRecord
from catalog.models import Product, ProductUnit
from inventory.services import estimate_shortage, consume_for_order


def _product_units_data():
    """Returns: {product_id: [{unit_id, unit_name, conversion_rate, price, cost}, ...]}"""
    data = {}
    qs = (
        ProductUnit.objects
        .filter(status=ProductUnit.Status.ACTIVE)
        .select_related("product", "unit")
    )
    for pu in qs:
        data.setdefault(str(pu.product_id), []).append({
            "unit_id": pu.unit_id,
            "unit_name": pu.unit.name,
            "conversion_rate": pu.conversion_rate,
            "price": str(pu.price),
            "cost": str(pu.cost),
        })
    return data


def _product_options():
    return list(Product.objects.select_related("category").order_by("id"))


def _build_records_from_formset(formset, order):
    """從 NewRecordForm formset 建立 OrderRecord。後端從 active ProductUnit 鎖定 price/cost/conversion_rate。"""
    created = []
    for f in formset:
        if not f.has_changed() or not f.cleaned_data:
            continue
        product = f.cleaned_data["product"]
        unit_id = f.cleaned_data["unit"]
        active_pu = ProductUnit.objects.filter(
            product=product, unit_id=unit_id, status=ProductUnit.Status.ACTIVE
        ).first()
        if not active_pu:
            f.add_error("unit", "此商品該單位目前沒有啟用的定價。")
            continue
        record = OrderRecord.objects.create(
            order=order,
            product=product,
            quantity=f.cleaned_data["quantity"],
            price=active_pu.price,
            cost=active_pu.cost,
            conversion_rate=active_pu.conversion_rate,
            discount=f.discount_ratio,
        )
        created.append(record)
    return created


def _flash_shortage_warning(request, records):
    shortage = estimate_shortage(records)
    for product, need_base in shortage.items():
        messages.warning(
            request,
            f"庫存不足提醒：「{product.name}」尚缺 {need_base} 基準單位。"
        )


def _new_record_formset_cls(extra=1):
    return formset_factory(NewRecordForm, extra=extra, can_delete=False)


class OrderListView(LoginRequiredMixin, View):
    """訂單列表，採輕量分頁：多查一筆（LIMIT page_size+1）判斷有無下一頁，不做 COUNT(*)。"""
    template_name = "orders/order_list.html"
    page_size = 25

    def get(self, request):
        # select: oId, order_date, status, custId, customers.name
        # 總額不在這裡算，留到查看／編輯頁查 order_record

        # 組querySet
        # 這邊select_related 因為在order model設定沒有customer null = True 所以這邊會是用inner join
        qs = (
            Order.objects
            .select_related("customer")
            .only("ordered_date", "status", "customer__name")
        )

        ##取得 query string
        q = request.GET.get("q", "").strip()
        status = request.GET.get("status", "").strip()
        if q:
            # 比對客戶名(customers.name) 或 訂單編號(orders.oId)，不需額外 JOIN
            qs = qs.filter(
                Q(customer__name__icontains=q) | Q(id__icontains=q)
            ).distinct()
        if status:
            qs = qs.filter(status=status)
        qs = qs.order_by("-ordered_date")

        try:
            page = max(1, int(request.GET.get("page", 1)))
        except (TypeError, ValueError):
            page = 1
        offset = (page - 1) * self.page_size
        window = qs[offset:offset + self.page_size + 1]  # 多查一筆
        rows = list(window)
        has_next = len(rows) > self.page_size
        rows = rows[:self.page_size]

        return render(request, self.template_name, {
            "orders": rows,
            "page": page,
            "prev_page": page - 1,
            "next_page": page + 1,
            "has_prev": page > 1,
            "has_next": has_next,
            "q": q,
            "status_filter": status,
            "status_choices": Order.Status.choices,
        })


class OrderCreateView(LoginRequiredMixin, View):
    template_name = "orders/order_form.html"

    def get(self, request):
        FS = _new_record_formset_cls(extra=1)
        return render(request, self.template_name, {
            "form": OrderForm(),
            "formset": FS(prefix="new"),
            "existing_records": [],
            "product_options": _product_options(),
            "product_unit_data_json": json.dumps(_product_units_data()),
            "action": "新增",
        })

    def post(self, request):
        FS = _new_record_formset_cls(extra=0)
        form = OrderForm(request.POST)
        formset = FS(request.POST, prefix="new")
        if form.is_valid() and formset.is_valid():
            # 至少一筆有資料
            if not any(f.has_changed() and f.cleaned_data for f in formset):
                messages.error(request, "至少填寫一筆訂單明細。")
            else:
                with transaction.atomic():
                    order = form.save(commit=False)
                    order.created_by = request.user
                    order.save()
                    records = _build_records_from_formset(formset, order)
                if any(f.errors for f in formset):
                    transaction.set_rollback(True)
                else:
                    _flash_shortage_warning(request, records)
                    messages.success(request, f"訂單 #{order.pk} 建立成功。")
                    return redirect("orders:detail", pk=order.pk)
        return render(request, self.template_name, {
            "form": form,
            "formset": formset,
            "existing_records": [],
            "product_options": _product_options(),
            "product_unit_data_json": json.dumps(_product_units_data()),
            "action": "新增",
        })


class OrderDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        order.delete()
        messages.success(request, f"訂單 #{pk} 已刪除。")
        return redirect("orders:list")


class OrderDetailView(LoginRequiredMixin, View):
    """訂單頁：查看 + 兩個獨立可儲存的區塊 —— 改狀態(save_status)、編輯內容(save_order)。"""
    template_name = "orders/order_detail.html"

    def _get_order(self, pk):
        rows = list(Order.objects.select_related("customer").filter(pk=pk).order_by()[:1])
        if not rows:
            raise Http404("找不到訂單")
        return rows[0]

    def _existing(self, order):
        return order.records.select_related("product")

    def _render(self, request, order, order_form=None, formset=None, status_form=None):
        records = list(self._existing(order))
        total = sum((r.subtotal for r in records), Decimal("0"))
        if formset is None:
            formset = _new_record_formset_cls(extra=1)(prefix="new")
        return render(request, self.template_name, {
            "order": order,
            "records": records,
            "total": total,
            "order_form": order_form or OrderForm(instance=order),
            "status_form": status_form or OrderStatusForm(instance=order),
            "formset": formset,
            "product_options": _product_options(),
            "product_unit_data_json": json.dumps(_product_units_data()),
        })

    def get(self, request, pk):
        return self._render(request, self._get_order(pk))

    def post(self, request, pk):
        order = self._get_order(pk)
        if "save_status" in request.POST:
            return self._save_status(request, order)
        return self._save_order(request, order)

    # ── 區塊一：改狀態 ──────────────────────────────────────────
    def _save_status(self, request, order):
        prev_status = order.status
        form = OrderStatusForm(request.POST, instance=order)
        if form.is_valid():
            new_status = form.cleaned_data["status"]
            with transaction.atomic():
                form.save()
                if new_status == Order.Status.COMPLETED and prev_status != Order.Status.COMPLETED:
                    shortages = consume_for_order(order, by=request.user)
                    for product, missing in shortages.items():
                        messages.warning(
                            request,
                            f"完成扣庫存後仍不足：「{product.name}」缺 {missing} 基準單位（已標記為負庫存）。"
                        )
            messages.success(request, "訂單狀態已更新。")
            return redirect("orders:detail", pk=order.pk)
        return self._render(request, order, status_form=form)

    # ── 區塊二：編輯內容（header + 明細增刪）──────────────────────
    def _save_order(self, request, order):
        FS = _new_record_formset_cls(extra=0)
        form = OrderForm(request.POST, instance=order)
        formset = FS(request.POST, prefix="new")
        delete_ids = set(map(int, request.POST.getlist("delete_record_ids")))
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                order = form.save()
                if delete_ids:
                    OrderRecord.objects.filter(pk__in=delete_ids, order=order).delete()
                _build_records_from_formset(formset, order)
                if any(f.errors for f in formset):
                    transaction.set_rollback(True)
                else:
                    _flash_shortage_warning(request, self._existing(order))
                    messages.success(request, "訂單內容已更新。")
                    return redirect("orders:detail", pk=order.pk)
        return self._render(request, order, order_form=form, formset=formset)


class OrderCancelView(LoginRequiredMixin, View):
    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        if order.status == Order.Status.CANCELLED:
            messages.warning(request, "此訂單已是取消狀態。")
        elif order.status == Order.Status.COMPLETED:
            messages.error(request, "已完成的訂單無法取消（庫存已扣）。")
        else:
            order.cancel()
            messages.success(request, f"訂單 #{pk} 已取消。")
        return redirect("orders:detail", pk=pk)


class ProductUnitsApiView(LoginRequiredMixin, View):
    """AJAX: 回傳某商品所有 active 的單位定價，供訂單表單動態載入。"""

    def get(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        rows = product.product_units.filter(status=ProductUnit.Status.ACTIVE).select_related("unit")
        return JsonResponse({
            "units": [
                {
                    "unit_id": r.unit_id,
                    "unit_name": r.unit.name,
                    "conversion_rate": r.conversion_rate,
                    "price": str(r.price),
                    "cost": str(r.cost),
                }
                for r in rows
            ]
        })
