from django import forms
from django.contrib import admin
from .models import Employee


class EmployeeAdminForm(forms.ModelForm):
    password = forms.CharField(
        label="密碼",
        widget=forms.PasswordInput,
        required=False,
        help_text="編輯時留空則不變更",
    )

    class Meta:
        model = Employee
        fields = ["username", "name", "cellphone", "address", "lv", "resigned_date", "password"]


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    form = EmployeeAdminForm
    list_display = ["username", "name", "lv", "cellphone", "resigned_date"]
    list_filter = ["lv", "resigned_date"]
    search_fields = ["username", "name", "cellphone"]

    def save_model(self, request, obj, form, change):
        password = form.cleaned_data.get("password")
        if password:
            obj.set_password(password)
        elif not change:
            obj.set_unusable_password()
        super().save_model(request, obj, form, change)
