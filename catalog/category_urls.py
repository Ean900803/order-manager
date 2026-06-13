from django.urls import path
from . import views

urlpatterns = [
    path("", views.CategoryListView.as_view(), name="category_list"),
    path("create/", views.CategoryCreateView.as_view(), name="category_create"),
    path("<int:pk>/edit/", views.CategoryEditView.as_view(), name="category_edit"),
    path("<int:pk>/delete/", views.CategoryDeleteView.as_view(), name="category_delete"),
]
