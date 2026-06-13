from django.contrib import admin

from .models import Stock


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ["id", "product", "unit", "quantity", "quantity_remaining", "unit_cost"]
    search_fields = ["product__name"]
