from django import forms
from .models import Customer


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ["name", "cellphone", "address", "note"]
        labels = {
            "name": "客戶姓名",
            "cellphone": "手機",
            "address": "地址",
            "note": "備註",
        }
