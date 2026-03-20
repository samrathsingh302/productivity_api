"""
Automated test suite for the Productivity & Habit Analytics API.
Run with: python manage.py test tracker -v 2
"""
from datetime import date, timedelta
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token
from .models import Category, Habit, HabitEntry, Task, TimeLog


class BaseTestCase(TestCase):
    """Base test case with shared setup for all test classes."""

    def setUp(self):
        """Create test users, tokens, and common fixtures."""
        self.client = APIClient()

        # Two users for ownership tests
        self.user1 = User.objects.create_user(
            username='alice', email='alice@example.com', password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='bob', email='bob@example.com', password='testpass123'
        )
        self.token1 = Token.objects.create(user=self.user1)
        self.token2 = Token.objects.create(user=self.user2)

        # Shared category
        self.cat1 = Category.objects.create(user=self.user1, name='Health', colour='#22C55E')
        self.cat2 = Category.objects.create(user=self.user1, name='Work', colour='#3B82F6')
        self.cat_bob = Category.objects.create(user=self.user2, name='Study', colour='#A855F7')

    def auth_client(self, token):
        """Return an authenticated API client."""
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION='Token ' + token.key)
        return client


# ═══════════════════════════════════════════════════════════════
# API Root
# ═══════════════════════════════════════════════════════════════

