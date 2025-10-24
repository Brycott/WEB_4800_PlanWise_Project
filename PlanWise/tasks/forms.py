from django import forms
from .models import Task, Category

class TaskForm(forms.ModelForm):

    class Meta:
        model = Task
        fields = ['title', 'description', 'category', 'due_date', 'is_completed', 'is_recurring', 'recurrence_frequency', 'recurrence_end_date']
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control', 'style': 'width: 25%'}),
            'recurrence_end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control', 'style': 'width: 25%'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'style': 'width: 25%'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name']