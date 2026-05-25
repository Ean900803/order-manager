from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import Q, Sum
from django.shortcuts import render, redirect
from django.views import View
from django.views.generic import ListView

from accounts.models import LV_EMPLOYEE, LV_SALES
from accounts.permissions import LevelRequiredMixin
from catalog.models import Product
from .forms import StockCreateForm
from .models import Stock


class StockBatchListView(LoginRequiredMixin, ListView):
    model = Stock
    template_name = "inventory/stock_list.html"
    context_object_name = "batches"
    queryset = (
        Stock.objects
        .select_related("product", "unit", "restocked_by")
        .order_by("-restocked_date", "-id")
    )


class StockBalanceView(LoginRequiredMixin, View):
    template_name = "inventory/stock_balance.html"

    def get(self, request):
        q = request.GET.get("q", "").strip()
        # JOIN catalog_product + JOIN catalog_category，LIKE 過濾
        stock_qs = Stock.objects.all()
        if q:
            stock_qs = stock_qs.filter(
                Q(product__name__icontains=q) | Q(product__category__name__icontains=q)
            )
        rows = list(
            stock_qs.values("product_id")
            .annotate(total=Sum("quantity_remaining"))
            .order_by("product_id")
        )
        products = {
            p.pk: p
            for p in Product.objects.filter(pk__in=[r["product_id"] for r in rows])
            .select_related("base_unit", "category")
        }
        items = [
            {
                "product": products[r["product_id"]],
                "base_unit": products[r["product_id"]].base_unit,
                "category": products[r["product_id"]].category,
                "total": r["total"] or 0,
            }
            for r in rows
            if r["product_id"] in products
        ]
        return render(request, self.template_name, {
            "items": items,
            "q": q,
            "sql": str(stock_qs.values("product_id").annotate(total=Sum("quantity_remaining")).query),
        })


class StockCreateView(LoginRequiredMixin, LevelRequiredMixin, View):
    template_name = "inventory/stock_form.html"
    min_lv = LV_SALES

    def get(self, request):
        return render(request, self.template_name, {"form": StockCreateForm(requesting_user=request.user)})

    def post(self, request):
        form = StockCreateForm(request.POST, requesting_user=request.user)
        if form.is_valid():
            stock = form.save()
            messages.success(
                request,
                f"進貨成功：{stock.product.name} x{stock.quantity} {stock.unit.name}（剩餘基準 {stock.quantity_remaining}）。"
            )
            return redirect("inventory:stock_list")
        return render(request, self.template_name, {"form": form})
