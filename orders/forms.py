from decimal import Decimal
from django import forms

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


class NewRecordForm(forms.Form):
    """訂單明細「新增列」用的 form。

    note: 明細不可編輯既有內容；只能新增整筆或軟刪除整筆。
    price / cost / conversion_rate 由後端從 ProductUnit(status=active) 鎖定，不接受表單傳值。
    """

    product = forms.ModelChoiceField(
        label="商品",
        queryset=Product.objects.none(),
        empty_label="--- 請選擇商品 ---",
    )
    unit = forms.IntegerField(label="單位", widget=forms.Select())
    quantity = forms.IntegerField(label="數量", min_value=1)
    discount_pct = forms.DecimalField(
        label="折扣 (%)",
        max_digits=5, decimal_places=2,
        min_value=Decimal("0"), max_value=Decimal("100"),
        initial=Decimal("0"),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["product"].queryset = Product.objects.all().select_related("category")

    @property
    def discount_ratio(self):
        return (self.cleaned_data["discount_pct"] / Decimal("100")).quantize(Decimal("0.01"))
