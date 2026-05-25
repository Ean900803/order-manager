from django.urls import path
from . import views

app_name = "orders"

urlpatterns = [
    path("", views.OrderListView.as_view(), name="list"),
    path("create/", views.OrderCreateView.as_view(), name="create"),
    path("<int:pk>/", views.OrderDetailView.as_view(), name="detail"),
    path("<int:pk>/edit/", views.OrderEditView.as_view(), name="edit"),
    path("<int:pk>/delete/", views.OrderDeleteView.as_view(), name="delete"),
    path("<int:pk>/status/", views.OrderStatusView.as_view(), name="status"),
    path("<int:pk>/cancel/", views.OrderCancelView.as_view(), name="cancel"),
    path("api/product/<int:pk>/units/", views.ProductUnitsApiView.as_view(), name="product_units_api"),
]
