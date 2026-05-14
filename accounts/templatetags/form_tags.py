from django import template
from django.forms import BoundField

register = template.Library()


@register.filter(name="bs5")
def add_bootstrap_class(field: BoundField):
    """為 BoundField 的 widget 加上 Bootstrap 5 class，回傳原 field 供後續繼續渲染。"""
    widget = field.field.widget
    widget_class = widget.__class__.__name__

    if widget_class in ("CheckboxInput",):
        css = "form-check-input"
    elif widget_class in ("Select", "SelectMultiple"):
        css = "form-select"
    else:
        css = "form-control"

    if field.errors:
        css += " is-invalid"

    attrs = widget.attrs.copy()
    existing = attrs.get("class", "")
    if css not in existing:
        attrs["class"] = f"{existing} {css}".strip()
    widget.attrs = attrs
    return field


@register.inclusion_tag("_field.html")
def field(bound_field, label=None, required=None):
    """
    Usage: {% field form.username %}
    Renders a Bootstrap 5 form-group div with label, input, and error message.
    """
    return {
        "field": bound_field,
        "label": label or bound_field.label,
        "required": required if required is not None else bound_field.field.required,
    }
