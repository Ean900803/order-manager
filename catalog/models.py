from django.conf import settings
from django.db import models
from django.utils import timezone


class Category(models.Model):
    name = models.CharField("分類名稱", max_length=20)
    deleted_at = models.DateTimeField("停用時間", null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="created_categories", verbose_name="建立者")
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="updated_categories", verbose_name="更新者")
    deleted_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="deleted_categories", verbose_name="刪除者")

    class Meta:
        verbose_name = "商品分類"
        verbose_name_plural = "商品分類"

    def __str__(self):
        return self.name

    @property
    def is_active(self):
        return self.deleted_at is None

    def disable(self):
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at"])

    def restore(self):
        self.deleted_at = None
        self.save(update_fields=["deleted_at"])


class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.PROTECT, verbose_name="分類")
    name = models.CharField("商品名稱", max_length=50)
    description = models.TextField("商品描述", blank=True)
    price = models.DecimalField("售價", max_digits=10, decimal_places=2)
    cost = models.DecimalField("成本", max_digits=10, decimal_places=2)
    created_at = models.DateTimeField("建立時間", auto_now_add=True)
    deleted_at = models.DateTimeField("停用時間", null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="created_products", verbose_name="建立者")
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="updated_products", verbose_name="更新者")
    deleted_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="deleted_products", verbose_name="刪除者")

    class Meta:
        verbose_name = "商品"
        verbose_name_plural = "商品"

    def __str__(self):
        return self.name

    @property
    def is_active(self):
        return self.deleted_at is None

    def disable(self):
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at"])

    def restore(self):
        self.deleted_at = None
        self.save(update_fields=["deleted_at"])
