from django.urls import path
from . import views

urlpatterns = [
    path("", views.ProductListView.as_view(), name="product_list"),
    path("create/", views.ProductCreateView.as_view(), name="product_create"),
    path("<int:pk>/edit/", views.ProductEditView.as_view(), name="product_edit"),
    path("<int:pk>/disable/", views.ProductDisableView.as_view(), name="product_disable"),
    path("<int:pk>/restore/", views.ProductRestoreView.as_view(), name="product_restore"),
    path("<int:product_pk>/units/", views.ProductUnitListView.as_view(), name="product_unit_list"),
    path("<int:product_pk>/units/create/", views.ProductUnitCreateView.as_view(), name="product_unit_create"),
    path("<int:product_pk>/units/<int:pk>/deactivate/", views.ProductUnitDeactivateView.as_view(), name="product_unit_deactivate"),
]
