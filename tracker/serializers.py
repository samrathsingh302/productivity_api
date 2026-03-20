from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Category, Habit, HabitEntry, Task, TimeLog


# ─── Auth ────────────────────────────────────────────────────

class UserRegisterSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password'],
        )
        return user


# ─── Category ────────────────────────────────────────────────

class CategorySerializer(serializers.ModelSerializer):
    """Serializer for Category with HATEOAS links."""
    links = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'colour', 'created_at', 'links']
        read_only_fields = ['id', 'created_at']

    def get_links(self, obj):
        return {
            'self': f'/api/categories/{obj.pk}/',
            'categories_list': '/api/categories/',
        }


# ─── Habit ───────────────────────────────────────────────────

class HabitEntrySerializer(serializers.ModelSerializer):
    """Serializer for HabitEntry."""
    links = serializers.SerializerMethodField()

    class Meta:
        model = HabitEntry
        fields = ['id', 'date', 'notes', 'created_at', 'links']
        read_only_fields = ['id', 'created_at']

    def get_links(self, obj):
        return {
            'self': f'/api/habits/{obj.habit.pk}/entries/{obj.pk}/',
            'habit': f'/api/habits/{obj.habit.pk}/',
        }


class HabitSerializer(serializers.ModelSerializer):
    """Serializer for Habit with HATEOAS links."""
    category_name = serializers.CharField(source='category.name', read_only=True, default=None)
    links = serializers.SerializerMethodField()

    class Meta:
        model = Habit
        fields = [
            'id', 'name', 'description', 'category', 'category_name',
            'target_frequency', 'is_active', 'created_at', 'links',
        ]
        read_only_fields = ['id', 'created_at']

    def get_links(self, obj):
        return {
            'self': f'/api/habits/{obj.pk}/',
            'entries': f'/api/habits/{obj.pk}/entries/',
            'habits_list': '/api/habits/',
            'analytics_streaks': '/api/analytics/streaks/',
        }


class HabitDetailSerializer(HabitSerializer):
    """Extended Habit serializer that includes recent entries."""
    recent_entries = serializers.SerializerMethodField()

    class Meta(HabitSerializer.Meta):
        fields = HabitSerializer.Meta.fields + ['recent_entries']

    def get_recent_entries(self, obj):
        entries = obj.entries.all()[:10]
        return HabitEntrySerializer(entries, many=True).data


# ─── Task ────────────────────────────────────────────────────

class TaskSerializer(serializers.ModelSerializer):
    """Serializer for Task with HATEOAS links."""
    category_name = serializers.CharField(source='category.name', read_only=True, default=None)
    links = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            'id', 'title', 'description', 'category', 'category_name',
            'priority', 'status', 'due_date', 'completed_at', 'created_at', 'links',
        ]
        read_only_fields = ['id', 'completed_at', 'created_at']

    def get_links(self, obj):
        return {
            'self': f'/api/tasks/{obj.pk}/',
            'tasks_list': '/api/tasks/',
        }


# ─── TimeLog ─────────────────────────────────────────────────

class TimeLogSerializer(serializers.ModelSerializer):
    """Serializer for TimeLog with HATEOAS links."""
    category_name = serializers.CharField(source='category.name', read_only=True, default=None)
    links = serializers.SerializerMethodField()

    class Meta:
        model = TimeLog
        fields = [
            'id', 'title', 'category', 'category_name',
            'duration_minutes', 'date', 'notes', 'created_at', 'links',
        ]
        read_only_fields = ['id', 'created_at']

    def get_links(self, obj):
        return {
            'self': f'/api/timelogs/{obj.pk}/',
            'timelogs_list': '/api/timelogs/',
            'analytics_heatmap': '/api/analytics/heatmap/',
        }
