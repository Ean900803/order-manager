from django.conf import settings
from django.db import models


class Unit(models.Model):
    id = models.AutoField(primary_key=True, db_column="uId")
    name = models.CharField("單位名稱", max_length=10, unique=True)

    class Meta:
        db_table = "units"
        verbose_name = "單位"
        verbose_name_plural = "單位"
        ordering = ["id"]

    def __str__(self):
        return self.name


class Category(models.Model):
    id = models.AutoField(primary_key=True, db_column="catId")
    name = models.CharField("分類名稱", max_length=20)

    class Meta:
        db_table = "categories"
        verbose_name = "商品分類"
        verbose_name_plural = "商品分類"
        ordering = ["id"]

    def __str__(self):
        return self.name


class Product(models.Model):
    id = models.AutoField(primary_key=True, db_column="pId")
    name = models.CharField("商品名稱", max_length=50)
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, db_column="catId", verbose_name="分類",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        db_column="eId",
        related_name="created_products",
        verbose_name="建立者",
    )
    description = models.TextField("商品描述", blank=True)

    class Meta:
        db_table = "products"
        verbose_name = "商品"
        verbose_name_plural = "商品"
        ordering = ["id"]
        indexes = [
            models.Index(fields=["category"], name="idx_product_category"),
        ]

    def __str__(self):
        return self.name

    def active_unit(self, unit):
        return self.product_units.filter(unit=unit, status=ProductUnit.Status.ACTIVE).first()


class ProductUnit(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "啟用中"
        INACTIVE = "inactive", "已失效"

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, db_column="pId",
        related_name="product_units", verbose_name="商品",
    )
    unit = models.ForeignKey(
        Unit, on_delete=models.PROTECT, db_column="uId",
        related_name="product_units", verbose_name="單位",
    )
    conversion_rate = models.PositiveIntegerField("換算比例", help_text="此單位 = 幾個基準單位")
    price = models.DecimalField("售價", max_digits=10, decimal_places=2)
    cost = models.DecimalField("成本", max_digits=10, decimal_places=2)
    status = models.CharField("狀態", max_length=10, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        db_table = "product_unit"
        verbose_name = "商品單位定價"
        verbose_name_plural = "商品單位定價"
        indexes = [
            models.Index(fields=["product", "unit", "status"], name="idx_active_lookup"),
        ]
        ordering = ["product_id", "unit_id"]

    def __str__(self):
        return f"{self.product.name} / {self.unit.name} ({self.get_status_display()})"

    @property
    def is_active(self):
        return self.status == self.Status.ACTIVE

    def deactivate(self):
        self.status = self.Status.INACTIVE
        self.save(update_fields=["status"])
