from django.contrib import admin
from .models import Task, Category

# Register your models here.

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'is_completed', 'user', 'created_at']
    list_filter = ['is_completed', 'category', 'user', 'created_at']
    search_fields = ['title', 'description']
    date_hierarchy = 'created_at'


