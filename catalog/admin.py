from django.contrib import admin
from .models import Category, Product


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "deleted_at"]
    list_filter = ["deleted_at"]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "category", "price", "cost", "deleted_at"]
    list_filter = ["category", "deleted_at"]
    search_fields = ["name"]
