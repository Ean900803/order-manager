from django.contrib.auth import login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views import View
from .forms import LoginForm, EmployeeCreateForm, EmployeeEditForm, PasswordResetForm
from .models import Employee

PAGINATE_BY = 30


def _paginate(qs, request):
    try:
        page = max(1, int(request.GET.get("page", 1)))
    except ValueError:
        page = 1
    offset = (page - 1) * PAGINATE_BY
    rows = list(qs[offset : offset + PAGINATE_BY + 1])
    has_next = len(rows) > PAGINATE_BY
    return rows[:PAGINATE_BY], {"page": page, "has_previous": page > 1, "has_next": has_next, "previous_page": page - 1, "next_page": page + 1}


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


class EmployeeListView(LoginRequiredMixin, View):
    template_name = "accounts/employee_list.html"

    def get(self, request):
        employees, paging = _paginate(Employee.objects.all().order_by("name"), request)
        return render(request, self.template_name, {"employees": employees, **paging})


class EmployeeCreateView(LoginRequiredMixin, View):
    template_name = "accounts/employee_form.html"

    def get(self, request):
        form = EmployeeCreateForm()
        return render(request, self.template_name, {"form": form, "action": "新增"})

    def post(self, request):
        form = EmployeeCreateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "員工新增成功。")
            return redirect("accounts:employee_list")
        return render(request, self.template_name, {"form": form, "action": "新增"})


class EmployeeEditView(LoginRequiredMixin, View):
    template_name = "accounts/employee_form.html"

    def get(self, request, pk):
        employee = get_object_or_404(Employee, pk=pk)
        form = EmployeeEditForm(instance=employee)
        return render(request, self.template_name, {"form": form, "action": "編輯", "employee": employee})

    def post(self, request, pk):
        employee = get_object_or_404(Employee, pk=pk)
        form = EmployeeEditForm(request.POST, instance=employee)
        if form.is_valid():
            form.save()
            messages.success(request, "員工資料更新成功。")
            return redirect("accounts:employee_list")
        return render(request, self.template_name, {"form": form, "action": "編輯", "employee": employee})


class EmployeePasswordResetView(LoginRequiredMixin, View):
    template_name = "accounts/employee_password_reset.html"

    def get(self, request, pk):
        employee = get_object_or_404(Employee, pk=pk)
        form = PasswordResetForm(user=employee)
        return render(request, self.template_name, {"form": form, "employee": employee})

    def post(self, request, pk):
        employee = get_object_or_404(Employee, pk=pk)
        form = PasswordResetForm(user=employee, data=request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "密碼重設成功。")
            return redirect("accounts:employee_list")
        return render(request, self.template_name, {"form": form, "employee": employee})


class EmployeeResignView(LoginRequiredMixin, View):
    def post(self, request, pk):
        employee = get_object_or_404(Employee, pk=pk)
        if employee.pk == request.user.pk:
            messages.error(request, "不能讓自己離職。")
            return redirect("accounts:employee_list")
        employee.resigned_date = timezone.now()
        employee.save(update_fields=["resigned_date"])
        messages.success(request, f"已將 {employee.name} 設為離職。")
        return redirect("accounts:employee_list")


class EmployeeRestoreView(LoginRequiredMixin, View):
    def post(self, request, pk):
        employee = get_object_or_404(Employee, pk=pk)
        employee.resigned_date = None
        employee.save(update_fields=["resigned_date"])
        messages.success(request, f"已復職 {employee.name}。")
        return redirect("accounts:employee_list")
