from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import ListView

from .forms import CategoryForm, ProductForm
from .models import Category, Product
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
        category.disable()
        messages.success(request, f"分類「{category.name}」已停用。")
        return redirect("catalog:category_list")


class CategoryRestoreView(LoginRequiredMixin, LevelRequiredMixin, View):
    min_lv = LV_ADMIN

    def post(self, request, pk):
        category = get_object_or_404(Category, pk=pk)
        category.restore()
        messages.success(request, f"分類「{category.name}」已復原。")
        return redirect("catalog:category_list")


# ── Product ───────────────────────────────────────────────────────────────────

class ProductListView(LoginRequiredMixin, ListView):
    model = Product
    template_name = "catalog/product_list.html"
    context_object_name = "products"
    queryset = Product.objects.select_related("category").order_by("id")


class ProductCreateView(LoginRequiredMixin, LevelRequiredMixin, View):
    template_name = "catalog/product_form.html"
    min_lv = LV_SALES

    def get(self, request):
        return render(request, self.template_name, {"form": ProductForm(), "action": "新增"})

    def post(self, request):
        form = ProductForm(request.POST)
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
        return render(request, self.template_name, {"form": ProductForm(instance=product), "action": "編輯", "product": product})

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, "商品更新成功。")
            return redirect("catalog:product_list")
        return render(request, self.template_name, {"form": form, "action": "編輯", "product": product})


class ProductDisableView(LoginRequiredMixin, LevelRequiredMixin, View):
    min_lv = LV_SALES

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        product.disable()
        messages.success(request, f"商品「{product.name}」已停用。")
        return redirect("catalog:product_list")


class ProductRestoreView(LoginRequiredMixin, LevelRequiredMixin, View):
    min_lv = LV_ADMIN

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        product.restore()
        messages.success(request, f"商品「{product.name}」已復原。")
        return redirect("catalog:product_list")
