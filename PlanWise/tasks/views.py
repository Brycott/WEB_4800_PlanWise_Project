from django.http import HttpResponseRedirect
from django.urls import reverse
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from .models import Task, Category
from .forms import TaskForm, CategoryForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import date
from dateutil.relativedelta import relativedelta
import uuid

def _create_recurring_tasks(task, user, recurring_task_id):
    if task.due_date and task.recurrence_end_date:
        current_date = task.due_date
        while current_date <= task.recurrence_end_date:
            Task.objects.create(
                title=task.title,
                description=task.description,
                category=task.category,
                due_date=current_date,
                user=user,
                is_recurring=True,
                recurrence_frequency=task.recurrence_frequency,
                recurrence_end_date=task.recurrence_end_date,
                recurring_task_id=recurring_task_id
            )
            if task.recurrence_frequency == 'daily':
                current_date += relativedelta(days=1)
            elif task.recurrence_frequency == 'weekly':
                current_date += relativedelta(weeks=1)
            elif task.recurrence_frequency == 'monthly':
                current_date += relativedelta(months=1)

# Create your views here.
class TaskListView(LoginRequiredMixin, ListView):
    model = Task
    template_name = 'tasks/task_list.html'
    context_object_name = 'tasks'

    def get_queryset(self):
        # Show only top-level tasks
        return Task.objects.filter(user=self.request.user, parent__isnull=True).select_related('category')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tasks_query = self.get_queryset()

        # Calculate task counts for summary cards
        context['total_tasks'] = tasks_query.count()
        context['completed_tasks'] = tasks_query.filter(is_completed=True).count()
        context['pending_tasks'] = tasks_query.filter(is_completed=False).count()
        context['overdue_tasks'] = tasks_query.filter(due_date__lt=timezone.now().date(), is_completed=False).count()
        context['today'] = timezone.now().date()

        # Get categories
        context['categories'] = Category.objects.all()
        return context


class TaskDetailView(LoginRequiredMixin, DetailView):
    model = Task
    template_name = 'tasks/task_detail.html'
    context_object_name = 'task'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['subtasks'] = self.object.subtasks.all()
        # Pass user to the form
        context['form'] = TaskForm(user=self.request.user)
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object() #  Assign object for context
        parent_task = self.object
        form = TaskForm(request.POST, user=request.user)  # Pass user to the form
        if form.is_valid():
            new_task = form.save(commit=False)
            new_task.parent = parent_task
            new_task.user = request.user
            new_task.save()
            return redirect(parent_task.get_absolute_url())
        else:
            # If form is invalid, re-render the page with the context
            context = self.get_context_data(**kwargs)
            context['form'] = form  # Pass the invalid form back to the template
            return self.render_to_response(context)

class TaskCreateView(LoginRequiredMixin, CreateView):
    model = Task
    form_class = TaskForm
    template_name = 'tasks/task_form.html'
    success_url = reverse_lazy('tasks:task_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.user = self.request.user
        self.object = form.save(commit=False)

        if self.object.is_recurring:
            recurring_task_id = uuid.uuid4()
            _create_recurring_tasks(self.object, self.request.user, recurring_task_id)
            return redirect(self.success_url)
        
        self.object.save()
        return HttpResponseRedirect(self.get_success_url())

class TaskUpdateView(LoginRequiredMixin, UpdateView):
    model = Task
    form_class = TaskForm
    template_name = 'tasks/task_form.html'
    success_url = reverse_lazy('tasks:task_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edit Task'
        return context

    def get_queryset(self):
        return Task.objects.filter(user=self.request.user)

    def form_valid(self, form):
        self.object = form.save(commit=False)

        if self.object.is_recurring:
            # Delete all future recurring tasks with the same recurring_task_id
            Task.objects.filter(
                user=self.request.user,
                recurring_task_id=self.object.recurring_task_id,
            ).delete()

            _create_recurring_tasks(self.object, self.request.user, self.object.recurring_task_id)
            return redirect(self.success_url)

        self.object.save()
        return HttpResponseRedirect(self.get_success_url())

class TaskDeleteView(LoginRequiredMixin, DeleteView):
    model = Task
    template_name = 'tasks/task_confirm_delete.html'
    success_url = reverse_lazy('tasks:task_list')

    def get_queryset(self):
        return Task.objects.filter(user=self.request.user)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.subtasks.filter(is_completed=False).exists():
            messages.error(request, 'Cannot delete a parent task with incomplete subtasks.', extra_tags='alert-danger')
            return redirect('tasks:task_list')
        messages.success(request, 'Task deleted successfully.', extra_tags='alert-success')
        return super().post(request, *args, **kwargs)

class CategoryListView(LoginRequiredMixin, ListView):
    model = Category
    template_name = 'tasks/category_list.html'
    context_object_name = 'categories'

    def get_queryset(self):
        return Category.objects.filter(user=self.request.user)

class CategoryCreateView(LoginRequiredMixin, CreateView):
    model = Category
    form_class = CategoryForm
    template_name = 'tasks/category_form.html'
    success_url = reverse_lazy('tasks:category_list')
    
    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, 'Category created successfully!', extra_tags='alert-success')
        return super().form_valid(form)

@login_required
def task_by_category(request, category_id):
    tasks = Task.objects.filter(category_id=category_id, user=request.user)
    category = get_object_or_404(Category, id=category_id)
    return render(request, 'tasks/tasks_by_category.html', {
        'tasks': tasks,
        'category': category
    })

@login_required
def toggle_complete(request, pk):
    task = get_object_or_404(Task, pk=pk, user=request.user)
    # Prevent completing a parent task if it has incomplete subtasks
    if not task.is_completed and task.subtasks.filter(is_completed=False).exists():
        messages.error(request, 'Cannot complete a parent task with incomplete subtasks.', extra_tags='alert-danger')
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', reverse('tasks:task_list')))
    task.is_completed = not task.is_completed
    task.save()
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', reverse('tasks:task_list')))

# Calendar view for tasks
@login_required
def calendar_view(request):
    import json
    from django.utils.dateparse import parse_datetime
    tasks = Task.objects.filter(user=request.user).exclude(due_date__isnull=True)
    events = []
    from datetime import datetime, time
    for task in tasks:
        if task.due_date:
            # Convert date to timestamp at local noon to avoid timezone shifts
            dt = datetime.combine(task.due_date, time(hour=12, minute=0))
            timestamp = int(dt.timestamp() * 1000)
            events.append({
                'id': task.id,
                'title': task.title,
                'start': timestamp,
                'url': f"/task/{task.id}/",  # Match Django URL pattern
            })
    events_json = json.dumps(events)
    return render(request, 'tasks/calendar.html', {'events_json': events_json, 'tasks': tasks})
    

class CategoryUpdateView(LoginRequiredMixin, UpdateView):
    model = Category
    fields = ['name']
    template_name = 'tasks/category_form.html'
    success_url = reverse_lazy('tasks:category_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edit Category'
        return context

class CategoryDeleteView(LoginRequiredMixin, DeleteView):
    model = Category
    template_name = 'tasks/category_confirm_delete.html'
    success_url = reverse_lazy('tasks:task_list')

    def get_queryset(self):
        return Category.objects.filter(user=self.request.user)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.task_set.exists():
            messages.error(request, 'Cannot delete category with associated tasks. Please remove tasks first.', extra_tags='alert-danger')
            return redirect('tasks:category_list')
        messages.success(request, 'Category deleted successfully.', extra_tags='alert-success')
        return super().post(request, *args, **kwargs)