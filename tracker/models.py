from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator


class Category(models.Model):
    """
    User-defined category for organising habits, tasks, and time logs.
    Examples: Work, Health, Study, Personal.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='categories'
    )
    name = models.CharField(max_length=100)
    colour = models.CharField(
        max_length=7, default='#4A90D9',
        help_text='Hex colour code for UI display, e.g. #4A90D9'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'name')
        ordering = ['name']
        verbose_name_plural = 'categories'

    def __str__(self):
        return f"{self.name} ({self.user.username})"


class Habit(models.Model):
    """
    A recurring behaviour the user wants to track.
    Completion is logged via HabitEntry records.
    """
    FREQUENCY_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='habits'
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='habits'
    )
    target_frequency = models.CharField(
        max_length=10, choices=FREQUENCY_CHOICES, default='daily'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'name')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.user.username})"


class HabitEntry(models.Model):
    """
    A single completion record for a habit on a given date.
    One entry per habit per date (used for streak calculations).
    """
    habit = models.ForeignKey(
        Habit, on_delete=models.CASCADE, related_name='entries'
    )
    date = models.DateField()
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('habit', 'date')
        ordering = ['-date']
        verbose_name_plural = 'habit entries'

    def __str__(self):
        return f"{self.habit.name} — {self.date}"


class Task(models.Model):
    """
    A one-off task with a lifecycle: pending → in_progress → completed.
    """
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='tasks'
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='tasks'
    )
    priority = models.CharField(
        max_length=10, choices=PRIORITY_CHOICES, default='medium'
    )
    status = models.CharField(
        max_length=15, choices=STATUS_CHOICES, default='pending'
    )
    due_date = models.DateField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} [{self.status}] ({self.user.username})"


class TimeLog(models.Model):
    """
    A record of time spent on an activity.
    Used for productivity heatmaps and time-based analytics.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='timelogs'
    )
    title = models.CharField(max_length=200)
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='timelogs'
    )
    duration_minutes = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text='Duration in minutes (minimum 1)'
    )
    date = models.DateField()
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.title} — {self.duration_minutes}min on {self.date} ({self.user.username})"
