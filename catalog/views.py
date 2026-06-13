from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import Prefetch, Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from .forms import CategoryForm, ProductForm, UnitForm, ProductUnitForm
from .models import Category, Product, Unit, ProductUnit

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


# ── Category ─────────────────────────────────────────────────────────────────

class CategoryListView(LoginRequiredMixin, View):
    template_name = "catalog/category_list.html"

    def get(self, request):
        categories, paging = _paginate(Category.objects.all().order_by("id"), request)
        return render(request, self.template_name, {"categories": categories, **paging})


class CategoryCreateView(LoginRequiredMixin, View):
    template_name = "catalog/category_form.html"

    def get(self, request):
        return render(request, self.template_name, {"form": CategoryForm(), "action": "新增"})

    def post(self, request):
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "分類新增成功。")
            return redirect("catalog:category_list")
        return render(request, self.template_name, {"form": form, "action": "新增"})


class CategoryEditView(LoginRequiredMixin, View):
    template_name = "catalog/category_form.html"

    def get(self, request, pk):
        category = get_object_or_404(Category, pk=pk)
        return render(request, self.template_name, {"form": CategoryForm(instance=category), "action": "編輯", "category": category})

    def post(self, request, pk):
        category = get_object_or_404(Category, pk=pk)
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, "分類更新成功。")
            return redirect("catalog:category_list")
        return render(request, self.template_name, {"form": form, "action": "編輯", "category": category})


class CategoryDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        category = get_object_or_404(Category, pk=pk)
        name = category.name
        try:
            category.delete()
            messages.success(request, f"分類「{name}」已刪除。")
        except ProtectedError:
            messages.error(request, f"分類「{name}」仍被商品引用，無法刪除。")
        return redirect("catalog:category_list")


# ── Unit ──────────────────────────────────────────────────────────────────────

class UnitListView(LoginRequiredMixin, View):
    template_name = "catalog/unit_list.html"

    def get(self, request):
        units, paging = _paginate(Unit.objects.all().order_by("id"), request)
        return render(request, self.template_name, {"units": units, **paging})


class UnitCreateView(LoginRequiredMixin, View):
    template_name = "catalog/unit_form.html"

    def get(self, request):
        return render(request, self.template_name, {"form": UnitForm(), "action": "新增"})

    def post(self, request):
        form = UnitForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "單位新增成功。")
            return redirect("catalog:unit_list")
        return render(request, self.template_name, {"form": form, "action": "新增"})


class UnitEditView(LoginRequiredMixin, View):
    template_name = "catalog/unit_form.html"

    def get(self, request, pk):
        unit = get_object_or_404(Unit, pk=pk)
        return render(request, self.template_name, {"form": UnitForm(instance=unit), "action": "編輯", "unit": unit})

    def post(self, request, pk):
        unit = get_object_or_404(Unit, pk=pk)
        form = UnitForm(request.POST, instance=unit)
        if form.is_valid():
            form.save()
            messages.success(request, "單位更新成功。")
            return redirect("catalog:unit_list")
        return render(request, self.template_name, {"form": form, "action": "編輯", "unit": unit})


class UnitDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        unit = get_object_or_404(Unit, pk=pk)
        name = unit.name
        try:
            unit.delete()
            messages.success(request, f"單位「{name}」已刪除。")
        except ProtectedError:
            messages.error(request, f"單位「{name}」仍被商品引用，無法刪除。")
        return redirect("catalog:unit_list")


# ── Product ───────────────────────────────────────────────────────────────────

class ProductListView(LoginRequiredMixin, View):
    template_name = "catalog/product_list.html"

    def get(self, request):
        qs = (
            Product.objects
            .select_related("category")
            .prefetch_related(
                Prefetch(
                    "product_units",
                    queryset=ProductUnit.objects.filter(status=ProductUnit.Status.ACTIVE).select_related("unit"),
                    to_attr="active_units",
                )
            )
        )
        q = request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(category__name__icontains=q))
        products, paging = _paginate(qs.order_by("id"), request)
        return render(request, self.template_name, {"products": products, "q": q, **paging})


class ProductCreateView(LoginRequiredMixin, View):
    template_name = "catalog/product_form.html"

    def get(self, request):
        return render(request, self.template_name, {"form": ProductForm(requesting_user=request.user), "action": "新增"})

    def post(self, request):
        form = ProductForm(request.POST, requesting_user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "商品新增成功。")
            return redirect("catalog:product_list")
        return render(request, self.template_name, {"form": form, "action": "新增"})


class ProductEditView(LoginRequiredMixin, View):
    template_name = "catalog/product_form.html"

    def get(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        form = ProductForm(instance=product, requesting_user=request.user)
        return render(request, self.template_name, {"form": form, "action": "編輯", "product": product})

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        form = ProductForm(request.POST, instance=product, requesting_user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "商品更新成功。")
            return redirect("catalog:product_list")
        return render(request, self.template_name, {"form": form, "action": "編輯", "product": product})


class ProductDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        name = product.name
        try:
            product.delete()
            messages.success(request, f"商品「{name}」已刪除。")
        except ProtectedError:
            messages.error(request, f"商品「{name}」仍被訂單或庫存引用，無法刪除。")
        return redirect("catalog:product_list")


# ── ProductUnit ───────────────────────────────────────────────────────────────

class ProductUnitListView(LoginRequiredMixin, View):
    template_name = "catalog/product_unit_list.html"

    def get(self, request, product_pk):
        product = get_object_or_404(Product, pk=product_pk)
        units = product.product_units.select_related("unit").order_by("unit_id")
        return render(request, self.template_name, {"product": product, "units": units})


class ProductUnitCreateView(LoginRequiredMixin, View):
    template_name = "catalog/product_unit_form.html"

    def get(self, request, product_pk):
        product = get_object_or_404(Product, pk=product_pk)
        form = ProductUnitForm(product=product)
        return render(request, self.template_name, {"form": form, "product": product})

    def post(self, request, product_pk):
        product = get_object_or_404(Product, pk=product_pk)
        form = ProductUnitForm(request.POST, product=product)
        if form.is_valid():
            form.save()
            messages.success(request, "定價已更新（舊定價已自動失效）。")
            return redirect("catalog:product_unit_list", product_pk=product.pk)
        return render(request, self.template_name, {"form": form, "product": product})


class ProductUnitDeactivateView(LoginRequiredMixin, View):
    def post(self, request, product_pk, pk):
        pu = get_object_or_404(ProductUnit, pk=pk, product_id=product_pk)
        pu.deactivate()
        messages.success(request, f"已失效「{pu.unit.name}」定價。")
        return redirect("catalog:product_unit_list", product_pk=product_pk)
