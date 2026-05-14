from django import forms
from django.contrib.auth.forms import AuthenticationForm, SetPasswordForm
from .models import Employee, LV_ADMIN, LEVEL_CHOICES


class LoginForm(AuthenticationForm):
    username = forms.CharField(label="帳號")
    password = forms.CharField(label="密碼", widget=forms.PasswordInput)

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not user.is_active_employee:
            raise forms.ValidationError("此帳號已離職，無法登入。", code="resigned")


class EmployeeCreateForm(forms.ModelForm):
    password = forms.CharField(label="密碼", widget=forms.PasswordInput)

    class Meta:
        model = Employee
        fields = ["username", "name", "cellphone", "address", "lv", "password"]
        labels = {
            "username": "帳號",
            "name": "姓名",
            "cellphone": "手機",
            "address": "地址",
            "lv": "權限等級",
        }

    def __init__(self, *args, requesting_user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.requesting_user = requesting_user
        if requesting_user and not requesting_user.has_lv(LV_ADMIN):
            self.fields["lv"].disabled = True

    def clean_cellphone(self):
        v = self.cleaned_data["cellphone"]
        if not v.isdigit() or len(v) != 10:
            raise forms.ValidationError("手機號碼需為 10 位數字。")
        return v

    def clean_lv(self):
        v = self.cleaned_data["lv"]
        if not (1 <= v <= 9):
            raise forms.ValidationError("權限等級需介於 1 到 9。")
        return v

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


class EmployeeEditForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = ["name", "cellphone", "address", "lv"]
        labels = {
            "name": "姓名",
            "cellphone": "手機",
            "address": "地址",
            "lv": "權限等級",
        }

    def __init__(self, *args, requesting_user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.requesting_user = requesting_user
        if requesting_user and not requesting_user.has_lv(LV_ADMIN):
            self.fields["lv"].disabled = True

    def clean_cellphone(self):
        v = self.cleaned_data["cellphone"]
        if not v.isdigit() or len(v) != 10:
            raise forms.ValidationError("手機號碼需為 10 位數字。")
        return v


class PasswordResetForm(SetPasswordForm):
    new_password1 = forms.CharField(label="新密碼", widget=forms.PasswordInput)
    new_password2 = forms.CharField(label="確認新密碼", widget=forms.PasswordInput)
