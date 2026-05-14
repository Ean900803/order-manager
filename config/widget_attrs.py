"""
在 AppConfig.ready() 或 settings.py import 後執行，
為 Django 預設 Widget 加上 Bootstrap 5 class。
"""
from django import forms


def apply_bootstrap_widgets():
    for widget_cls, css_class in [
        (forms.TextInput,       "form-control"),
        (forms.NumberInput,     "form-control"),
        (forms.EmailInput,      "form-control"),
        (forms.URLInput,        "form-control"),
        (forms.PasswordInput,   "form-control"),
        (forms.Textarea,        "form-control"),
        (forms.DateInput,       "form-control"),
        (forms.DateTimeInput,   "form-control"),
        (forms.Select,          "form-select"),
        (forms.SelectMultiple,  "form-select"),
        (forms.CheckboxInput,   "form-check-input"),
    ]:
        if "class" not in (widget_cls.attrs if hasattr(widget_cls, "attrs") else {}):
            original_init = widget_cls.__init__

            def make_init(cls_css):
                def __init__(self, attrs=None, **kwargs):
                    if attrs is None:
                        attrs = {}
                    attrs.setdefault("class", cls_css)
                    original_init(self, attrs=attrs, **kwargs)
                return __init__

            widget_cls.__init__ = make_init(css_class)
