from django.conf import settings
from django.db import models
from django.utils import timezone


class Unit(models.Model):
    name = models.CharField("單位名稱", max_length=10, unique=True)

    class Meta:
        verbose_name = "單位"
        verbose_name_plural = "單位"
        ordering = ["id"]

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField("分類名稱", max_length=20)
    deleted_at = models.DateTimeField("停用時間", null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="deleted_categories",
        verbose_name="停用者",
    )

    class Meta:
        verbose_name = "商品分類"
        verbose_name_plural = "商品分類"

    def __str__(self):
        return self.name

    @property
    def is_active(self):
        return self.deleted_at is None

    def disable(self, by=None):
        self.deleted_at = timezone.now()
        self.deleted_by = by
        self.save(update_fields=["deleted_at", "deleted_by"])

    def restore(self):
        self.deleted_at = None
        self.deleted_by = None
        self.save(update_fields=["deleted_at", "deleted_by"])


class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.PROTECT, verbose_name="分類")
    name = models.CharField("商品名稱", max_length=50)
    description = models.TextField("商品描述", blank=True)
    base_unit = models.ForeignKey(
        Unit, on_delete=models.PROTECT, related_name="base_for_products",
        verbose_name="基準單位",
    )
    created_at = models.DateTimeField("建立時間", auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_products",
        verbose_name="建立者",
    )
    deleted_at = models.DateTimeField("停用時間", null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="deleted_products",
        verbose_name="停用者",
    )

    class Meta:
        verbose_name = "商品"
        verbose_name_plural = "商品"
        indexes = [
            models.Index(fields=["category"], name="idx_product_category"),
            models.Index(fields=["deleted_at"], name="idx_product_deleted"),
        ]

    def __str__(self):
        return self.name

    @property
    def is_active(self):
        return self.deleted_at is None

    def disable(self, by=None):
        self.deleted_at = timezone.now()
        self.deleted_by = by
        self.save(update_fields=["deleted_at", "deleted_by"])

    def restore(self):
        self.deleted_at = None
        self.deleted_by = None
        self.save(update_fields=["deleted_at", "deleted_by"])

    def active_unit(self, unit):
        return self.product_units.filter(unit=unit, status=ProductUnit.Status.ACTIVE).first()


class ProductUnit(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "啟用中"
        INACTIVE = "inactive", "已失效"

    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="product_units", verbose_name="商品")
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name="product_units", verbose_name="單位")
    conversion_rate = models.PositiveIntegerField("換算比例", help_text="此單位 = 幾個基準單位")
    price = models.DecimalField("售價", max_digits=10, decimal_places=2)
    cost = models.DecimalField("成本", max_digits=10, decimal_places=2)
    status = models.CharField("狀態", max_length=10, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField("建立時間", auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_product_units",
        verbose_name="建立者",
    )

    class Meta:
        verbose_name = "商品單位定價"
        verbose_name_plural = "商品單位定價"
        indexes = [
            models.Index(fields=["product", "unit", "status"], name="idx_active_lookup"),
        ]
        ordering = ["product_id", "unit_id", "-created_at"]

    def __str__(self):
        return f"{self.product.name} / {self.unit.name} ({self.get_status_display()})"

    @property
    def is_active(self):
        return self.status == self.Status.ACTIVE

    def deactivate(self):
        self.status = self.Status.INACTIVE
        self.save(update_fields=["status"])
