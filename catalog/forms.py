from django import forms
from .models import Category, Product


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name"]
        labels = {"name": "分類名稱"}


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["category", "name", "description", "price", "cost"]
        labels = {
            "category": "分類",
            "name": "商品名稱",
            "description": "商品描述",
            "price": "售價",
            "cost": "成本",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.filter(deleted_at__isnull=True)

    def clean_price(self):
        v = self.cleaned_data["price"]
        if v < 0:
            raise forms.ValidationError("售價不得小於 0。")
        return v

    def clean_cost(self):
        v = self.cleaned_data["cost"]
        if v < 0:
            raise forms.ValidationError("成本不得小於 0。")
        return v
