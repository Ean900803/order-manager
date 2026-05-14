from django import forms
from django.forms import inlineformset_factory

from .models import Order, OrderRecord
from customers.models import Customer
from catalog.models import Product


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ["customer", "ordered_date"]
        labels = {
            "customer": "客戶",
            "ordered_date": "訂單日期",
        }
        widgets = {
            "ordered_date": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["customer"].queryset = Customer.objects.all().order_by("name")
        if self.instance.pk:
            self.fields["ordered_date"].initial = self.instance.ordered_date.strftime("%Y-%m-%dT%H:%M")


class OrderStatusForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ["status"]
        labels = {"status": "訂單狀態"}


class OrderRecordForm(forms.ModelForm):
    class Meta:
        model = OrderRecord
        fields = ["product", "quantity", "discount"]
        labels = {
            "product": "商品",
            "quantity": "數量",
            "discount": "折扣 (%)",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["product"].queryset = Product.objects.filter(
            deleted_at__isnull=True
        ).select_related("category")
        self.fields["product"].empty_label = "--- 請選擇商品 ---"

    def clean_quantity(self):
        v = self.cleaned_data.get("quantity")
        if v is not None and v < 1:
            raise forms.ValidationError("數量需大於等於 1。")
        return v

    def clean_discount(self):
        v = self.cleaned_data.get("discount")
        if v is not None and not (0 <= v <= 100):
            raise forms.ValidationError("折扣需介於 0 到 100。")
        return v


OrderRecordFormSet = inlineformset_factory(
    Order,
    OrderRecord,
    form=OrderRecordForm,
    fields=["product", "quantity", "discount"],
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True,
)
