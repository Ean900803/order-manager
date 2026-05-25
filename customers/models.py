from django.db import models


class Customer(models.Model):
    name = models.CharField("客戶姓名", max_length=20)
    cellphone = models.CharField("手機", max_length=10, blank=True)
    address = models.CharField("地址", max_length=100, blank=True)
    note = models.TextField("備註", blank=True)

    class Meta:
        verbose_name = "客戶"
        verbose_name_plural = "客戶"

    def __str__(self):
        return self.name
