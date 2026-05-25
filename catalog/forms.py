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
    """建立 / 編輯商品。建立時同時建一筆基準單位 ProductUnit。"""

    base_unit = forms.ModelChoiceField(
        label="基準單位",
        queryset=Unit.objects.all().order_by("id"),
        empty_label="--- 請選擇單位 ---",
    )
    base_price = forms.DecimalField(label="售價（基準單位）", max_digits=10, decimal_places=2, min_value=Decimal("0"))
    base_cost = forms.DecimalField(label="成本（基準單位）", max_digits=10, decimal_places=2, min_value=Decimal("0"))

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
        self.fields["category"].queryset = Category.objects.filter(deleted_at__isnull=True).order_by("id")
        if self.instance.pk:
            self.fields["base_unit"].disabled = True
            self.fields["base_unit"].initial = self.instance.base_unit_id
            active = self.instance.active_unit(self.instance.base_unit)
            if active:
                self.fields["base_price"].initial = active.price
                self.fields["base_cost"].initial = active.cost
                self.fields["base_price"].help_text = "若改價將失效當前 ProductUnit 並建立新筆。"
                self.fields["base_cost"].help_text = "同上。"

    @transaction.atomic
    def save(self, commit=True):
        is_create = self.instance.pk is None
        base_unit = self.cleaned_data["base_unit"]
        base_price = self.cleaned_data["base_price"]
        base_cost = self.cleaned_data["base_cost"]

        if is_create:
            self.instance.base_unit = base_unit
            self.instance.created_by = self.requesting_user

        product = super().save(commit=commit)

        if commit:
            current = product.active_unit(base_unit) if not is_create else None
            need_new = is_create or current is None or current.price != base_price or current.cost != base_cost
            if need_new:
                if current:
                    current.deactivate()
                ProductUnit.objects.create(
                    product=product,
                    unit=base_unit,
                    conversion_rate=1,
                    price=base_price,
                    cost=base_cost,
                    status=ProductUnit.Status.ACTIVE,
                    created_by=self.requesting_user,
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

    def __init__(self, *args, product=None, requesting_user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.product = product
        self.requesting_user = requesting_user
        self.fields["unit"].queryset = Unit.objects.all().order_by("id")
        if product:
            self.fields["unit"].help_text = f"基準單位為「{product.base_unit.name}」"

    def clean(self):
        cleaned = super().clean()
        unit = cleaned.get("unit")
        rate = cleaned.get("conversion_rate")
        if unit and self.product and unit == self.product.base_unit and rate not in (None, 1):
            self.add_error("conversion_rate", "基準單位的換算比例必須為 1。")
        return cleaned

    @transaction.atomic
    def save(self, commit=True):
        self.instance.product = self.product
        self.instance.created_by = self.requesting_user
        self.instance.status = ProductUnit.Status.ACTIVE
        unit = self.cleaned_data["unit"]
        current = self.product.active_unit(unit)
        if current:
            current.deactivate()
        return super().save(commit=commit)
