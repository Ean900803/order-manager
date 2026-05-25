from django.conf import settings
from django.db import models

from catalog.models import Product, Unit


class Stock(models.Model):
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="stocks", verbose_name="商品")
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, verbose_name="進貨單位")
    quantity = models.PositiveIntegerField("進貨數量", help_text="以進貨單位計")
    quantity_remaining = models.IntegerField("剩餘基準單位數", help_text="可為負值表示超賣")
    unit_cost = models.DecimalField("基準單位成本", max_digits=10, decimal_places=2)
    restocked_date = models.DateField("進貨日期")
    restocked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="restocked_stocks",
        verbose_name="進貨人",
    )

    class Meta:
        verbose_name = "進貨批次"
        verbose_name_plural = "進貨批次"
        indexes = [
            models.Index(
                fields=["product", "restocked_date", "quantity_remaining"],
                name="idx_fifo_lookup",
            ),
        ]
        ordering = ["restocked_date", "id"]

    def __str__(self):
        return f"{self.product.name} 批次 #{self.pk} ({self.restocked_date})"
