from django.urls import path
from . import views

urlpatterns = [
    # API root
    path('', views.api_root, name='api-root'),

    # Authentication
    path('register/', views.register, name='register'),
    path('login/', views.login, name='login'),

    # Categories
    path('categories/', views.category_list, name='category-list'),
    path('categories/<int:pk>/', views.category_detail, name='category-detail'),

    # Habits
    path('habits/', views.habit_list, name='habit-list'),
    path('habits/<int:pk>/', views.habit_detail, name='habit-detail'),

    # Habit Entries
    path('habits/<int:habit_pk>/entries/', views.habit_entry_list, name='habit-entry-list'),
    path('habits/<int:habit_pk>/entries/<int:entry_pk>/', views.habit_entry_detail, name='habit-entry-detail'),

    # Tasks
    path('tasks/', views.task_list, name='task-list'),
    path('tasks/<int:pk>/', views.task_detail, name='task-detail'),

    # Time Logs
    path('timelogs/', views.timelog_list, name='timelog-list'),
    path('timelogs/<int:pk>/', views.timelog_detail, name='timelog-detail'),

    # Analytics
    path('analytics/streaks/', views.analytics_streaks, name='analytics-streaks'),
    path('analytics/heatmap/', views.analytics_heatmap, name='analytics-heatmap'),
    path('analytics/summary/', views.analytics_summary, name='analytics-summary'),
]
