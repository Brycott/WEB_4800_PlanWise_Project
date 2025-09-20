from django.urls import path
from . import views


urlpatterns = [
    path('', views.TaskListView.as_view(), name='task_list'),
    path('task/<int:pk>/', views.TaskDetailView.as_view(), name='task_detail'),
    path('task/new/', views.TaskCreateView.as_view(), name='task_create'),
    path('task/<int:pk>/edit/', views.TaskUpdateView.as_view(), name='task_update'),
    path('task/<int:pk>/delete/', views.TaskDeleteView.as_view(), name='task_delete'),
    path('task/<int:pk>/toggle/', views.toggle_complete, name='task_toggle complete'),
    path('category/new/', views.CategoryCreateView.as_view(), name='category_create'),
    path('category/<int:category_id>/', views.task_by_category, name='tasks_by_category'),
    path('calendar/', views.calendar_view, name='task_calendar'),
]