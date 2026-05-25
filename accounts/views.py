from django.contrib.auth import login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views import View
from django.views.generic import ListView

from .forms import LoginForm, EmployeeCreateForm, EmployeeEditForm, PasswordResetForm
from .models import Employee, LV_ADMIN
from .permissions import LevelRequiredMixin


class LoginView(View):
    template_name = "accounts/login.html"

    def get(self, request):
        if request.user.is_authenticated:
            return redirect("orders:list")
        return render(request, self.template_name, {"form": LoginForm()})

    def post(self, request):
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect(request.GET.get("next", "orders:list"))
        return render(request, self.template_name, {"form": form})


class LogoutView(View):
    def post(self, request):
        logout(request)
        return redirect("accounts:login")


class EmployeeListView(LoginRequiredMixin, LevelRequiredMixin, ListView):
    model = Employee
    template_name = "accounts/employee_list.html"
    context_object_name = "employees"
    min_lv = 1

    def get_queryset(self):
        qs = Employee.objects.all().order_by("lv", "name")
        if not self.request.user.has_lv(LV_ADMIN):
            qs = qs.filter(resigned_date__isnull=True)
        return qs


class EmployeeCreateView(LoginRequiredMixin, LevelRequiredMixin, View):
    template_name = "accounts/employee_form.html"
    min_lv = LV_ADMIN

    def get(self, request):
        form = EmployeeCreateForm(requesting_user=request.user)
        return render(request, self.template_name, {"form": form, "action": "新增"})

    def post(self, request):
        form = EmployeeCreateForm(request.POST, requesting_user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "員工新增成功。")
            return redirect("accounts:employee_list")
        return render(request, self.template_name, {"form": form, "action": "新增"})


class EmployeeEditView(LoginRequiredMixin, View):
    template_name = "accounts/employee_form.html"

    def _can_edit(self, request, employee):
        return request.user.has_lv(LV_ADMIN) or request.user.pk == employee.pk

    def get(self, request, pk):
        employee = get_object_or_404(Employee, pk=pk)
        if not self._can_edit(request, employee):
            messages.error(request, "您無權編輯此員工資料。")
            return redirect("accounts:employee_list")
        form = EmployeeEditForm(instance=employee, requesting_user=request.user)
        return render(request, self.template_name, {"form": form, "action": "編輯", "employee": employee})

    def post(self, request, pk):
        employee = get_object_or_404(Employee, pk=pk)
        if not self._can_edit(request, employee):
            messages.error(request, "您無權編輯此員工資料。")
            return redirect("accounts:employee_list")
        form = EmployeeEditForm(request.POST, instance=employee, requesting_user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "員工資料更新成功。")
            return redirect("accounts:employee_list")
        return render(request, self.template_name, {"form": form, "action": "編輯", "employee": employee})


class EmployeePasswordResetView(LoginRequiredMixin, View):
    template_name = "accounts/employee_password_reset.html"

    def _can_reset(self, request, employee):
        return request.user.has_lv(LV_ADMIN) or request.user.pk == employee.pk

    def get(self, request, pk):
        employee = get_object_or_404(Employee, pk=pk)
        if not self._can_reset(request, employee):
            messages.error(request, "您無權重設此員工密碼。")
            return redirect("accounts:employee_list")
        form = PasswordResetForm(user=employee)
        return render(request, self.template_name, {"form": form, "employee": employee})

    def post(self, request, pk):
        employee = get_object_or_404(Employee, pk=pk)
        if not self._can_reset(request, employee):
            messages.error(request, "您無權重設此員工密碼。")
            return redirect("accounts:employee_list")
        form = PasswordResetForm(user=employee, data=request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "密碼重設成功。")
            return redirect("accounts:employee_list")
        return render(request, self.template_name, {"form": form, "employee": employee})


class EmployeeResignView(LoginRequiredMixin, LevelRequiredMixin, View):
    min_lv = LV_ADMIN

    def post(self, request, pk):
        employee = get_object_or_404(Employee, pk=pk)
        if employee.pk == request.user.pk:
            messages.error(request, "不能讓自己離職。")
            return redirect("accounts:employee_list")
        employee.resigned_date = timezone.now()
        employee.save(update_fields=["resigned_date"])
        messages.success(request, f"已將 {employee.name} 設為離職。")
        return redirect("accounts:employee_list")


class EmployeeRestoreView(LoginRequiredMixin, LevelRequiredMixin, View):
    min_lv = LV_ADMIN

    def post(self, request, pk):
        employee = get_object_or_404(Employee, pk=pk)
        employee.resigned_date = None
        employee.save(update_fields=["resigned_date"])
        messages.success(request, f"已復職 {employee.name}。")
        return redirect("accounts:employee_list")
