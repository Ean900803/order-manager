from django.contrib.auth.models import AbstractUser
from django.db import models

LV_EMPLOYEE = 1
LV_SALES = 2
LV_MANAGER = 3
LV_ADMIN = 9

LEVEL_CHOICES = [
    (LV_EMPLOYEE, "員工"),
    (LV_SALES, "業務"),
    (LV_MANAGER, "主管"),
    (LV_ADMIN, "管理員"),
]


class Employee(AbstractUser):
    name = models.CharField("姓名", max_length=20)
    cellphone = models.CharField("手機", max_length=10)
    address = models.CharField("地址", max_length=100, blank=True)
    lv = models.PositiveSmallIntegerField("權限等級", choices=LEVEL_CHOICES, default=LV_EMPLOYEE)
    resigned_date = models.DateTimeField("離職時間", null=True, blank=True)

    # Disable unused AbstractUser fields
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    email = models.EmailField(blank=True)

    REQUIRED_FIELDS = ["name", "cellphone"]

    class Meta:
        verbose_name = "員工"
        verbose_name_plural = "員工"

    def __str__(self):
        return f"{self.name} ({self.username})"

    @property
    def is_active_employee(self):
        return self.resigned_date is None

    def has_lv(self, min_lv):
        return self.lv >= min_lv
