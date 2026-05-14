from django.conf import settings
from django.db import models


class Customer(models.Model):
    name = models.CharField("客戶姓名", max_length=20)
    cellphone = models.CharField("手機", max_length=10, blank=True)
    address = models.CharField("地址", max_length=100, blank=True)
    note = models.TextField("備註", blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="created_customers", verbose_name="建立者")
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="updated_customers", verbose_name="更新者")

    class Meta:
        verbose_name = "客戶"
        verbose_name_plural = "客戶"

    def __str__(self):
        return self.name
