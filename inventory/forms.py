from decimal import Decimal
from django import forms

from catalog.models import Product, ProductUnit, Unit
from .models import Stock


class StockCreateForm(forms.ModelForm):
    """進貨表單。

    使用者填：商品、進貨單位、進貨數量、基準單位成本、進貨日期。
    save 時自動：quantity_remaining = quantity × conversion_rate（從 ProductUnit 取）。
    """

    class Meta:
        model = Stock
        fields = ["product", "unit", "quantity", "unit_cost", "restocked_date"]
        labels = {
            "product": "商品",
            "unit": "進貨單位",
            "quantity": "進貨數量",
            "unit_cost": "基準單位成本",
            "restocked_date": "進貨日期",
        }
        widgets = {
            "restocked_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, requesting_user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.requesting_user = requesting_user
        self.fields["product"].queryset = Product.objects.filter(deleted_at__isnull=True).order_by("id")
        self.fields["unit"].queryset = Unit.objects.all().order_by("id")
        self.fields["unit_cost"].min_value = Decimal("0")

    def clean(self):
        cleaned = super().clean()
        product = cleaned.get("product")
        unit = cleaned.get("unit")
        if product and unit:
            pu = ProductUnit.objects.filter(
                product=product, unit=unit, status=ProductUnit.Status.ACTIVE
            ).first()
            if not pu:
                self.add_error("unit", "此商品該單位目前沒有啟用的定價，無法進貨。")
            else:
                cleaned["_conversion_rate"] = pu.conversion_rate
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.restocked_by = self.requesting_user
        instance.quantity_remaining = self.cleaned_data["quantity"] * self.cleaned_data["_conversion_rate"]
        if commit:
            instance.save()
        return instance
