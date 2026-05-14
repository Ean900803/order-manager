import json
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import ListView

from .forms import OrderForm, OrderStatusForm, OrderRecordFormSet
from .models import Order, OrderRecord
from catalog.models import Product
from accounts.models import LV_EMPLOYEE, LV_MANAGER
from accounts.permissions import LevelRequiredMixin


class OrderListView(LoginRequiredMixin, ListView):
    model = Order
    template_name = "orders/order_list.html"
    context_object_name = "orders"

    def get_queryset(self):
        return (
            Order.objects.filter(deleted_at__isnull=True)
            .select_related("customer")
            .prefetch_related("records")
            .order_by("-ordered_date")
        )


class OrderCreateView(LoginRequiredMixin, LevelRequiredMixin, View):
    template_name = "orders/order_form.html"
    min_lv = LV_EMPLOYEE

    def _product_data(self):
        products = Product.objects.filter(deleted_at__isnull=True).select_related("category")
        return {str(p.pk): {"price": str(p.price), "cost": str(p.cost), "name": p.name} for p in products}

    def get(self, request):
        form = OrderForm()
        formset = OrderRecordFormSet()
        return render(request, self.template_name, {
            "form": form,
            "formset": formset,
            "product_data_json": json.dumps(self._product_data()),
            "action": "新增",
        })

    def post(self, request):
        form = OrderForm(request.POST)
        formset = OrderRecordFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                order = form.save()
                records = formset.save(commit=False)
                for record in records:
                    product = record.product
                    record.order = order
                    record.price = product.price
                    record.cost = product.cost
                    record.save()
                for obj in formset.deleted_objects:
                    obj.delete()
            messages.success(request, "訂單建立成功。")
            return redirect("orders:detail", pk=order.pk)
        return render(request, self.template_name, {
            "form": form,
            "formset": formset,
            "product_data_json": json.dumps(self._product_data()),
            "action": "新增",
        })


class OrderDetailView(LoginRequiredMixin, View):
    template_name = "orders/order_detail.html"

    def get(self, request, pk):
        order = get_object_or_404(Order, pk=pk, deleted_at__isnull=True)
        records = order.records.filter(deleted_at__isnull=True).select_related("product")
        return render(request, self.template_name, {
            "order": order,
            "records": records,
        })


class OrderStatusView(LoginRequiredMixin, LevelRequiredMixin, View):
    template_name = "orders/order_status.html"
    min_lv = LV_MANAGER

    def get(self, request, pk):
        order = get_object_or_404(Order, pk=pk, deleted_at__isnull=True)
        form = OrderStatusForm(instance=order)
        records = order.records.filter(deleted_at__isnull=True).select_related("product")
        return render(request, self.template_name, {"order": order, "form": form, "records": records})

    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk, deleted_at__isnull=True)
        form = OrderStatusForm(request.POST, instance=order)
        if form.is_valid():
            form.save()
            messages.success(request, "訂單狀態已更新。")
            return redirect("orders:detail", pk=pk)
        records = order.records.filter(deleted_at__isnull=True).select_related("product")
        return render(request, self.template_name, {"order": order, "form": form, "records": records})


class OrderCancelView(LoginRequiredMixin, LevelRequiredMixin, View):
    min_lv = LV_MANAGER

    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk, deleted_at__isnull=True)
        if order.status == Order.STATUS_CANCELLED:
            messages.warning(request, "此訂單已是取消狀態。")
        else:
            order.cancel()
            messages.success(request, f"訂單 #{pk} 已取消。")
        return redirect("orders:detail", pk=pk)


class ProductPriceApiView(LoginRequiredMixin, View):
    """AJAX endpoint: 回傳商品售價與成本，供訂單表單即時計算用"""

    def get(self, request, pk):
        product = get_object_or_404(Product, pk=pk, deleted_at__isnull=True)
        return JsonResponse({"price": str(product.price), "cost": str(product.cost)})
