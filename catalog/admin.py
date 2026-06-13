from django.contrib import admin
from .models import Category, Product, Unit, ProductUnit


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ["id", "name"]
    search_fields = ["name"]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["id", "name"]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "category"]
    list_filter = ["category"]
    search_fields = ["name"]


@admin.register(ProductUnit)
class ProductUnitAdmin(admin.ModelAdmin):
    list_display = ["id", "product", "unit", "conversion_rate", "price", "cost", "status"]
    list_filter = ["status"]
    search_fields = ["product__name", "unit__name"]
