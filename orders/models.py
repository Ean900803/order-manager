from decimal import Decimal
from django.conf import settings
from django.db import models
from django.utils import timezone

from customers.models import Customer
from catalog.models import Product


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "待確認"
        CONFIRMED = "confirmed", "已確認"
        COMPLETED = "completed", "已完成"
        CANCELLED = "cancelled", "已取消"

    id = models.AutoField(primary_key=True, db_column="oId")
    customer = models.ForeignKey(
        Customer, on_delete=models.PROTECT, db_column="custId", verbose_name="客戶",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        db_column="eId",
        related_name="created_orders",
        verbose_name="建立者",
    )
    ordered_date = models.DateTimeField("訂單日期", db_column="order_date", default=timezone.now)
    status = models.CharField("狀態", max_length=20, choices=Status.choices, default=Status.PENDING)

    class Meta:
        db_table = "orders"
        verbose_name = "訂單"
        verbose_name_plural = "訂單"
        ordering = ["-ordered_date"]
        indexes = [
            models.Index(fields=["customer"], name="idx_order_customer"),
            models.Index(fields=["ordered_date"], name="idx_order_date"),
        ]

    def __str__(self):
        return f"訂單 #{self.pk} - {self.customer.name}"

    @property
    def total(self):
        return sum(r.subtotal for r in self.records.all())

    def cancel(self):
        self.status = self.Status.CANCELLED
        self.save(update_fields=["status"])


class OrderRecord(models.Model):
    id = models.AutoField(primary_key=True, db_column="id")
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, db_column="oId",
        related_name="records", verbose_name="訂單",
    )
    product = models.ForeignKey(
        Product, on_delete=models.PROTECT, db_column="pId", verbose_name="商品",
    )
    price = models.DecimalField("成交單價", max_digits=10, decimal_places=2)
    cost = models.DecimalField("成交成本", max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField("數量")
    discount = models.DecimalField("折扣率", max_digits=5, decimal_places=2, default=Decimal("0"), help_text="0~1 之間")
    conversion_rate = models.PositiveIntegerField("成交換算比例", help_text="此單位 = 幾個基準單位")

    class Meta:
        db_table = "order_record"
        verbose_name = "訂單明細"
        verbose_name_plural = "訂單明細"
        indexes = [
            models.Index(fields=["order"], name="idx_record_order"),
            models.Index(fields=["product"], name="idx_record_product"),
        ]

    @property
    def subtotal(self):
        return self.price * self.quantity * (Decimal("1") - self.discount)

    @property
    def base_quantity(self):
        return self.quantity * self.conversion_rate
