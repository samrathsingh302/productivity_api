from django.contrib import admin
from .models import Category, Habit, HabitEntry, Task, TimeLog


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'colour', 'created_at')
    list_filter = ('user',)
    search_fields = ('name',)


@admin.register(Habit)
class HabitAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'category', 'target_frequency', 'is_active', 'created_at')
    list_filter = ('target_frequency', 'is_active', 'user')
    search_fields = ('name',)


@admin.register(HabitEntry)
class HabitEntryAdmin(admin.ModelAdmin):
    list_display = ('habit', 'date', 'created_at')
    list_filter = ('date',)
    search_fields = ('habit__name',)


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'priority', 'status', 'due_date', 'completed_at')
    list_filter = ('status', 'priority', 'user')
    search_fields = ('title',)


@admin.register(TimeLog)
class TimeLogAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'category', 'duration_minutes', 'date')
    list_filter = ('date', 'user')
    search_fields = ('title',)