class APIRootTests(BaseTestCase):

    def test_api_root_returns_200(self):
        response = self.client.get('/api/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_api_root_contains_all_endpoint_keys(self):
        response = self.client.get('/api/')
        endpoints = response.data['endpoints']
        for key in ['register', 'login', 'categories', 'habits', 'tasks',
                     'timelogs', 'analytics_streaks', 'analytics_heatmap',
                     'analytics_summary']:
            self.assertIn(key, endpoints)


# ═══════════════════════════════════════════════════════════════
# Authentication
# ═══════════════════════════════════════════════════════════════

class RegistrationTests(BaseTestCase):

    def test_register_success(self):
        data = {'username': 'newuser', 'email': 'new@example.com', 'password': 'securepass1'}
        response = self.client.post('/api/register/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('token', response.data)
        self.assertEqual(response.data['username'], 'newuser')

    def test_register_duplicate_username(self):
        data = {'username': 'alice', 'email': 'dup@example.com', 'password': 'securepass1'}
        response = self.client.post('/api/register/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_missing_password(self):
        data = {'username': 'nopass', 'email': 'nopass@example.com'}
        response = self.client.post('/api/register/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_short_password(self):
        data = {'username': 'shortpw', 'email': 'sp@example.com', 'password': 'abc'}
        response = self.client.post('/api/register/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class LoginTests(BaseTestCase):

    def test_login_success(self):
        data = {'username': 'alice', 'password': 'testpass123'}
        response = self.client.post('/api/login/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)

    def test_login_wrong_password(self):
        data = {'username': 'alice', 'password': 'wrongpass'}
        response = self.client.post('/api/login/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_nonexistent_user(self):
        data = {'username': 'nouser', 'password': 'testpass123'}
        response = self.client.post('/api/login/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_missing_fields(self):
        response = self.client.post('/api/login/', {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# ═══════════════════════════════════════════════════════════════
# Categories (Task 4)
# ═══════════════════════════════════════════════════════════════

class CategoryListTests(BaseTestCase):

    def test_list_requires_auth(self):
        response = self.client.get('/api/categories/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_returns_own_categories_only(self):
        client = self.auth_client(self.token1)
        response = client.get('/api/categories/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertEqual(response.data['count'], 2)
        names = [c['name'] for c in response.data['results']]
        self.assertIn('Health', names)
        self.assertIn('Work', names)
        self.assertNotIn('Study', names)

    def test_list_is_paginated(self):
        client = self.auth_client(self.token1)
        response = client.get('/api/categories/')
        self.assertIn('count', response.data)
        self.assertIn('next', response.data)
        self.assertIn('previous', response.data)
        self.assertIn('results', response.data)

    def test_create_category_success(self):
        client = self.auth_client(self.token1)
        data = {'name': 'Personal', 'colour': '#F59E0B'}
        response = client.post('/api/categories/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Personal')
        self.assertEqual(response.data['colour'], '#F59E0B')

    def test_create_category_default_colour(self):
        client = self.auth_client(self.token1)
        data = {'name': 'Misc'}
        response = client.post('/api/categories/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['colour'], '#4A90D9')

    def test_create_category_missing_name(self):
        client = self.auth_client(self.token1)
        response = client.post('/api/categories/', {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_category_duplicate_name(self):
        client = self.auth_client(self.token1)
        data = {'name': 'Health'}
        response = client.post('/api/categories/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_category_same_name_different_user(self):
        """Two users can have categories with the same name."""
        client = self.auth_client(self.token2)
        data = {'name': 'Health'}
        response = client.post('/api/categories/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class CategoryDetailTests(BaseTestCase):

    def test_get_detail(self):
        client = self.auth_client(self.token1)
        response = client.get(f'/api/categories/{self.cat1.pk}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Health')

    def test_get_detail_not_owner(self):
        client = self.auth_client(self.token2)
        response = client.get(f'/api/categories/{self.cat1.pk}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_category(self):
        client = self.auth_client(self.token1)
        response = client.put(
            f'/api/categories/{self.cat1.pk}/',
            {'name': 'Fitness', 'colour': '#10B981'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Fitness')

    def test_update_category_duplicate_name(self):
        client = self.auth_client(self.token1)
        response = client.put(
            f'/api/categories/{self.cat1.pk}/',
            {'name': 'Work'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_category(self):
        client = self.auth_client(self.token1)
        response = client.delete(f'/api/categories/{self.cat1.pk}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Category.objects.filter(pk=self.cat1.pk).exists())

    def test_delete_category_not_owner(self):
        client = self.auth_client(self.token2)
        response = client.delete(f'/api/categories/{self.cat1.pk}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_category_not_found(self):
        client = self.auth_client(self.token1)
        response = client.get('/api/categories/9999/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_category_has_hateoas_links(self):
        client = self.auth_client(self.token1)
        response = client.get(f'/api/categories/{self.cat1.pk}/')
        self.assertIn('links', response.data)
        self.assertIn('self', response.data['links'])
        self.assertEqual(response.data['links']['self'], f'/api/categories/{self.cat1.pk}/')


# ═══════════════════════════════════════════════════════════════
# Habits (Task 4)
# ═══════════════════════════════════════════════════════════════

class HabitListTests(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.habit1 = Habit.objects.create(
            user=self.user1, name='Morning run', category=self.cat1,
            target_frequency='daily',
        )
        self.habit2 = Habit.objects.create(
            user=self.user1, name='Read 30 pages', target_frequency='daily',
        )
        self.habit_inactive = Habit.objects.create(
            user=self.user1, name='Old habit', is_active=False,
        )

    def test_list_requires_auth(self):
        response = self.client.get('/api/habits/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_returns_own_habits(self):
        client = self.auth_client(self.token1)
        response = client.get('/api/habits/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 3)

    def test_list_filter_active_true(self):
        client = self.auth_client(self.token1)
        response = client.get('/api/habits/?active=true')
        self.assertEqual(response.data['count'], 2)

    def test_list_filter_active_false(self):
        client = self.auth_client(self.token1)
        response = client.get('/api/habits/?active=false')
        self.assertEqual(response.data['count'], 1)

    def test_list_is_paginated(self):
        client = self.auth_client(self.token1)
        response = client.get('/api/habits/')
        self.assertIn('count', response.data)
        self.assertIn('results', response.data)

    def test_create_habit_success(self):
        client = self.auth_client(self.token1)
        data = {'name': 'Meditate', 'target_frequency': 'daily', 'category': self.cat1.pk}
        response = client.post('/api/habits/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Meditate')
        self.assertEqual(response.data['category_name'], 'Health')

    def test_create_habit_minimal(self):
        client = self.auth_client(self.token1)
        data = {'name': 'Stretch'}
        response = client.post('/api/habits/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['target_frequency'], 'daily')

    def test_create_habit_missing_name(self):
        client = self.auth_client(self.token1)
        response = client.post('/api/habits/', {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_habit_duplicate_name(self):
        client = self.auth_client(self.token1)
        data = {'name': 'Morning run'}
        response = client.post('/api/habits/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_habit_invalid_frequency(self):
        client = self.auth_client(self.token1)
        data = {'name': 'New habit', 'target_frequency': 'monthly'}
        response = client.post('/api/habits/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_habit_other_users_category_rejected(self):
        client = self.auth_client(self.token1)
        data = {'name': 'Sneaky', 'category': self.cat_bob.pk}
        response = client.post('/api/habits/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class HabitDetailTests(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.habit = Habit.objects.create(
            user=self.user1, name='Morning run', category=self.cat1,
        )
        self.entry = HabitEntry.objects.create(
            habit=self.habit, date=date.today(),
        )

    def test_get_detail_with_recent_entries(self):
        client = self.auth_client(self.token1)
        response = client.get(f'/api/habits/{self.habit.pk}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Morning run')
        self.assertIn('recent_entries', response.data)
        self.assertEqual(len(response.data['recent_entries']), 1)

    def test_get_detail_not_owner(self):
        client = self.auth_client(self.token2)
        response = client.get(f'/api/habits/{self.habit.pk}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_habit(self):
        client = self.auth_client(self.token1)
        response = client.put(
            f'/api/habits/{self.habit.pk}/',
            {'name': 'Evening run', 'target_frequency': 'weekly'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Evening run')
        self.assertEqual(response.data['target_frequency'], 'weekly')

    def test_update_habit_partial(self):
        client = self.auth_client(self.token1)
        response = client.put(
            f'/api/habits/{self.habit.pk}/',
            {'is_active': False},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['is_active'])

    def test_delete_habit_cascades_entries(self):
        client = self.auth_client(self.token1)
        response = client.delete(f'/api/habits/{self.habit.pk}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Habit.objects.filter(pk=self.habit.pk).exists())
        self.assertFalse(HabitEntry.objects.filter(pk=self.entry.pk).exists())

    def test_habit_has_hateoas_links(self):
        client = self.auth_client(self.token1)
        response = client.get(f'/api/habits/{self.habit.pk}/')
        self.assertIn('links', response.data)
        self.assertIn('self', response.data['links'])
        self.assertIn('entries', response.data['links'])

    def test_habit_not_found(self):
        client = self.auth_client(self.token1)
        response = client.get('/api/habits/9999/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# ═══════════════════════════════════════════════════════════════
# Habit Entries (Task 5)
# ═══════════════════════════════════════════════════════════════

class HabitEntryListTests(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.habit = Habit.objects.create(user=self.user1, name='Meditate')
        self.entry1 = HabitEntry.objects.create(
            habit=self.habit, date=date.today() - timedelta(days=1),
        )
        self.entry2 = HabitEntry.objects.create(
            habit=self.habit, date=date.today() - timedelta(days=2),
        )

    def test_list_entries_requires_auth(self):
        response = self.client.get(f'/api/habits/{self.habit.pk}/entries/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_entries(self):
        client = self.auth_client(self.token1)
        response = client.get(f'/api/habits/{self.habit.pk}/entries/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)

    def test_list_entries_not_owner(self):
        client = self.auth_client(self.token2)
        response = client.get(f'/api/habits/{self.habit.pk}/entries/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_entry_success(self):
        client = self.auth_client(self.token1)
        data = {'date': str(date.today()), 'notes': 'Felt great'}
        response = client.post(f'/api/habits/{self.habit.pk}/entries/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['notes'], 'Felt great')

    def test_create_entry_missing_date(self):
        client = self.auth_client(self.token1)
        response = client.post(f'/api/habits/{self.habit.pk}/entries/', {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_entry_invalid_date_format(self):
        client = self.auth_client(self.token1)
        data = {'date': '17-03-2026'}
        response = client.post(f'/api/habits/{self.habit.pk}/entries/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_entry_future_date_rejected(self):
        client = self.auth_client(self.token1)
        future = date.today() + timedelta(days=5)
        data = {'date': str(future)}
        response = client.post(f'/api/habits/{self.habit.pk}/entries/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_entry_duplicate_date_rejected(self):
        client = self.auth_client(self.token1)
        data = {'date': str(date.today() - timedelta(days=1))}
        response = client.post(f'/api/habits/{self.habit.pk}/entries/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_entry_not_owner(self):
        client = self.auth_client(self.token2)
        data = {'date': str(date.today())}
        response = client.post(f'/api/habits/{self.habit.pk}/entries/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_entries_paginated(self):
        client = self.auth_client(self.token1)
        response = client.get(f'/api/habits/{self.habit.pk}/entries/')
        self.assertIn('count', response.data)
        self.assertIn('results', response.data)


class HabitEntryDetailTests(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.habit = Habit.objects.create(user=self.user1, name='Meditate')
        self.entry = HabitEntry.objects.create(
            habit=self.habit, date=date.today(),
        )

    def test_get_entry_detail(self):
        client = self.auth_client(self.token1)
        response = client.get(
            f'/api/habits/{self.habit.pk}/entries/{self.entry.pk}/'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['date'], str(date.today()))

    def test_delete_entry(self):
        client = self.auth_client(self.token1)
        response = client.delete(
            f'/api/habits/{self.habit.pk}/entries/{self.entry.pk}/'
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(HabitEntry.objects.filter(pk=self.entry.pk).exists())

    def test_delete_entry_not_owner(self):
        client = self.auth_client(self.token2)
        response = client.delete(
            f'/api/habits/{self.habit.pk}/entries/{self.entry.pk}/'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_entry_has_hateoas_links(self):
        client = self.auth_client(self.token1)
        response = client.get(
            f'/api/habits/{self.habit.pk}/entries/{self.entry.pk}/'
        )
        self.assertIn('links', response.data)
        self.assertIn('self', response.data['links'])
        self.assertIn('habit', response.data['links'])

    def test_entry_not_found(self):
        client = self.auth_client(self.token1)
        response = client.get(f'/api/habits/{self.habit.pk}/entries/9999/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_entry_wrong_habit(self):
        """Entry ID exists but under a different habit — should 404."""
        other_habit = Habit.objects.create(user=self.user1, name='Other')
        client = self.auth_client(self.token1)
        response = client.get(
            f'/api/habits/{other_habit.pk}/entries/{self.entry.pk}/'
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# ═══════════════════════════════════════════════════════════════
# Tasks (Task 6)
# ═══════════════════════════════════════════════════════════════

class TaskListTests(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.task1 = Task.objects.create(
            user=self.user1, title='Write report', priority='high',
            status='pending', category=self.cat2,
        )
        self.task2 = Task.objects.create(
            user=self.user1, title='Buy groceries', priority='low',
            status='completed', completed_at=timezone.now(),
        )
        self.task3 = Task.objects.create(
            user=self.user1, title='Code review', priority='medium',
            status='in_progress',
        )

    def test_list_requires_auth(self):
        response = self.client.get('/api/tasks/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_returns_own_tasks(self):
        client = self.auth_client(self.token1)
        response = client.get('/api/tasks/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 3)

    def test_list_filter_by_status(self):
        client = self.auth_client(self.token1)
        response = client.get('/api/tasks/?status=pending')
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['title'], 'Write report')

    def test_list_filter_by_priority(self):
        client = self.auth_client(self.token1)
        response = client.get('/api/tasks/?priority=high')
        self.assertEqual(response.data['count'], 1)

    def test_list_is_paginated(self):
        client = self.auth_client(self.token1)
        response = client.get('/api/tasks/')
        self.assertIn('count', response.data)
        self.assertIn('results', response.data)

    def test_create_task_success(self):
        client = self.auth_client(self.token1)
        data = {
            'title': 'Deploy API',
            'priority': 'high',
            'category': self.cat2.pk,
            'due_date': '2026-04-01',
        }
        response = client.post('/api/tasks/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], 'Deploy API')
        self.assertEqual(response.data['status'], 'pending')
        self.assertEqual(response.data['category_name'], 'Work')
        self.assertIsNone(response.data['completed_at'])

    def test_create_task_minimal(self):
        client = self.auth_client(self.token1)
        data = {'title': 'Quick task'}
        response = client.post('/api/tasks/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['priority'], 'medium')
        self.assertEqual(response.data['status'], 'pending')

    def test_create_task_missing_title(self):
        client = self.auth_client(self.token1)
        response = client.post('/api/tasks/', {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_task_invalid_priority(self):
        client = self.auth_client(self.token1)
        data = {'title': 'Bad task', 'priority': 'urgent'}
        response = client.post('/api/tasks/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_task_invalid_status(self):
        client = self.auth_client(self.token1)
        data = {'title': 'Bad task', 'status': 'done'}
        response = client.post('/api/tasks/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_task_other_users_category_rejected(self):
        client = self.auth_client(self.token1)
        data = {'title': 'Sneaky task', 'category': self.cat_bob.pk}
        response = client.post('/api/tasks/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_task_completed_sets_timestamp(self):
        client = self.auth_client(self.token1)
        data = {'title': 'Already done', 'status': 'completed'}
        response = client.post('/api/tasks/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNotNone(response.data['completed_at'])


class TaskDetailTests(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.task = Task.objects.create(
            user=self.user1, title='Write report', priority='high',
            status='pending', category=self.cat2,
        )

    def test_get_detail(self):
        client = self.auth_client(self.token1)
        response = client.get(f'/api/tasks/{self.task.pk}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Write report')

    def test_get_detail_not_owner(self):
        client = self.auth_client(self.token2)
        response = client.get(f'/api/tasks/{self.task.pk}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_task_partial(self):
        client = self.auth_client(self.token1)
        response = client.put(
            f'/api/tasks/{self.task.pk}/',
            {'priority': 'low'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['priority'], 'low')

    def test_update_task_to_completed_sets_timestamp(self):
        client = self.auth_client(self.token1)
        response = client.put(
            f'/api/tasks/{self.task.pk}/',
            {'status': 'completed'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'completed')
        self.assertIsNotNone(response.data['completed_at'])

    def test_update_task_from_completed_clears_timestamp(self):
        self.task.status = 'completed'
        self.task.completed_at = timezone.now()
        self.task.save()

        client = self.auth_client(self.token1)
        response = client.put(
            f'/api/tasks/{self.task.pk}/',
            {'status': 'in_progress'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'in_progress')
        self.assertIsNone(response.data['completed_at'])

    def test_delete_task(self):
        client = self.auth_client(self.token1)
        response = client.delete(f'/api/tasks/{self.task.pk}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Task.objects.filter(pk=self.task.pk).exists())

    def test_delete_task_not_owner(self):
        client = self.auth_client(self.token2)
        response = client.delete(f'/api/tasks/{self.task.pk}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_task_has_hateoas_links(self):
        client = self.auth_client(self.token1)
        response = client.get(f'/api/tasks/{self.task.pk}/')
        self.assertIn('links', response.data)
        self.assertIn('self', response.data['links'])
        self.assertIn('tasks_list', response.data['links'])

    def test_task_not_found(self):
        client = self.auth_client(self.token1)
        response = client.get('/api/tasks/9999/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_task_invalid_priority(self):
        client = self.auth_client(self.token1)
        response = client.put(
            f'/api/tasks/{self.task.pk}/',
            {'priority': 'critical'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# ═══════════════════════════════════════════════════════════════
# Model Constraints & __str__
# ═══════════════════════════════════════════════════════════════

class ModelTests(BaseTestCase):

    def test_category_str(self):
        self.assertEqual(str(self.cat1), 'Health (alice)')

    def test_habit_str(self):
        habit = Habit.objects.create(user=self.user1, name='Run')
        self.assertEqual(str(habit), 'Run (alice)')

    def test_habit_entry_str(self):
        habit = Habit.objects.create(user=self.user1, name='Run')
        entry = HabitEntry.objects.create(habit=habit, date=date(2026, 3, 17))
        self.assertEqual(str(entry), 'Run — 2026-03-17')

    def test_task_str(self):
        task = Task.objects.create(user=self.user1, title='Deploy', status='pending')
        self.assertEqual(str(task), 'Deploy [pending] (alice)')

    def test_timelog_str(self):
        tl = TimeLog.objects.create(
            user=self.user1, title='Coding', duration_minutes=60,
            date=date(2026, 3, 17),
        )
        self.assertEqual(str(tl), 'Coding — 60min on 2026-03-17 (alice)')

    def test_category_unique_together(self):
        with self.assertRaises(Exception):
            Category.objects.create(user=self.user1, name='Health')

    def test_habit_unique_together(self):
        Habit.objects.create(user=self.user1, name='Run')
        with self.assertRaises(Exception):
            Habit.objects.create(user=self.user1, name='Run')

    def test_habit_entry_unique_together(self):
        habit = Habit.objects.create(user=self.user1, name='Run')
        HabitEntry.objects.create(habit=habit, date=date.today())
        with self.assertRaises(Exception):
            HabitEntry.objects.create(habit=habit, date=date.today())

    def test_category_cascade_sets_null_on_habit(self):
        """Deleting a category sets habit.category to NULL, not cascade delete."""
        habit = Habit.objects.create(
            user=self.user1, name='Test', category=self.cat1,
        )
        self.cat1.delete()
        habit.refresh_from_db()
        self.assertIsNone(habit.category)

    def test_habit_cascade_deletes_entries(self):
        habit = Habit.objects.create(user=self.user1, name='Temp')
        HabitEntry.objects.create(habit=habit, date=date.today())
        entry_count = HabitEntry.objects.count()
        habit.delete()
        self.assertEqual(HabitEntry.objects.count(), entry_count - 1)


# ═══════════════════════════════════════════════════════════════
# Time Logs (Task 7)
# ═══════════════════════════════════════════════════════════════

class TimeLogListTests(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.tl1 = TimeLog.objects.create(
            user=self.user1, title='Coding session', category=self.cat2,
            duration_minutes=90, date=date.today(),
        )
        self.tl2 = TimeLog.objects.create(
            user=self.user1, title='Morning jog', category=self.cat1,
            duration_minutes=30, date=date.today() - timedelta(days=1),
        )
        self.tl3 = TimeLog.objects.create(
            user=self.user1, title='Reading',
            duration_minutes=45, date=date.today() - timedelta(days=5),
        )

    def test_list_requires_auth(self):
        response = self.client.get('/api/timelogs/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_returns_own_timelogs(self):
        client = self.auth_client(self.token1)
        response = client.get('/api/timelogs/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 3)

    def test_list_is_paginated(self):
        client = self.auth_client(self.token1)
        response = client.get('/api/timelogs/')
        self.assertIn('count', response.data)
        self.assertIn('results', response.data)

    def test_list_filter_by_category(self):
        client = self.auth_client(self.token1)
        response = client.get(f'/api/timelogs/?category={self.cat2.pk}')
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['title'], 'Coding session')

    def test_list_filter_by_date_range(self):
        client = self.auth_client(self.token1)
        from_date = str(date.today() - timedelta(days=2))
        to_date = str(date.today())
        response = client.get(f'/api/timelogs/?date_from={from_date}&date_to={to_date}')
        self.assertEqual(response.data['count'], 2)

    def test_create_timelog_success(self):
        client = self.auth_client(self.token1)
        data = {
            'title': 'Study Django',
            'duration_minutes': 60,
            'date': str(date.today()),
            'category': self.cat2.pk,
            'notes': 'DRF serializers',
        }
        response = client.post('/api/timelogs/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], 'Study Django')
        self.assertEqual(response.data['duration_minutes'], 60)
        self.assertEqual(response.data['category_name'], 'Work')

    def test_create_timelog_minimal(self):
        client = self.auth_client(self.token1)
        data = {'title': 'Quick task', 'duration_minutes': 15, 'date': str(date.today())}
        response = client.post('/api/timelogs/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_timelog_missing_title(self):
        client = self.auth_client(self.token1)
        data = {'duration_minutes': 60, 'date': str(date.today())}
        response = client.post('/api/timelogs/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_timelog_missing_duration(self):
        client = self.auth_client(self.token1)
        data = {'title': 'No duration', 'date': str(date.today())}
        response = client.post('/api/timelogs/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_timelog_zero_duration_rejected(self):
        client = self.auth_client(self.token1)
        data = {'title': 'Zero', 'duration_minutes': 0, 'date': str(date.today())}
        response = client.post('/api/timelogs/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_timelog_negative_duration_rejected(self):
        client = self.auth_client(self.token1)
        data = {'title': 'Neg', 'duration_minutes': -10, 'date': str(date.today())}
        response = client.post('/api/timelogs/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_timelog_missing_date(self):
        client = self.auth_client(self.token1)
        data = {'title': 'No date', 'duration_minutes': 30}
        response = client.post('/api/timelogs/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_timelog_future_date_rejected(self):
        client = self.auth_client(self.token1)
        future = date.today() + timedelta(days=5)
        data = {'title': 'Future', 'duration_minutes': 30, 'date': str(future)}
        response = client.post('/api/timelogs/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_timelog_invalid_date(self):
        client = self.auth_client(self.token1)
        data = {'title': 'Bad date', 'duration_minutes': 30, 'date': 'not-a-date'}
        response = client.post('/api/timelogs/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_timelog_other_users_category_rejected(self):
        client = self.auth_client(self.token1)
        data = {
            'title': 'Sneaky', 'duration_minutes': 30,
            'date': str(date.today()), 'category': self.cat_bob.pk,
        }
        response = client.post('/api/timelogs/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TimeLogDetailTests(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.tl = TimeLog.objects.create(
            user=self.user1, title='Coding', category=self.cat2,
            duration_minutes=120, date=date.today(),
        )

    def test_get_detail(self):
        client = self.auth_client(self.token1)
        response = client.get(f'/api/timelogs/{self.tl.pk}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Coding')
        self.assertEqual(response.data['duration_minutes'], 120)

    def test_get_detail_not_owner(self):
        client = self.auth_client(self.token2)
        response = client.get(f'/api/timelogs/{self.tl.pk}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_timelog(self):
        client = self.auth_client(self.token1)
        response = client.put(
            f'/api/timelogs/{self.tl.pk}/',
            {'title': 'Deep work', 'duration_minutes': 180},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Deep work')
        self.assertEqual(response.data['duration_minutes'], 180)

    def test_update_timelog_partial(self):
        client = self.auth_client(self.token1)
        response = client.put(
            f'/api/timelogs/{self.tl.pk}/',
            {'notes': 'Added notes'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['notes'], 'Added notes')
        self.assertEqual(response.data['title'], 'Coding')  # unchanged

    def test_update_timelog_invalid_duration(self):
        client = self.auth_client(self.token1)
        response = client.put(
            f'/api/timelogs/{self.tl.pk}/',
            {'duration_minutes': -5},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_timelog(self):
        client = self.auth_client(self.token1)
        response = client.delete(f'/api/timelogs/{self.tl.pk}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(TimeLog.objects.filter(pk=self.tl.pk).exists())

    def test_delete_timelog_not_owner(self):
        client = self.auth_client(self.token2)
        response = client.delete(f'/api/timelogs/{self.tl.pk}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_timelog_has_hateoas_links(self):
        client = self.auth_client(self.token1)
        response = client.get(f'/api/timelogs/{self.tl.pk}/')
        self.assertIn('links', response.data)
        self.assertIn('self', response.data['links'])
        self.assertIn('timelogs_list', response.data['links'])
        self.assertIn('analytics_heatmap', response.data['links'])

    def test_timelog_not_found(self):
        client = self.auth_client(self.token1)
        response = client.get('/api/timelogs/9999/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# ═══════════════════════════════════════════════════════════════
# Analytics — Streaks (Task 8)
# ═══════════════════════════════════════════════════════════════

class AnalyticsStreaksTests(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.habit = Habit.objects.create(user=self.user1, name='Meditate')
        self.habit2 = Habit.objects.create(user=self.user1, name='Read')
        # Inactive habit should be excluded
        self.habit_inactive = Habit.objects.create(
            user=self.user1, name='Old habit', is_active=False,
        )

    def test_streaks_requires_auth(self):
        response = self.client.get('/api/analytics/streaks/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_streaks_empty(self):
        client = self.auth_client(self.token1)
        response = client.get('/api/analytics/streaks/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Two active habits, zero streaks
        self.assertEqual(len(response.data), 2)
        for item in response.data:
            self.assertEqual(item['current_streak'], 0)
            self.assertEqual(item['longest_streak'], 0)

    def test_streaks_excludes_inactive(self):
        client = self.auth_client(self.token1)
        response = client.get('/api/analytics/streaks/')
        habit_names = [item['habit_name'] for item in response.data]
        self.assertNotIn('Old habit', habit_names)

    def test_current_streak_counts_consecutive_ending_today(self):
        today = date.today()
        for i in range(5):
            HabitEntry.objects.create(
                habit=self.habit, date=today - timedelta(days=i),
            )
        client = self.auth_client(self.token1)
        response = client.get('/api/analytics/streaks/')
        meditate = next(h for h in response.data if h['habit_name'] == 'Meditate')
        self.assertEqual(meditate['current_streak'], 5)

    def test_current_streak_counts_consecutive_ending_yesterday(self):
        """Streak still counts if last entry was yesterday (haven't done today yet)."""
        today = date.today()
        for i in range(1, 4):
            HabitEntry.objects.create(
                habit=self.habit, date=today - timedelta(days=i),
            )
        client = self.auth_client(self.token1)
        response = client.get('/api/analytics/streaks/')
        meditate = next(h for h in response.data if h['habit_name'] == 'Meditate')
        self.assertEqual(meditate['current_streak'], 3)

    def test_current_streak_zero_if_gap(self):
        """No current streak if last entry was 2+ days ago."""
        today = date.today()
        HabitEntry.objects.create(habit=self.habit, date=today - timedelta(days=3))
        HabitEntry.objects.create(habit=self.habit, date=today - timedelta(days=4))
        client = self.auth_client(self.token1)
        response = client.get('/api/analytics/streaks/')
        meditate = next(h for h in response.data if h['habit_name'] == 'Meditate')
        self.assertEqual(meditate['current_streak'], 0)
        self.assertEqual(meditate['longest_streak'], 2)

    def test_longest_streak_historical(self):
        """Longest streak can be from the past, not necessarily current."""
        today = date.today()
        # Old streak of 7 days, 20 days ago
        for i in range(20, 13, -1):
            HabitEntry.objects.create(
                habit=self.habit, date=today - timedelta(days=i),
            )
        # Current streak of 2
        HabitEntry.objects.create(habit=self.habit, date=today)
        HabitEntry.objects.create(habit=self.habit, date=today - timedelta(days=1))

        client = self.auth_client(self.token1)
        response = client.get('/api/analytics/streaks/')
        meditate = next(h for h in response.data if h['habit_name'] == 'Meditate')
        self.assertEqual(meditate['current_streak'], 2)
        self.assertEqual(meditate['longest_streak'], 7)

    def test_streaks_has_hateoas_links(self):
        client = self.auth_client(self.token1)
        response = client.get('/api/analytics/streaks/')
        for item in response.data:
            self.assertIn('links', item)
            self.assertIn('habit', item['links'])
            self.assertIn('entries', item['links'])

    def test_streaks_has_total_entries(self):
        today = date.today()
        for i in range(3):
            HabitEntry.objects.create(
                habit=self.habit, date=today - timedelta(days=i),
            )
        client = self.auth_client(self.token1)
        response = client.get('/api/analytics/streaks/')
        meditate = next(h for h in response.data if h['habit_name'] == 'Meditate')
        self.assertEqual(meditate['total_entries'], 3)


# ═══════════════════════════════════════════════════════════════
# Analytics — Heatmap (Task 8)
# ═══════════════════════════════════════════════════════════════

class AnalyticsHeatmapTests(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.habit = Habit.objects.create(user=self.user1, name='Run')
        self.today = date.today()

    def test_heatmap_requires_auth(self):
        response = self.client.get('/api/analytics/heatmap/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_heatmap_default_30_days(self):
        client = self.auth_client(self.token1)
        response = client.get('/api/analytics/heatmap/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['data']), 30)
        self.assertIn('period', response.data)
        self.assertIn('total_active_days', response.data)

    def test_heatmap_custom_days(self):
        client = self.auth_client(self.token1)
        response = client.get('/api/analytics/heatmap/?days=7')
        self.assertEqual(len(response.data['data']), 7)

    def test_heatmap_max_365_days(self):
        client = self.auth_client(self.token1)
        response = client.get('/api/analytics/heatmap/?days=999')
        self.assertEqual(len(response.data['data']), 365)

    def test_heatmap_counts_habit_entries(self):
        HabitEntry.objects.create(habit=self.habit, date=self.today)
        HabitEntry.objects.create(
            habit=Habit.objects.create(user=self.user1, name='Read'),
            date=self.today,
        )
        client = self.auth_client(self.token1)
        response = client.get('/api/analytics/heatmap/?days=1')
        day_data = response.data['data'][0]
        self.assertEqual(day_data['date'], str(self.today))
        self.assertEqual(day_data['habit_entries'], 2)

    def test_heatmap_counts_completed_tasks(self):
        Task.objects.create(
            user=self.user1, title='Done task', status='completed',
            completed_at=timezone.now(),
        )
        client = self.auth_client(self.token1)
        response = client.get('/api/analytics/heatmap/?days=1')
        day_data = response.data['data'][0]
        self.assertEqual(day_data['tasks_completed'], 1)

    def test_heatmap_counts_timelogs(self):
        TimeLog.objects.create(
            user=self.user1, title='Work', duration_minutes=60,
            date=self.today,
        )
        client = self.auth_client(self.token1)
        response = client.get('/api/analytics/heatmap/?days=1')
        day_data = response.data['data'][0]
        self.assertEqual(day_data['time_logs'], 1)

    def test_heatmap_total_is_sum(self):
        HabitEntry.objects.create(habit=self.habit, date=self.today)
        Task.objects.create(
            user=self.user1, title='T', status='completed',
            completed_at=timezone.now(),
        )
        TimeLog.objects.create(
            user=self.user1, title='W', duration_minutes=30,
            date=self.today,
        )
        client = self.auth_client(self.token1)
        response = client.get('/api/analytics/heatmap/?days=1')
        day_data = response.data['data'][0]
        self.assertEqual(day_data['total'], 3)
        self.assertEqual(response.data['total_active_days'], 1)

    def test_heatmap_empty_days_have_zero(self):
        client = self.auth_client(self.token1)
        response = client.get('/api/analytics/heatmap/?days=7')
        for day_data in response.data['data']:
            self.assertEqual(day_data['total'], 0)
        self.assertEqual(response.data['total_active_days'], 0)

    def test_heatmap_does_not_leak_other_users(self):
        """Bob's data should not appear in Alice's heatmap."""
        bob_habit = Habit.objects.create(user=self.user2, name='Bob run')
        HabitEntry.objects.create(habit=bob_habit, date=self.today)
        client = self.auth_client(self.token1)
        response = client.get('/api/analytics/heatmap/?days=1')
        day_data = response.data['data'][0]
        self.assertEqual(day_data['habit_entries'], 0)


# ═══════════════════════════════════════════════════════════════
# Analytics — Summary (Task 8)
# ═══════════════════════════════════════════════════════════════

class AnalyticsSummaryTests(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.today = date.today()
        self.habit = Habit.objects.create(user=self.user1, name='Run')
        self.habit2 = Habit.objects.create(user=self.user1, name='Read')

    def test_summary_requires_auth(self):
        response = self.client.get('/api/analytics/summary/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_summary_default_period_is_week(self):
        client = self.auth_client(self.token1)
        response = client.get('/api/analytics/summary/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['period'], 'week')

    def test_summary_month_period(self):
        client = self.auth_client(self.token1)
        response = client.get('/api/analytics/summary/?period=month')
        self.assertEqual(response.data['period'], 'month')

    def test_summary_habits_section(self):
        # 5 entries for Run, 2 for Read this week
        for i in range(5):
            HabitEntry.objects.create(
                habit=self.habit, date=self.today - timedelta(days=i),
            )
        for i in range(2):
            HabitEntry.objects.create(
                habit=self.habit2, date=self.today - timedelta(days=i),
            )
        client = self.auth_client(self.token1)
        response = client.get('/api/analytics/summary/')
        habits = response.data['habits']
        self.assertEqual(habits['total_active'], 2)
        self.assertEqual(habits['total_entries'], 7)
        # completion_rate = 7 / (2 habits * 7 days) = 0.5
        self.assertEqual(habits['completion_rate'], 0.5)
        self.assertEqual(habits['best_habit']['name'], 'Run')
        self.assertEqual(habits['best_habit']['entries'], 5)
        self.assertEqual(habits['worst_habit']['name'], 'Read')
        self.assertEqual(habits['worst_habit']['entries'], 2)

    def test_summary_tasks_section(self):
        Task.objects.create(
            user=self.user1, title='T1', status='completed',
            priority='high', completed_at=timezone.now(),
        )
        Task.objects.create(
            user=self.user1, title='T2', status='completed',
            priority='low', completed_at=timezone.now(),
        )
        Task.objects.create(
            user=self.user1, title='T3', status='pending', priority='medium',
        )
        client = self.auth_client(self.token1)
        response = client.get('/api/analytics/summary/')
        tasks = response.data['tasks']
        self.assertEqual(tasks['total_created'], 3)
        self.assertEqual(tasks['total_completed'], 2)
        self.assertAlmostEqual(tasks['completion_rate'], 0.67)
        self.assertEqual(tasks['by_priority']['high'], 1)
        self.assertEqual(tasks['by_priority']['low'], 1)
        self.assertEqual(tasks['by_priority']['medium'], 0)

    def test_summary_timelogs_section(self):
        TimeLog.objects.create(
            user=self.user1, title='Coding', category=self.cat2,
            duration_minutes=120, date=self.today,
        )
        TimeLog.objects.create(
            user=self.user1, title='More coding', category=self.cat2,
            duration_minutes=60, date=self.today - timedelta(days=1),
        )
        TimeLog.objects.create(
            user=self.user1, title='Gym', category=self.cat1,
            duration_minutes=45, date=self.today,
        )
        client = self.auth_client(self.token1)
        response = client.get('/api/analytics/summary/')
        tl = response.data['time_logs']
        self.assertEqual(tl['total_entries'], 3)
        self.assertEqual(tl['total_minutes'], 225)
        # daily_average = 225 / 7 = 32.1
        self.assertAlmostEqual(tl['daily_average_minutes'], 32.1, places=1)
        # by_category sorted descending
        self.assertEqual(tl['by_category'][0]['category'], 'Work')
        self.assertEqual(tl['by_category'][0]['minutes'], 180)
        self.assertEqual(tl['by_category'][1]['category'], 'Health')
        self.assertEqual(tl['by_category'][1]['minutes'], 45)

    def test_summary_empty(self):
        client = self.auth_client(self.token1)
        response = client.get('/api/analytics/summary/')
        self.assertEqual(response.data['habits']['total_entries'], 0)
        self.assertEqual(response.data['habits']['completion_rate'], 0.0)
        self.assertIsNone(response.data['habits']['best_habit'])
        self.assertEqual(response.data['tasks']['total_created'], 0)
        self.assertEqual(response.data['tasks']['completion_rate'], 0.0)
        self.assertEqual(response.data['time_logs']['total_minutes'], 0)

    def test_summary_does_not_include_other_users(self):
        bob_habit = Habit.objects.create(user=self.user2, name='Bob habit')
        HabitEntry.objects.create(habit=bob_habit, date=self.today)
        Task.objects.create(
            user=self.user2, title='Bob task', status='completed',
            completed_at=timezone.now(),
        )
        client = self.auth_client(self.token1)
        response = client.get('/api/analytics/summary/')
        self.assertEqual(response.data['habits']['total_entries'], 0)
        self.assertEqual(response.data['tasks']['total_completed'], 0)

    def test_summary_date_range_present(self):
        client = self.auth_client(self.token1)
        response = client.get('/api/analytics/summary/')
        self.assertIn('date_range', response.data)
        self.assertIn('from', response.data['date_range'])
        self.assertIn('to', response.data['date_range'])

    def test_summary_uncategorised_timelogs(self):
        """Time logs without a category show as 'Uncategorised'."""
        TimeLog.objects.create(
            user=self.user1, title='Random', duration_minutes=30,
            date=self.today,
        )
        client = self.auth_client(self.token1)
        response = client.get('/api/analytics/summary/')
        self.assertEqual(response.data['time_logs']['by_category'][0]['category'], 'Uncategorised')


# ═══════════════════════════════════════════════════════════════
# Pagination Tests (cross-cutting)
# ═══════════════════════════════════════════════════════════════

class PaginationTests(BaseTestCase):

    def test_categories_paginated(self):
        client = self.auth_client(self.token1)
        response = client.get('/api/categories/')
        for key in ('count', 'next', 'previous', 'results'):
            self.assertIn(key, response.data)

    def test_habits_paginated(self):
        client = self.auth_client(self.token1)
        response = client.get('/api/habits/')
        self.assertIn('results', response.data)

    def test_tasks_paginated(self):
        client = self.auth_client(self.token1)
        response = client.get('/api/tasks/')
        self.assertIn('results', response.data)

    def test_timelogs_paginated(self):
        client = self.auth_client(self.token1)
        response = client.get('/api/timelogs/')
        self.assertIn('results', response.data)
