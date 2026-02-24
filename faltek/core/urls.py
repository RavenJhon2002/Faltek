
from django.urls import path
from . import views

urlpatterns = [
    path('', views.project_list, name='project_list'),
    path('create/', views.project_create, name='project_create'),
    path('edit/<int:pk>/', views.project_edit, name='project_edit'),
    path('delete/<int:pk>/', views.project_delete, name='project_delete'),
    path('signup/', views.signup, name='signup'),
    path("project/<int:project_id>/upload-boq/", views.upload_boq, name="upload_boq"),
    path("projects/<int:project_id>/gantt/",views.project_gantt,name="project_gantt"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path('project/<int:pk>/', views.project_detail, name='project_detail'),

]   