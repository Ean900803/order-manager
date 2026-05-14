from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from .models import LV_EMPLOYEE


def level_required(min_lv):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect("accounts:login")
            if not request.user.has_lv(min_lv):
                messages.error(request, "您的權限不足以執行此操作。")
                return redirect("orders:list")
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


class LevelRequiredMixin:
    min_lv = LV_EMPLOYEE

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("accounts:login")
        if not request.user.has_lv(self.min_lv):
            messages.error(request, "您的權限不足以執行此操作。")
            return redirect("orders:list")
        return super().dispatch(request, *args, **kwargs)
