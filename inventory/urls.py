from django.urls import path
from . import views

app_name = "inventory"

urlpatterns = [
    path("stocks/", views.StockBatchListView.as_view(), name="stock_list"),
    path("stocks/create/", views.StockCreateView.as_view(), name="stock_create"),
    path("stocks/balance/", views.StockBalanceView.as_view(), name="stock_balance"),
]
