from django.db import models

from catalog.models import Product, Unit


class Stock(models.Model):
    id = models.AutoField(primary_key=True, db_column="sId")
    product = models.ForeignKey(
        Product, on_delete=models.PROTECT, db_column="pId",
        related_name="stocks", verbose_name="商品",
    )
    unit = models.ForeignKey(
        Unit, on_delete=models.PROTECT, db_column="uId", verbose_name="進貨單位",
    )
    quantity = models.PositiveIntegerField("進貨數量", help_text="以進貨單位計")
    quantity_remaining = models.IntegerField("剩餘基準單位數", help_text="可為負值表示超賣")
    unit_cost = models.DecimalField("基準單位成本", max_digits=10, decimal_places=2)

    class Meta:
        db_table = "stocks"
        verbose_name = "進貨批次"
        verbose_name_plural = "進貨批次"
        indexes = [
            models.Index(fields=["product", "id"], name="idx_fifo_lookup"),
        ]
        ordering = ["id"]

    def __str__(self):
        return f"{self.product.name} 批次 #{self.pk}"
