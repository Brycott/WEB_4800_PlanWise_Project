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

# Create your views here.
class TaskListView(LoginRequiredMixin, ListView):
    model = Task
    template_name = 'tasks/task_list.html'
    context_object_name = 'tasks'

    def get_queryset(self):
        # Show only top-level tasks
        return Task.objects.filter(user=self.request.user).select_related('category')

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


    def post(self, request, *args, **kwargs):
        parent_task = self.get_object()
        form = TaskForm(request.POST)
        if form.is_valid():
            new_task = form.save(commit=False)
            new_task.parent = parent_task
            new_task.user = request.user
            new_task.save()
            return redirect(parent_task.get_absolute_url())
        else:
            # If form is invalid, re-render the page with the context
            context = self.get_context_data(**kwargs)
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
        return super().form_valid(form)

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

class TaskDeleteView(LoginRequiredMixin, DeleteView):
    model = Task
    template_name = 'tasks/task_confirm_delete.html'
    success_url = reverse_lazy('tasks:task_list')
    
    def get_queryset(self):
        return Task.objects.filter(user=self.request.user)

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
    success_url = reverse_lazy('tasks:category_list')

    def get_queryset(self):
        return Category.objects.filter(user=self.request.user)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.task_set.exists():
            messages.error(request, 'Cannot delete category with associated tasks. Please remove tasks first.', extra_tags='alert-danger')
            return redirect('tasks:category_list')
        messages.success(request, 'Category deleted successfully.', extra_tags='alert-success')
        return super().post(request, *args, **kwargs)