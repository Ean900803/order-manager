from django.contrib import admin
from .models import Order, OrderRecord


class OrderRecordInline(admin.TabularInline):
    model = OrderRecord
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["id", "customer", "status", "ordered_date"]
    list_filter = ["status"]
    inlines = [OrderRecordInline]
