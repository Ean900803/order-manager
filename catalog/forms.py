from decimal import Decimal
from django import forms
from django.db import transaction

from .models import Category, Product, Unit, ProductUnit


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name"]
        labels = {"name": "分類名稱"}


class UnitForm(forms.ModelForm):
    class Meta:
        model = Unit
        fields = ["name"]
        labels = {"name": "單位名稱"}


class ProductForm(forms.ModelForm):
    """建立 / 編輯商品。建立時可一併建立第一筆單位定價（換算比例固定為 1）。"""

    unit = forms.ModelChoiceField(
        label="單位",
        queryset=Unit.objects.all().order_by("id"),
        empty_label="--- 請選擇單位 ---",
        required=False,
    )
    price = forms.DecimalField(label="售價", max_digits=10, decimal_places=2, min_value=Decimal("0"), required=False)
    cost = forms.DecimalField(label="成本", max_digits=10, decimal_places=2, min_value=Decimal("0"), required=False)

    class Meta:
        model = Product
        fields = ["category", "name", "description"]
        labels = {
            "category": "分類",
            "name": "商品名稱",
            "description": "商品描述",
        }

    def __init__(self, *args, requesting_user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.requesting_user = requesting_user
        self.fields["category"].queryset = Category.objects.all().order_by("id")
        if self.instance.pk:
            # 編輯時不在此處改定價，請至「單位定價」管理
            del self.fields["unit"]
            del self.fields["price"]
            del self.fields["cost"]

    def clean(self):
        cleaned = super().clean()
        if not self.instance.pk:
            unit = cleaned.get("unit")
            price = cleaned.get("price")
            cost = cleaned.get("cost")
            if not (unit and price is not None and cost is not None):
                raise forms.ValidationError("建立商品時需填寫單位、售價與成本。")
        return cleaned

    @transaction.atomic
    def save(self, commit=True):
        is_create = self.instance.pk is None
        if is_create:
            self.instance.created_by = self.requesting_user
        product = super().save(commit=commit)
        if commit and is_create:
            ProductUnit.objects.create(
                product=product,
                unit=self.cleaned_data["unit"],
                conversion_rate=1,
                price=self.cleaned_data["price"],
                cost=self.cleaned_data["cost"],
                status=ProductUnit.Status.ACTIVE,
            )
        return product


class ProductUnitForm(forms.ModelForm):
    """為現有商品新增 / 替換某單位的定價。"""

    class Meta:
        model = ProductUnit
        fields = ["unit", "conversion_rate", "price", "cost"]
        labels = {
            "unit": "單位",
            "conversion_rate": "換算比例（= 幾個基準單位）",
            "price": "售價",
            "cost": "成本",
        }

    def __init__(self, *args, product=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.product = product
        self.fields["unit"].queryset = Unit.objects.all().order_by("id")

    @transaction.atomic
    def save(self, commit=True):
        self.instance.product = self.product
        self.instance.status = ProductUnit.Status.ACTIVE
        unit = self.cleaned_data["unit"]
        current = self.product.active_unit(unit)
        if current:
            current.deactivate()
        return super().save(commit=commit)
