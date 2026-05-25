import json
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.forms import formset_factory
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import ListView

from .forms import OrderForm, OrderStatusForm, NewRecordForm
from .models import Order, OrderRecord
from catalog.models import Product, ProductUnit
from accounts.models import LV_EMPLOYEE, LV_MANAGER
from accounts.permissions import LevelRequiredMixin
from inventory.services import estimate_shortage, consume_for_order


def _product_units_data():
    """Returns: {product_id: [{unit_id, unit_name, conversion_rate, price, cost}, ...]}"""
    data = {}
    qs = (
        ProductUnit.objects
        .filter(status=ProductUnit.Status.ACTIVE, product__deleted_at__isnull=True)
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


def _build_records_from_formset(formset, order, user):
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
            unit_id=unit_id,
            quantity=f.cleaned_data["quantity"],
            price=active_pu.price,
            cost=active_pu.cost,
            conversion_rate=active_pu.conversion_rate,
            discount=f.discount_ratio,
            created_by=user,
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


class OrderListView(LoginRequiredMixin, ListView):
    model = Order
    template_name = "orders/order_list.html"
    context_object_name = "orders"
    paginate_by = 25

    def get_queryset(self):
        qs = (
            Order.objects.filter(deleted_at__isnull=True)
            .select_related("customer")
            .prefetch_related("records__product", "records__unit")
        )
        q = self.request.GET.get("q", "").strip()
        status = self.request.GET.get("status", "").strip()
        if q:
            # JOIN customers_customer + JOIN orders_orderrecord + JOIN catalog_product
            # 產生 LIKE '%q%' OR LIKE '%q%'
            qs = qs.filter(
                Q(customer__name__icontains=q) | Q(records__product__name__icontains=q)
            ).distinct()
        if status:
            qs = qs.filter(status=status)
        return qs.order_by("-ordered_date")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        ctx["status_filter"] = self.request.GET.get("status", "")
        ctx["status_choices"] = Order.Status.choices
        ctx["sql"] = str(self.get_queryset().query)
        return ctx


class OrderCreateView(LoginRequiredMixin, LevelRequiredMixin, View):
    template_name = "orders/order_form.html"
    min_lv = LV_EMPLOYEE

    def get(self, request):
        FS = _new_record_formset_cls(extra=1)
        return render(request, self.template_name, {
            "form": OrderForm(),
            "formset": FS(prefix="new"),
            "existing_records": [],
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
                    order = form.save()
                    records = _build_records_from_formset(formset, order, request.user)
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
            "product_unit_data_json": json.dumps(_product_units_data()),
            "action": "新增",
        })


class OrderEditView(LoginRequiredMixin, LevelRequiredMixin, View):
    """編輯：header 可改、可追加新明細、可軟刪除既有明細；既有明細的數量/價格/折扣不可改。"""
    template_name = "orders/order_form.html"
    min_lv = LV_EMPLOYEE

    def _existing(self, order):
        return order.records.filter(deleted_at__isnull=True).select_related("product", "unit")

    def get(self, request, pk):
        order = get_object_or_404(Order, pk=pk, deleted_at__isnull=True)
        FS = _new_record_formset_cls(extra=0)
        return render(request, self.template_name, {
            "form": OrderForm(instance=order),
            "formset": FS(prefix="new"),
            "existing_records": self._existing(order),
            "product_unit_data_json": json.dumps(_product_units_data()),
            "action": "編輯",
            "order": order,
            "back_url": reverse("orders:detail", kwargs={"pk": pk}),
        })

    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk, deleted_at__isnull=True)
        FS = _new_record_formset_cls(extra=0)
        form = OrderForm(request.POST, instance=order)
        formset = FS(request.POST, prefix="new")
        delete_ids = set(map(int, request.POST.getlist("delete_record_ids")))

        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                order = form.save()
                if delete_ids:
                    OrderRecord.objects.filter(pk__in=delete_ids, order=order, deleted_at__isnull=True).update(
                        deleted_at=timezone.now(), deleted_by=request.user
                    )
                new_records = _build_records_from_formset(formset, order, request.user)
                if any(f.errors for f in formset):
                    transaction.set_rollback(True)
                else:
                    _flash_shortage_warning(request, self._existing(order))
                    messages.success(request, "訂單更新成功。")
                    return redirect("orders:detail", pk=order.pk)
        return render(request, self.template_name, {
            "form": form,
            "formset": formset,
            "existing_records": self._existing(order),
            "product_unit_data_json": json.dumps(_product_units_data()),
            "action": "編輯",
            "order": order,
            "back_url": reverse("orders:detail", kwargs={"pk": pk}),
        })


class OrderDeleteView(LoginRequiredMixin, LevelRequiredMixin, View):
    min_lv = LV_MANAGER

    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk, deleted_at__isnull=True)
        order.deleted_at = timezone.now()
        order.deleted_by = request.user
        order.save(update_fields=["deleted_at", "deleted_by"])
        messages.success(request, f"訂單 #{pk} 已刪除。")
        return redirect("orders:list")


class OrderDetailView(LoginRequiredMixin, View):
    template_name = "orders/order_detail.html"

    def get(self, request, pk):
        order = get_object_or_404(Order, pk=pk, deleted_at__isnull=True)
        records = order.records.filter(deleted_at__isnull=True).select_related("product", "unit")
        return render(request, self.template_name, {"order": order, "records": records})


class OrderStatusView(LoginRequiredMixin, LevelRequiredMixin, View):
    template_name = "orders/order_status.html"
    min_lv = LV_MANAGER

    def get(self, request, pk):
        order = get_object_or_404(Order, pk=pk, deleted_at__isnull=True)
        form = OrderStatusForm(instance=order)
        records = order.records.filter(deleted_at__isnull=True).select_related("product", "unit")
        return render(request, self.template_name, {"order": order, "form": form, "records": records})

    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk, deleted_at__isnull=True)
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
            return redirect("orders:detail", pk=pk)
        records = order.records.filter(deleted_at__isnull=True).select_related("product", "unit")
        return render(request, self.template_name, {"order": order, "form": form, "records": records})


class OrderCancelView(LoginRequiredMixin, LevelRequiredMixin, View):
    min_lv = LV_MANAGER

    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk, deleted_at__isnull=True)
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
        product = get_object_or_404(Product, pk=pk, deleted_at__isnull=True)
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
