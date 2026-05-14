from decimal import Decimal
from django.conf import settings
from django.db import models
from django.utils import timezone

from customers.models import Customer
from catalog.models import Product


class Order(models.Model):
    STATUS_PENDING = "pending"
    STATUS_CONFIRMED = "confirmed"
    STATUS_COMPLETED = "completed"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_PENDING, "待確認"),
        (STATUS_CONFIRMED, "已確認"),
        (STATUS_COMPLETED, "已完成"),
        (STATUS_CANCELLED, "已取消"),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, verbose_name="客戶")
    ordered_date = models.DateTimeField("訂單日期", default=timezone.now)
    status = models.CharField("狀態", max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    deleted_at = models.DateTimeField("刪除時間", null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="created_orders", verbose_name="建立者")
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="updated_orders", verbose_name="更新者")
    deleted_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="deleted_orders", verbose_name="刪除者")

    class Meta:
        verbose_name = "訂單"
        verbose_name_plural = "訂單"
        ordering = ["-ordered_date"]

    def __str__(self):
        return f"訂單 #{self.pk} - {self.customer.name}"

    @property
    def total(self):
        return sum(r.subtotal for r in self.records.filter(deleted_at__isnull=True))

    def cancel(self):
        self.status = self.STATUS_CANCELLED
        self.save(update_fields=["status"])


class OrderRecord(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="records", verbose_name="訂單")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, verbose_name="商品")
    quantity = models.PositiveIntegerField("數量")
    price = models.DecimalField("成交單價", max_digits=10, decimal_places=2)
    cost = models.DecimalField("成交成本", max_digits=10, decimal_places=2)
    discount = models.DecimalField("折扣 (%)", max_digits=5, decimal_places=2, default=Decimal("0"))
    created_at = models.DateTimeField("建立時間", auto_now_add=True)
    deleted_at = models.DateTimeField("刪除時間", null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="created_order_records", verbose_name="建立者")
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="updated_order_records", verbose_name="更新者")
    deleted_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="deleted_order_records", verbose_name="刪除者")

    class Meta:
        verbose_name = "訂單明細"
        verbose_name_plural = "訂單明細"

    @property
    def subtotal(self):
        return self.price * self.quantity * (1 - self.discount / 100)
