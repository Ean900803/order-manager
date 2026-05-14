from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
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
    queryset = Customer.objects.all().order_by("id")


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
