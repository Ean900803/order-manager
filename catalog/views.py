from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import Prefetch, Q
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import ListView

from .forms import CategoryForm, ProductForm, UnitForm, ProductUnitForm
from .models import Category, Product, Unit, ProductUnit
from accounts.models import LV_SALES, LV_ADMIN
from accounts.permissions import LevelRequiredMixin


# ── Category ─────────────────────────────────────────────────────────────────

class CategoryListView(LoginRequiredMixin, ListView):
    model = Category
    template_name = "catalog/category_list.html"
    context_object_name = "categories"
    queryset = Category.objects.all().order_by("id")


class CategoryCreateView(LoginRequiredMixin, LevelRequiredMixin, View):
    template_name = "catalog/category_form.html"
    min_lv = LV_SALES

    def get(self, request):
        return render(request, self.template_name, {"form": CategoryForm(), "action": "新增"})

    def post(self, request):
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "分類新增成功。")
            return redirect("catalog:category_list")
        return render(request, self.template_name, {"form": form, "action": "新增"})


class CategoryEditView(LoginRequiredMixin, LevelRequiredMixin, View):
    template_name = "catalog/category_form.html"
    min_lv = LV_SALES

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


class CategoryDisableView(LoginRequiredMixin, LevelRequiredMixin, View):
    min_lv = LV_SALES

    def post(self, request, pk):
        category = get_object_or_404(Category, pk=pk)
        category.disable(by=request.user)
        messages.success(request, f"分類「{category.name}」已停用。")
        return redirect("catalog:category_list")


class CategoryRestoreView(LoginRequiredMixin, LevelRequiredMixin, View):
    min_lv = LV_ADMIN

    def post(self, request, pk):
        category = get_object_or_404(Category, pk=pk)
        category.restore()
        messages.success(request, f"分類「{category.name}」已復原。")
        return redirect("catalog:category_list")


# ── Unit ──────────────────────────────────────────────────────────────────────

class UnitListView(LoginRequiredMixin, ListView):
    model = Unit
    template_name = "catalog/unit_list.html"
    context_object_name = "units"
    queryset = Unit.objects.all().order_by("id")


class UnitCreateView(LoginRequiredMixin, LevelRequiredMixin, View):
    template_name = "catalog/unit_form.html"
    min_lv = LV_SALES

    def get(self, request):
        return render(request, self.template_name, {"form": UnitForm(), "action": "新增"})

    def post(self, request):
        form = UnitForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "單位新增成功。")
            return redirect("catalog:unit_list")
        return render(request, self.template_name, {"form": form, "action": "新增"})


class UnitEditView(LoginRequiredMixin, LevelRequiredMixin, View):
    template_name = "catalog/unit_form.html"
    min_lv = LV_SALES

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


class UnitDeleteView(LoginRequiredMixin, LevelRequiredMixin, View):
    min_lv = LV_ADMIN

    def post(self, request, pk):
        unit = get_object_or_404(Unit, pk=pk)
        name = unit.name
        try:
            unit.delete()
            messages.success(request, f"單位「{name}」已刪除。")
        except Exception:
            messages.error(request, f"單位「{name}」仍被商品引用，無法刪除。")
        return redirect("catalog:unit_list")


# ── Product ───────────────────────────────────────────────────────────────────

class ProductListView(LoginRequiredMixin, ListView):
    model = Product
    template_name = "catalog/product_list.html"
    context_object_name = "products"
    paginate_by = 30

    def get_queryset(self):
        qs = (
            Product.objects
            .select_related("category", "base_unit")
            .prefetch_related(
                Prefetch(
                    "product_units",
                    queryset=ProductUnit.objects.filter(status=ProductUnit.Status.ACTIVE).select_related("unit"),
                    to_attr="active_units",
                )
            )
        )
        q = self.request.GET.get("q", "").strip()
        if q:
            # JOIN catalog_category, LIKE '%q%' OR LIKE '%q%'
            qs = qs.filter(
                Q(name__icontains=q) | Q(category__name__icontains=q)
            )
        return qs.order_by("id")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        ctx["sql"] = str(self.get_queryset().query)
        return ctx


class ProductCreateView(LoginRequiredMixin, LevelRequiredMixin, View):
    template_name = "catalog/product_form.html"
    min_lv = LV_SALES

    def get(self, request):
        return render(request, self.template_name, {"form": ProductForm(requesting_user=request.user), "action": "新增"})

    def post(self, request):
        form = ProductForm(request.POST, requesting_user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "商品新增成功。")
            return redirect("catalog:product_list")
        return render(request, self.template_name, {"form": form, "action": "新增"})


class ProductEditView(LoginRequiredMixin, LevelRequiredMixin, View):
    template_name = "catalog/product_form.html"
    min_lv = LV_SALES

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


class ProductDisableView(LoginRequiredMixin, LevelRequiredMixin, View):
    min_lv = LV_SALES

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        product.disable(by=request.user)
        messages.success(request, f"商品「{product.name}」已停用。")
        return redirect("catalog:product_list")


class ProductRestoreView(LoginRequiredMixin, LevelRequiredMixin, View):
    min_lv = LV_ADMIN

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        product.restore()
        messages.success(request, f"商品「{product.name}」已復原。")
        return redirect("catalog:product_list")


# ── ProductUnit ───────────────────────────────────────────────────────────────

class ProductUnitListView(LoginRequiredMixin, View):
    template_name = "catalog/product_unit_list.html"

    def get(self, request, product_pk):
        product = get_object_or_404(Product, pk=product_pk)
        units = product.product_units.select_related("unit", "created_by").order_by("unit_id", "-created_at")
        return render(request, self.template_name, {"product": product, "units": units})


class ProductUnitCreateView(LoginRequiredMixin, LevelRequiredMixin, View):
    template_name = "catalog/product_unit_form.html"
    min_lv = LV_SALES

    def get(self, request, product_pk):
        product = get_object_or_404(Product, pk=product_pk)
        form = ProductUnitForm(product=product, requesting_user=request.user)
        return render(request, self.template_name, {"form": form, "product": product})

    def post(self, request, product_pk):
        product = get_object_or_404(Product, pk=product_pk)
        form = ProductUnitForm(request.POST, product=product, requesting_user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "定價已更新（舊定價已自動失效）。")
            return redirect("catalog:product_unit_list", product_pk=product.pk)
        return render(request, self.template_name, {"form": form, "product": product})


class ProductUnitDeactivateView(LoginRequiredMixin, LevelRequiredMixin, View):
    min_lv = LV_SALES

    def post(self, request, product_pk, pk):
        pu = get_object_or_404(ProductUnit, pk=pk, product_id=product_pk)
        pu.deactivate()
        messages.success(request, f"已失效「{pu.unit.name}」定價。")
        return redirect("catalog:product_unit_list", product_pk=product_pk)
