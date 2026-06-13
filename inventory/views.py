from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import Q, Sum
from django.shortcuts import render, redirect
from django.views import View
from catalog.models import Product
from .forms import StockCreateForm
from .models import Stock

PAGINATE_BY = 30


def _paginate(qs, request):
    try:
        page = max(1, int(request.GET.get("page", 1)))
    except ValueError:
        page = 1
    offset = (page - 1) * PAGINATE_BY
    rows = list(qs[offset : offset + PAGINATE_BY + 1])
    has_next = len(rows) > PAGINATE_BY
    return rows[:PAGINATE_BY], {"page": page, "has_previous": page > 1, "has_next": has_next, "previous_page": page - 1, "next_page": page + 1}


class StockBatchListView(LoginRequiredMixin, View):
    template_name = "inventory/stock_list.html"

    def get(self, request):
        qs = Stock.objects.select_related("product", "unit").order_by("-id")
        batches, paging = _paginate(qs, request)
        return render(request, self.template_name, {"batches": batches, **paging})


class StockBalanceView(LoginRequiredMixin, View):
    template_name = "inventory/stock_balance.html"

    def get(self, request):
        q = request.GET.get("q", "").strip()
        stock_qs = Stock.objects.all()
        if q:
            stock_qs = stock_qs.filter(
                Q(product__name__icontains=q) | Q(product__category__name__icontains=q)
            )
        agg_qs = (
            stock_qs.values("product_id")
            .annotate(total=Sum("quantity_remaining"))
            .order_by("product_id")
        )
        rows, paging = _paginate(agg_qs, request)
        products = {
            p.pk: p
            for p in Product.objects.filter(pk__in=[r["product_id"] for r in rows])
            .select_related("category")
        }
        items = [
            {
                "product": products[r["product_id"]],
                "category": products[r["product_id"]].category,
                "total": r["total"] or 0,
            }
            for r in rows
            if r["product_id"] in products
        ]
        return render(request, self.template_name, {"items": items, "q": q, **paging})


class StockCreateView(LoginRequiredMixin, View):
    template_name = "inventory/stock_form.html"

    def get(self, request):
        return render(request, self.template_name, {"form": StockCreateForm()})

    def post(self, request):
        form = StockCreateForm(request.POST)
        if form.is_valid():
            stock = form.save()
            messages.success(
                request,
                f"進貨成功：{stock.product.name} x{stock.quantity} {stock.unit.name}（剩餘基準 {stock.quantity_remaining}）。"
            )
            return redirect("inventory:stock_list")
        return render(request, self.template_name, {"form": form})
