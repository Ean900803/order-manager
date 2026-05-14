from django.urls import path, include

app_name = "catalog"

urlpatterns = [
    path("categories/", include("catalog.category_urls")),
    path("products/", include("catalog.product_urls")),
]
