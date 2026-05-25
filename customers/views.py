from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import ListView

from .forms import CustomerForm
from .models import Customer
from accounts.models import LV_SALES
from accounts.permissions import LevelRequiredMixin


class CustomerListView(LoginRequiredMixin, ListView):
    model = Customer
    template_name = "customers/customer_list.html"
    context_object_name = "customers"
    paginate_by = 30

    def get_queryset(self):
        qs = Customer.objects.all()
        q = self.request.GET.get("q", "").strip()
        if q:
            # LIKE '%q%' OR LIKE '%q%' （無 JOIN，純 customers 表）
            qs = qs.filter(Q(name__icontains=q) | Q(cellphone__icontains=q))
        return qs.order_by("id")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        ctx["sql"] = str(self.get_queryset().query)
        return ctx


class CustomerCreateView(LoginRequiredMixin, LevelRequiredMixin, View):
    template_name = "customers/customer_form.html"
    min_lv = LV_SALES

    def get(self, request):
        return render(request, self.template_name, {"form": CustomerForm(), "action": "新增"})

    def post(self, request):
        form = CustomerForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "客戶新增成功。")
            return redirect("customers:customer_list")
        return render(request, self.template_name, {"form": form, "action": "新增"})


class CustomerEditView(LoginRequiredMixin, LevelRequiredMixin, View):
    template_name = "customers/customer_form.html"
    min_lv = LV_SALES

    def get(self, request, pk):
        customer = get_object_or_404(Customer, pk=pk)
        return render(request, self.template_name, {"form": CustomerForm(instance=customer), "action": "編輯", "customer": customer})

    def post(self, request, pk):
        customer = get_object_or_404(Customer, pk=pk)
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            form.save()
            messages.success(request, "客戶資料更新成功。")
            return redirect("customers:customer_list")
        return render(request, self.template_name, {"form": form, "action": "編輯", "customer": customer})


class CustomerDeleteView(LoginRequiredMixin, LevelRequiredMixin, View):
    min_lv = LV_SALES

    def post(self, request, pk):
        customer = get_object_or_404(Customer, pk=pk)
        name = customer.name
        try:
            customer.delete()
            messages.success(request, f"客戶「{name}」已刪除。")
        except ProtectedError:
            messages.error(request, f"客戶「{name}」有關聯訂單，無法刪除。請先刪除相關訂單。")
        return redirect("customers:customer_list")
