from datetime import timedelta
from collections import OrderedDict

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.pagination import PageNumberPagination
from django.contrib.auth import authenticate
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Count, Sum

from .models import Category, Habit, HabitEntry, Task, TimeLog
from .serializers import (
    UserRegisterSerializer,
    CategorySerializer,
    HabitSerializer,
    HabitDetailSerializer,
    HabitEntrySerializer,
    TaskSerializer,
    TimeLogSerializer,
)


# ─── Helpers ─────────────────────────────────────────────────

def paginate(request, queryset, serializer_class):
    """Helper to paginate a queryset in function-based views."""
    paginator = PageNumberPagination()
    page = paginator.paginate_queryset(queryset, request)
    if page is not None:
        serializer = serializer_class(page, many=True)
        return paginator.get_paginated_response(serializer.data)
    serializer = serializer_class(queryset, many=True)
    return Response(serializer.data)


def require_auth(request):
    """Return an error Response if user is not authenticated, else None."""
    if not request.user.is_authenticated:
        return Response(
            {'error': 'Authentication required. Include your token in the Authorization header.'},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    return None


def require_owner(obj, request):
    """Return an error Response if request.user does not own obj, else None."""
    if obj.user != request.user:
        return Response(
            {'error': 'You can only access your own resources.'},
            status=status.HTTP_403_FORBIDDEN,
        )
    return None


# ─── API Root ────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([AllowAny])
def api_root(request):
    """API root listing all available endpoints with HATEOAS links."""
    return Response({
        'message': 'Welcome to the Productivity & Habit Analytics API',
        'endpoints': {
            'register': '/api/register/',
            'login': '/api/login/',
            'categories': '/api/categories/',
            'category_detail': '/api/categories/<id>/',
            'habits': '/api/habits/',
            'habit_detail': '/api/habits/<id>/',
            'habit_entries': '/api/habits/<id>/entries/',
            'habit_entry_delete': '/api/habits/<id>/entries/<entry_id>/',
            'tasks': '/api/tasks/',
            'task_detail': '/api/tasks/<id>/',
            'timelogs': '/api/timelogs/',
            'timelog_detail': '/api/timelogs/<id>/',
            'analytics_streaks': '/api/analytics/streaks/',
            'analytics_heatmap': '/api/analytics/heatmap/',
            'analytics_summary': '/api/analytics/summary/',
        },
    })


# ─── Authentication ──────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """Register a new user account and return an auth token."""
    serializer = UserRegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            'message': 'User registered successfully.',
            'username': user.username,
            'token': token.key,
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """Log in and receive an authentication token."""
    username = request.data.get('username')
    password = request.data.get('password')

    if not username or not password:
        return Response(
            {'error': 'Both username and password are required.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = authenticate(username=username, password=password)
    if user is None:
        return Response(
            {'error': 'Invalid username or password.'},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    token, _ = Token.objects.get_or_create(user=user)
    return Response({
        'message': 'Login successful.',
        'username': user.username,
        'token': token.key,
    }, status=status.HTTP_200_OK)


# ─── Categories ──────────────────────────────────────────────

@api_view(['GET', 'POST'])
def category_list(request):
    """
    GET:  List the authenticated user's categories (paginated).
    POST: Create a new category for the authenticated user.
    """
    auth_err = require_auth(request)
    if auth_err:
        return auth_err

    if request.method == 'GET':
        categories = Category.objects.filter(user=request.user)
        return paginate(request, categories, CategorySerializer)

    # POST
    name = request.data.get('name')
    if not name or not str(name).strip():
        return Response(
            {'error': 'The name field is required.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Duplicate check
    if Category.objects.filter(user=request.user, name=name.strip()).exists():
        return Response(
            {'error': 'You already have a category with this name.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    serializer = CategorySerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(user=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
def category_detail(request, pk):
    """
    GET:    View a single category.
    PUT:    Update a category (owner only).
    DELETE: Delete a category (owner only).
    """
    auth_err = require_auth(request)
    if auth_err:
        return auth_err

    category = get_object_or_404(Category, pk=pk)

    owner_err = require_owner(category, request)
    if owner_err:
        return owner_err

    if request.method == 'GET':
        serializer = CategorySerializer(category)
        return Response(serializer.data, status=status.HTTP_200_OK)

    if request.method == 'PUT':
        name = request.data.get('name')
        if not name or not str(name).strip():
            return Response(
                {'error': 'The name field is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Duplicate check (exclude self)
        if Category.objects.filter(
            user=request.user, name=name.strip()
        ).exclude(pk=pk).exists():
            return Response(
                {'error': 'You already have a category with this name.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = CategorySerializer(category, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # DELETE
    category.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


# ─── Habits ──────────────────────────────────────────────────

@api_view(['GET', 'POST'])
def habit_list(request):
    """
    GET:  List the authenticated user's habits (paginated).
          Supports ?active=true|false filter.
    POST: Create a new habit for the authenticated user.
    """
    auth_err = require_auth(request)
    if auth_err:
        return auth_err

    if request.method == 'GET':
        habits = Habit.objects.filter(user=request.user).select_related('category')

        # Optional active filter
        active_param = request.query_params.get('active')
        if active_param is not None:
            if active_param.lower() in ('true', '1'):
                habits = habits.filter(is_active=True)
            elif active_param.lower() in ('false', '0'):
                habits = habits.filter(is_active=False)

        return paginate(request, habits, HabitSerializer)

    # POST
    name = request.data.get('name')
    if not name or not str(name).strip():
        return Response(
            {'error': 'The name field is required.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Duplicate check
    if Habit.objects.filter(user=request.user, name=name.strip()).exists():
        return Response(
            {'error': 'You already have a habit with this name.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Validate category ownership if provided
    category_id = request.data.get('category')
    if category_id is not None:
        category = Category.objects.filter(pk=category_id, user=request.user).first()
        if category is None:
            return Response(
                {'error': 'Category not found or does not belong to you.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

    # Validate target_frequency if provided
    frequency = request.data.get('target_frequency')
    valid_frequencies = [c[0] for c in Habit.FREQUENCY_CHOICES]
    if frequency and frequency not in valid_frequencies:
        return Response(
            {'error': f'target_frequency must be one of: {", ".join(valid_frequencies)}.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    serializer = HabitSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(user=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
def habit_detail(request, pk):
    """
    GET:    View a single habit with recent entries.
    PUT:    Update a habit (owner only).
    DELETE: Delete a habit and all its entries (owner only).
    """
    auth_err = require_auth(request)
    if auth_err:
        return auth_err

    habit = get_object_or_404(Habit, pk=pk)

    owner_err = require_owner(habit, request)
    if owner_err:
        return owner_err

    if request.method == 'GET':
        serializer = HabitDetailSerializer(habit)
        return Response(serializer.data, status=status.HTTP_200_OK)

    if request.method == 'PUT':
        # Validate category ownership if changing
        category_id = request.data.get('category')
        if category_id is not None:
            category = Category.objects.filter(pk=category_id, user=request.user).first()
            if category is None:
                return Response(
                    {'error': 'Category not found or does not belong to you.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Duplicate name check (exclude self)
        name = request.data.get('name')
        if name:
            if Habit.objects.filter(
                user=request.user, name=name.strip()
            ).exclude(pk=pk).exists():
                return Response(
                    {'error': 'You already have a habit with this name.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Validate target_frequency if provided
        frequency = request.data.get('target_frequency')
        valid_frequencies = [c[0] for c in Habit.FREQUENCY_CHOICES]
        if frequency and frequency not in valid_frequencies:
            return Response(
                {'error': f'target_frequency must be one of: {", ".join(valid_frequencies)}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = HabitSerializer(habit, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # DELETE
    habit.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


# ─── Habit Entries ───────────────────────────────────────────

@api_view(['GET', 'POST'])
def habit_entry_list(request, habit_pk):
    """
    GET:  List all entries for a habit (paginated). Owner only.
    POST: Log a completion entry for a habit on a given date. Owner only.
    """
    auth_err = require_auth(request)
    if auth_err:
        return auth_err

    habit = get_object_or_404(Habit, pk=habit_pk)

    owner_err = require_owner(habit, request)
    if owner_err:
        return owner_err

    if request.method == 'GET':
        entries = HabitEntry.objects.filter(habit=habit)
        return paginate(request, entries, HabitEntrySerializer)

    # POST
    date = request.data.get('date')
    if not date:
        return Response(
            {'error': 'The date field is required (YYYY-MM-DD).'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Validate date format
    from datetime import datetime as dt
    try:
        parsed_date = dt.strptime(str(date), '%Y-%m-%d').date()
    except ValueError:
        return Response(
            {'error': 'Invalid date format. Use YYYY-MM-DD.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # No future dates
    if parsed_date > timezone.now().date():
        return Response(
            {'error': 'Cannot log entries for future dates.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Duplicate check
    if HabitEntry.objects.filter(habit=habit, date=parsed_date).exists():
        return Response(
            {'error': 'An entry for this habit on this date already exists.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    entry = HabitEntry.objects.create(
        habit=habit,
        date=parsed_date,
        notes=request.data.get('notes', ''),
    )
    serializer = HabitEntrySerializer(entry)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['GET', 'DELETE'])
def habit_entry_detail(request, habit_pk, entry_pk):
    """
    GET:    View a single habit entry. Owner only.
    DELETE: Remove a habit entry. Owner only.
    """
    auth_err = require_auth(request)
    if auth_err:
        return auth_err

    habit = get_object_or_404(Habit, pk=habit_pk)

    owner_err = require_owner(habit, request)
    if owner_err:
        return owner_err

    entry = get_object_or_404(HabitEntry, pk=entry_pk, habit=habit)

    if request.method == 'GET':
        serializer = HabitEntrySerializer(entry)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # DELETE
    entry.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


# ─── Tasks ───────────────────────────────────────────────────

@api_view(['GET', 'POST'])
def task_list(request):
    """
    GET:  List the authenticated user's tasks (paginated).
          Supports filters: ?status=pending|in_progress|completed
                            ?priority=low|medium|high
    POST: Create a new task for the authenticated user.
    """
    auth_err = require_auth(request)
    if auth_err:
        return auth_err

    if request.method == 'GET':
        tasks = Task.objects.filter(user=request.user).select_related('category')

        # Optional filters
        status_param = request.query_params.get('status')
        valid_statuses = [c[0] for c in Task.STATUS_CHOICES]
        if status_param and status_param in valid_statuses:
            tasks = tasks.filter(status=status_param)

        priority_param = request.query_params.get('priority')
        valid_priorities = [c[0] for c in Task.PRIORITY_CHOICES]
        if priority_param and priority_param in valid_priorities:
            tasks = tasks.filter(priority=priority_param)

        return paginate(request, tasks, TaskSerializer)

    # POST
    title = request.data.get('title')
    if not title or not str(title).strip():
        return Response(
            {'error': 'The title field is required.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Validate category ownership if provided
    category_id = request.data.get('category')
    if category_id is not None:
        category = Category.objects.filter(pk=category_id, user=request.user).first()
        if category is None:
            return Response(
                {'error': 'Category not found or does not belong to you.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

    # Validate priority if provided
    priority = request.data.get('priority')
    valid_priorities = [c[0] for c in Task.PRIORITY_CHOICES]
    if priority and priority not in valid_priorities:
        return Response(
            {'error': f'priority must be one of: {", ".join(valid_priorities)}.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Validate status if provided
    task_status = request.data.get('status')
    valid_statuses = [c[0] for c in Task.STATUS_CHOICES]
    if task_status and task_status not in valid_statuses:
        return Response(
            {'error': f'status must be one of: {", ".join(valid_statuses)}.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    serializer = TaskSerializer(data=request.data)
    if serializer.is_valid():
        task = serializer.save(user=request.user)
        # Auto-set completed_at if created with status=completed
        if task.status == 'completed' and task.completed_at is None:
            task.completed_at = timezone.now()
            task.save()
            serializer = TaskSerializer(task)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
def task_detail(request, pk):
    """
    GET:    View a single task.
    PUT:    Update a task (owner only). Automatically manages completed_at.
    DELETE: Delete a task (owner only).
    """
    auth_err = require_auth(request)
    if auth_err:
        return auth_err

    task = get_object_or_404(Task, pk=pk)

    owner_err = require_owner(task, request)
    if owner_err:
        return owner_err

    if request.method == 'GET':
        serializer = TaskSerializer(task)
        return Response(serializer.data, status=status.HTTP_200_OK)

    if request.method == 'PUT':
        # Validate category ownership if changing
        category_id = request.data.get('category')
        if category_id is not None:
            category = Category.objects.filter(pk=category_id, user=request.user).first()
            if category is None:
                return Response(
                    {'error': 'Category not found or does not belong to you.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Validate priority if provided
        priority = request.data.get('priority')
        valid_priorities = [c[0] for c in Task.PRIORITY_CHOICES]
        if priority and priority not in valid_priorities:
            return Response(
                {'error': f'priority must be one of: {", ".join(valid_priorities)}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate status if provided
        new_status = request.data.get('status')
        valid_statuses = [c[0] for c in Task.STATUS_CHOICES]
        if new_status and new_status not in valid_statuses:
            return Response(
                {'error': f'status must be one of: {", ".join(valid_statuses)}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        old_status = task.status

        serializer = TaskSerializer(task, data=request.data, partial=True)
        if serializer.is_valid():
            task = serializer.save()

            # Auto-manage completed_at timestamp
            if task.status == 'completed' and old_status != 'completed':
                task.completed_at = timezone.now()
                task.save()
            elif task.status != 'completed' and old_status == 'completed':
                task.completed_at = None
                task.save()

            serializer = TaskSerializer(task)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # DELETE
    task.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


# ─── Time Logs ───────────────────────────────────────────────

@api_view(['GET', 'POST'])
def timelog_list(request):
    """
    GET:  List the authenticated user's time logs (paginated).
          Supports filters: ?category=<id>
                            ?date_from=YYYY-MM-DD
                            ?date_to=YYYY-MM-DD
    POST: Create a new time log entry.
    """
    auth_err = require_auth(request)
    if auth_err:
        return auth_err

    if request.method == 'GET':
        timelogs = TimeLog.objects.filter(user=request.user).select_related('category')

        # Optional filters
        category_param = request.query_params.get('category')
        if category_param:
            timelogs = timelogs.filter(category_id=category_param)

        date_from = request.query_params.get('date_from')
        if date_from:
            timelogs = timelogs.filter(date__gte=date_from)

        date_to = request.query_params.get('date_to')
        if date_to:
            timelogs = timelogs.filter(date__lte=date_to)

        return paginate(request, timelogs, TimeLogSerializer)

    # POST
    title = request.data.get('title')
    if not title or not str(title).strip():
        return Response(
            {'error': 'The title field is required.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    duration = request.data.get('duration_minutes')
    if duration is None:
        return Response(
            {'error': 'The duration_minutes field is required.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        duration = int(duration)
        if duration < 1:
            raise ValueError
    except (ValueError, TypeError):
        return Response(
            {'error': 'duration_minutes must be a positive integer.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    log_date = request.data.get('date')
    if not log_date:
        return Response(
            {'error': 'The date field is required (YYYY-MM-DD).'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    from datetime import datetime as dt
    try:
        parsed_date = dt.strptime(str(log_date), '%Y-%m-%d').date()
    except ValueError:
        return Response(
            {'error': 'Invalid date format. Use YYYY-MM-DD.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # No future dates
    if parsed_date > timezone.now().date():
        return Response(
            {'error': 'Cannot log time for future dates.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Validate category ownership if provided
    category_id = request.data.get('category')
    if category_id is not None:
        category = Category.objects.filter(pk=category_id, user=request.user).first()
        if category is None:
            return Response(
                {'error': 'Category not found or does not belong to you.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

    serializer = TimeLogSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(user=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
def timelog_detail(request, pk):
    """
    GET:    View a single time log.
    PUT:    Update a time log (owner only).
    DELETE: Delete a time log (owner only).
    """
    auth_err = require_auth(request)
    if auth_err:
        return auth_err

    timelog = get_object_or_404(TimeLog, pk=pk)

    owner_err = require_owner(timelog, request)
    if owner_err:
        return owner_err

    if request.method == 'GET':
        serializer = TimeLogSerializer(timelog)
        return Response(serializer.data, status=status.HTTP_200_OK)

    if request.method == 'PUT':
        # Validate category ownership if changing
        category_id = request.data.get('category')
        if category_id is not None:
            category = Category.objects.filter(pk=category_id, user=request.user).first()
            if category is None:
                return Response(
                    {'error': 'Category not found or does not belong to you.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Validate duration if changing
        duration = request.data.get('duration_minutes')
        if duration is not None:
            try:
                duration = int(duration)
                if duration < 1:
                    raise ValueError
            except (ValueError, TypeError):
                return Response(
                    {'error': 'duration_minutes must be a positive integer.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        serializer = TimeLogSerializer(timelog, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # DELETE
    timelog.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


# ─── Analytics ───────────────────────────────────────────────

def _compute_streaks(entries_dates, today):
    """
    Given a sorted set of dates (ascending) and today's date,
    compute current streak and longest streak.
    Current streak: consecutive days ending on today or yesterday.
    Longest streak: longest consecutive run ever.
    """
    if not entries_dates:
        return {'current_streak': 0, 'longest_streak': 0}

    sorted_dates = sorted(entries_dates)

    # Longest streak
    longest = 1
    current_run = 1
    for i in range(1, len(sorted_dates)):
        if sorted_dates[i] - sorted_dates[i - 1] == timedelta(days=1):
            current_run += 1
            longest = max(longest, current_run)
        elif sorted_dates[i] != sorted_dates[i - 1]:
            current_run = 1

    # Current streak — walk backwards from the most recent entry
    # Only counts if the most recent entry is today or yesterday
    last_date = sorted_dates[-1]
    if last_date < today - timedelta(days=1):
        current = 0
    else:
        current = 1
        for i in range(len(sorted_dates) - 2, -1, -1):
            if sorted_dates[i] == sorted_dates[i + 1] - timedelta(days=1):
                current += 1
            else:
                break

    return {'current_streak': current, 'longest_streak': longest}


@api_view(['GET'])
def analytics_streaks(request):
    """
    Return current and longest streak for each of the user's active habits.
    Server-side computation using habit entry dates.

    Response format:
    [
      {
        "habit_id": 1,
        "habit_name": "Morning run",
        "current_streak": 5,
        "longest_streak": 12,
        "total_entries": 45,
        "links": {"habit": "/api/habits/1/", "entries": "/api/habits/1/entries/"}
      },
      ...
    ]
    """
    auth_err = require_auth(request)
    if auth_err:
        return auth_err

    today = timezone.now().date()
    habits = Habit.objects.filter(user=request.user, is_active=True)

    results = []
    for habit in habits:
        entry_dates = list(
            habit.entries.values_list('date', flat=True).order_by('date')
        )
        streaks = _compute_streaks(entry_dates, today)
        results.append({
            'habit_id': habit.pk,
            'habit_name': habit.name,
            'current_streak': streaks['current_streak'],
            'longest_streak': streaks['longest_streak'],
            'total_entries': len(entry_dates),
            'links': {
                'habit': f'/api/habits/{habit.pk}/',
                'entries': f'/api/habits/{habit.pk}/entries/',
            },
        })

    return Response(results, status=status.HTTP_200_OK)


@api_view(['GET'])
def analytics_heatmap(request):
    """
    Return activity counts by date for a heatmap visualisation.
    Aggregates across habit entries, completed tasks, and time logs.

    Query params:
        ?days=30  (default 30, max 365)

    Response format:
    {
      "period": {"from": "2026-02-15", "to": "2026-03-17"},
      "total_active_days": 18,
      "data": [
        {"date": "2026-03-17", "habit_entries": 2, "tasks_completed": 1, "time_logs": 1, "total": 4},
        {"date": "2026-03-16", "habit_entries": 1, "tasks_completed": 0, "time_logs": 2, "total": 3},
        ...
      ]
    }
    """
    auth_err = require_auth(request)
    if auth_err:
        return auth_err

    # Parse days parameter
    try:
        days = int(request.query_params.get('days', 30))
        days = max(1, min(days, 365))
    except (ValueError, TypeError):
        days = 30

    today = timezone.now().date()
    start_date = today - timedelta(days=days - 1)

    # Habit entries by date
    habit_entry_counts = dict(
        HabitEntry.objects.filter(
            habit__user=request.user,
            date__gte=start_date,
            date__lte=today,
        ).values('date').annotate(count=Count('id')).values_list('date', 'count')
    )

    # Completed tasks by completion date
    task_counts = dict(
        Task.objects.filter(
            user=request.user,
            status='completed',
            completed_at__date__gte=start_date,
            completed_at__date__lte=today,
        ).values('completed_at__date').annotate(count=Count('id')).values_list('completed_at__date', 'count')
    )

    # Time logs by date
    timelog_counts = dict(
        TimeLog.objects.filter(
            user=request.user,
            date__gte=start_date,
            date__lte=today,
        ).values('date').annotate(count=Count('id')).values_list('date', 'count')
    )

    # Build day-by-day data
    data = []
    total_active_days = 0
    for i in range(days):
        d = today - timedelta(days=i)
        h = habit_entry_counts.get(d, 0)
        t = task_counts.get(d, 0)
        tl = timelog_counts.get(d, 0)
        total = h + t + tl
        if total > 0:
            total_active_days += 1
        data.append({
            'date': str(d),
            'habit_entries': h,
            'tasks_completed': t,
            'time_logs': tl,
            'total': total,
        })

    return Response({
        'period': {'from': str(start_date), 'to': str(today)},
        'total_active_days': total_active_days,
        'data': data,
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
def analytics_summary(request):
    """
    Return a behavioural summary over a period.

    Query params:
        ?period=week  (default, or 'month')

    Response format:
    {
      "period": "week",
      "date_range": {"from": "2026-03-11", "to": "2026-03-17"},
      "habits": {
        "total_active": 3,
        "total_entries": 15,
        "completion_rate": 0.71,
        "best_habit": {"name": "Morning run", "entries": 7},
        "worst_habit": {"name": "Read", "entries": 2}
      },
      "tasks": {
        "total_created": 5,
        "total_completed": 3,
        "completion_rate": 0.60,
        "by_priority": {"high": 1, "medium": 1, "low": 1}
      },
      "time_logs": {
        "total_entries": 8,
        "total_minutes": 420,
        "daily_average_minutes": 60.0,
        "by_category": [
          {"category": "Work", "minutes": 300},
          {"category": "Health", "minutes": 120}
        ]
      }
    }
    """
    auth_err = require_auth(request)
    if auth_err:
        return auth_err

    period = request.query_params.get('period', 'week')
    today = timezone.now().date()

    if period == 'month':
        start_date = today - timedelta(days=29)
        num_days = 30
    else:
        period = 'week'
        start_date = today - timedelta(days=6)
        num_days = 7

    # ── Habits ──
    active_habits = Habit.objects.filter(user=request.user, is_active=True)
    total_active = active_habits.count()

    habit_entries_in_period = HabitEntry.objects.filter(
        habit__user=request.user,
        habit__is_active=True,
        date__gte=start_date,
        date__lte=today,
    )
    total_entries = habit_entries_in_period.count()

    # Completion rate: entries / (active_habits * days in period)
    max_possible = total_active * num_days
    completion_rate = round(total_entries / max_possible, 2) if max_possible > 0 else 0.0

    # Per-habit entry counts for best/worst
    habit_entry_counts = (
        habit_entries_in_period
        .values('habit__id', 'habit__name')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    best_habit = None
    worst_habit = None
    if habit_entry_counts.exists():
        best = habit_entry_counts.first()
        best_habit = {'name': best['habit__name'], 'entries': best['count']}
        worst = habit_entry_counts.last()
        worst_habit = {'name': worst['habit__name'], 'entries': worst['count']}

    # ── Tasks ──
    tasks_created = Task.objects.filter(
        user=request.user,
        created_at__date__gte=start_date,
        created_at__date__lte=today,
    )
    total_tasks_created = tasks_created.count()

    tasks_completed = Task.objects.filter(
        user=request.user,
        status='completed',
        completed_at__date__gte=start_date,
        completed_at__date__lte=today,
    )
    total_tasks_completed = tasks_completed.count()

    task_completion_rate = (
        round(total_tasks_completed / total_tasks_created, 2)
        if total_tasks_created > 0 else 0.0
    )

    # Completed tasks by priority
    by_priority = {}
    for choice_val, _ in Task.PRIORITY_CHOICES:
        by_priority[choice_val] = tasks_completed.filter(priority=choice_val).count()

    # ── Time Logs ──
    timelogs_in_period = TimeLog.objects.filter(
        user=request.user,
        date__gte=start_date,
        date__lte=today,
    )
    total_tl_entries = timelogs_in_period.count()
    total_minutes = timelogs_in_period.aggregate(total=Sum('duration_minutes'))['total'] or 0
    daily_avg = round(total_minutes / num_days, 1) if num_days > 0 else 0.0

    # Time by category
    by_category_qs = (
        timelogs_in_period
        .values('category__name')
        .annotate(minutes=Sum('duration_minutes'))
        .order_by('-minutes')
    )
    by_category = [
        {
            'category': row['category__name'] or 'Uncategorised',
            'minutes': row['minutes'],
        }
        for row in by_category_qs
    ]

    return Response({
        'period': period,
        'date_range': {'from': str(start_date), 'to': str(today)},
        'habits': {
            'total_active': total_active,
            'total_entries': total_entries,
            'completion_rate': completion_rate,
            'best_habit': best_habit,
            'worst_habit': worst_habit,
        },
        'tasks': {
            'total_created': total_tasks_created,
            'total_completed': total_tasks_completed,
            'completion_rate': task_completion_rate,
            'by_priority': by_priority,
        },
        'time_logs': {
            'total_entries': total_tl_entries,
            'total_minutes': total_minutes,
            'daily_average_minutes': daily_avg,
            'by_category': by_category,
        },
    }, status=status.HTTP_200_OK)
