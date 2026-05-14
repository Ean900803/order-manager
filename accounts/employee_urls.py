from django.urls import path
from . import views

urlpatterns = [
    path("", views.EmployeeListView.as_view(), name="employee_list"),
    path("create/", views.EmployeeCreateView.as_view(), name="employee_create"),
    path("<int:pk>/edit/", views.EmployeeEditView.as_view(), name="employee_edit"),
    path("<int:pk>/reset-password/", views.EmployeePasswordResetView.as_view(), name="employee_reset_password"),
    path("<int:pk>/resign/", views.EmployeeResignView.as_view(), name="employee_resign"),
    path("<int:pk>/restore/", views.EmployeeRestoreView.as_view(), name="employee_restore"),
]
