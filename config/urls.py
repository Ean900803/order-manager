from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", RedirectView.as_view(url="/orders/", permanent=False)),
    path("", include("accounts.urls")),
    path("", include("catalog.urls")),
    path("customers/", include("customers.urls")),
    path("orders/", include("orders.urls")),
]
