from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View

from .forms import CustomerForm
from .models import Customer


class CustomerListView(LoginRequiredMixin, View):
    template_name = "customers/customer_list.html"
    paginate_by = 30

    def get(self, request):
        qs = Customer.objects.all()
        q = request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(cellphone__icontains=q))
        qs = qs.order_by("id")

        try:
            page = max(1, int(request.GET.get("page", 1)))
        except ValueError:
            page = 1

        offset = (page - 1) * self.paginate_by
        rows = list(qs[offset : offset + self.paginate_by + 1])
        has_next = len(rows) > self.paginate_by
        customers = rows[: self.paginate_by]

        return render(request, self.template_name, {
            "customers": customers,
            "q": q,
            "page": page,
            "has_previous": page > 1,
            "has_next": has_next,
            "previous_page": page - 1,
            "next_page": page + 1,
        })


class CustomerCreateView(LoginRequiredMixin, View):
    template_name = "customers/customer_form.html"

    def get(self, request):
        return render(request, self.template_name, {"form": CustomerForm(), "action": "新增"})

    def post(self, request):
        form = CustomerForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "客戶新增成功。")
            return redirect("customers:customer_list")
        return render(request, self.template_name, {"form": form, "action": "新增"})


class CustomerEditView(LoginRequiredMixin, View):
    template_name = "customers/customer_form.html"

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


class CustomerDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        customer = get_object_or_404(Customer, pk=pk)
        name = customer.name
        try:
            customer.delete()
            messages.success(request, f"客戶「{name}」已刪除。")
        except ProtectedError:
            messages.error(request, f"客戶「{name}」有關聯訂單，無法刪除。請先刪除相關訂單。")
        return redirect("customers:customer_list")
