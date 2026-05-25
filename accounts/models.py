from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
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


class EmployeeManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, username, password, **extra_fields):
        if not username:
            raise ValueError("username 必填")
        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, username, password=None, **extra_fields):
        extra_fields.setdefault("lv", LV_EMPLOYEE)
        return self._create_user(username, password, **extra_fields)

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields["lv"] = LV_ADMIN
        extra_fields.setdefault("name", username)
        extra_fields.setdefault("cellphone", "0000000000")
        return self._create_user(username, password, **extra_fields)


class Employee(AbstractBaseUser):
    username = models.CharField("帳號", max_length=20, unique=True)
    name = models.CharField("姓名", max_length=20)
    cellphone = models.CharField("手機", max_length=10)
    address = models.CharField("地址", max_length=100, blank=True)
    lv = models.PositiveSmallIntegerField("權限等級", choices=LEVEL_CHOICES, default=LV_EMPLOYEE)
    resigned_date = models.DateTimeField("離職時間", null=True, blank=True)

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["name", "cellphone"]

    objects = EmployeeManager()

    class Meta:
        verbose_name = "員工"
        verbose_name_plural = "員工"
        indexes = [
            models.Index(fields=["resigned_date"], name="idx_resigned"),
        ]

    def __str__(self):
        return f"{self.name} ({self.username})"

    @property
    def is_active(self):
        return self.resigned_date is None

    @property
    def is_active_employee(self):
        return self.resigned_date is None

    @property
    def is_staff(self):
        return self.lv >= LV_ADMIN

    def has_lv(self, min_lv):
        return self.lv >= min_lv

    def has_perm(self, perm, obj=None):
        return self.lv >= LV_ADMIN

    def has_module_perms(self, app_label):
        return self.lv >= LV_ADMIN
