from django.urls import path
from . import views

app_name = "customers"

urlpatterns = [
    path("", views.CustomerListView.as_view(), name="customer_list"),
    path("create/", views.CustomerCreateView.as_view(), name="customer_create"),
    path("<int:pk>/edit/", views.CustomerEditView.as_view(), name="customer_edit"),
]
