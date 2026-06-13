from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.db import models


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
        return self._create_user(username, password, **extra_fields)

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault("name", username)
        extra_fields.setdefault("cellphone", "0000000000")
        return self._create_user(username, password, **extra_fields)


class Employee(AbstractBaseUser):
    last_login = None
    id = models.AutoField(primary_key=True, db_column="eId")
    username = models.CharField("帳號", max_length=20, unique=True)
    name = models.CharField("姓名", max_length=20)
    cellphone = models.CharField("手機", max_length=10)
    address = models.CharField("地址", max_length=100, blank=True)
    resigned_date = models.DateTimeField("離職時間", null=True, blank=True)

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["name", "cellphone"]

    objects = EmployeeManager()

    class Meta:
        db_table = "employees"
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

    # 權限系統已移除：登入後即視為具備所有操作與後台權限
    @property
    def is_staff(self):
        return True

    def has_perm(self, perm, obj=None):
        return True

    def has_module_perms(self, app_label):
        return True
