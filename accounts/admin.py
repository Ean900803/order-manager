from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Employee


@admin.register(Employee)
class EmployeeAdmin(UserAdmin):
    list_display = ["username", "name", "lv", "cellphone", "resigned_date"]
    list_filter = ["lv", "resigned_date"]
    fieldsets = UserAdmin.fieldsets + (
        ("員工資料", {"fields": ("name", "cellphone", "address", "lv", "resigned_date")}),
    )
