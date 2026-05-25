from django.urls import path
from . import views

urlpatterns = [
    path("", views.UnitListView.as_view(), name="unit_list"),
    path("create/", views.UnitCreateView.as_view(), name="unit_create"),
    path("<int:pk>/edit/", views.UnitEditView.as_view(), name="unit_edit"),
    path("<int:pk>/delete/", views.UnitDeleteView.as_view(), name="unit_delete"),
]
