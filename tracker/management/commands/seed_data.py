"""
Management command to populate the database with realistic sample data.
Usage: python manage.py seed_data
"""
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from tracker.models import Category, Habit, HabitEntry, Task, TimeLog


class Command(BaseCommand):
    help = 'Populate the database with sample productivity data for demonstration'

    def handle(self, *args, **options):
        self.stdout.write('Seeding database...')
        today = date.today()

        # ── Users ──
        user1, _ = User.objects.get_or_create(
            username='alice', defaults={'email': 'alice@example.com'}
        )
        user1.set_password('demopass123')
        user1.save()

        user2, _ = User.objects.get_or_create(
            username='bob', defaults={'email': 'bob@example.com'}
        )
        user2.set_password('demopass123')
        user2.save()
        self.stdout.write(f'  Users: {User.objects.count()}')

        # ── Categories ──
        cats = {}
        cat_data = [
            (user1, 'Health', '#22C55E'),
            (user1, 'Work', '#3B82F6'),
            (user1, 'Learning', '#A855F7'),
            (user1, 'Personal', '#F59E0B'),
            (user2, 'Fitness', '#EF4444'),
            (user2, 'Study', '#6366F1'),
        ]
        for user, name, colour in cat_data:
            cat, _ = Category.objects.get_or_create(
                user=user, name=name, defaults={'colour': colour}
            )
            cats[(user.username, name)] = cat
        self.stdout.write(f'  Categories: {Category.objects.count()}')

        # ── Habits ──
        habits = {}
        habit_data = [
            (user1, 'Morning run', 'Run 5km before 8am', cats[('alice', 'Health')], 'daily'),
            (user1, 'Read 30 pages', 'Read non-fiction for 30+ pages', cats[('alice', 'Learning')], 'daily'),
            (user1, 'Meditate', '10 minutes of mindfulness', cats[('alice', 'Health')], 'daily'),
            (user1, 'Code review', 'Review at least one PR', cats[('alice', 'Work')], 'weekly'),
            (user2, 'Gym session', 'Weight training at gym', cats[('bob', 'Fitness')], 'daily'),
            (user2, 'Study hour', 'Focused study block', cats[('bob', 'Study')], 'daily'),
        ]
        for user, name, desc, cat, freq in habit_data:
            habit, _ = Habit.objects.get_or_create(
                user=user, name=name,
                defaults={'description': desc, 'category': cat, 'target_frequency': freq}
            )
            habits[(user.username, name)] = habit
        self.stdout.write(f'  Habits: {Habit.objects.count()}')

        # ── Habit Entries — create realistic streaks ──
        entry_count = 0

        # Alice: Morning run — 12-day streak ending today
        for i in range(12):
            _, created = HabitEntry.objects.get_or_create(
                habit=habits[('alice', 'Morning run')],
                date=today - timedelta(days=i),
            )
            if created:
                entry_count += 1

        # Alice: Read — 8-day streak ending today, plus older block
        for i in range(8):
            _, created = HabitEntry.objects.get_or_create(
                habit=habits[('alice', 'Read 30 pages')],
                date=today - timedelta(days=i),
            )
            if created:
                entry_count += 1
        for i in range(20, 35):
            _, created = HabitEntry.objects.get_or_create(
                habit=habits[('alice', 'Read 30 pages')],
                date=today - timedelta(days=i),
            )
            if created:
                entry_count += 1

        # Alice: Meditate — scattered entries (not every day)
        for i in [0, 1, 2, 4, 5, 7, 10, 11, 14, 18, 21, 25]:
            _, created = HabitEntry.objects.get_or_create(
                habit=habits[('alice', 'Meditate')],
                date=today - timedelta(days=i),
            )
            if created:
                entry_count += 1

        # Alice: Code review — weekly, so scattered
        for i in [0, 6, 13, 20, 27]:
            _, created = HabitEntry.objects.get_or_create(
                habit=habits[('alice', 'Code review')],
                date=today - timedelta(days=i),
            )
            if created:
                entry_count += 1

        # Bob: Gym — 5-day streak ending yesterday
        for i in range(1, 6):
            _, created = HabitEntry.objects.get_or_create(
                habit=habits[('bob', 'Gym session')],
                date=today - timedelta(days=i),
            )
            if created:
                entry_count += 1

        # Bob: Study — scattered
        for i in [0, 1, 3, 4, 7, 8, 12, 15]:
            _, created = HabitEntry.objects.get_or_create(
                habit=habits[('bob', 'Study hour')],
                date=today - timedelta(days=i),
            )
            if created:
                entry_count += 1

        self.stdout.write(f'  Habit entries: {HabitEntry.objects.count()} ({entry_count} new)')

        # ── Tasks ──
        task_data = [
            (user1, 'Finish coursework', 'Complete COMP3011 API project', 'high', 'in_progress', cats[('alice', 'Work')], today + timedelta(days=6), None),
            (user1, 'Write technical report', 'Document design choices', 'high', 'completed', cats[('alice', 'Work')], today - timedelta(days=1), timezone.now() - timedelta(days=1)),
            (user1, 'Prepare presentation', 'Create slides for oral exam', 'medium', 'pending', cats[('alice', 'Work')], today + timedelta(days=8), None),
            (user1, 'Grocery shopping', 'Weekly shop at Morrisons', 'low', 'completed', cats[('alice', 'Personal')], today, timezone.now()),
            (user1, 'Read REST paper', 'Read Fielding dissertation Ch5', 'medium', 'completed', cats[('alice', 'Learning')], today - timedelta(days=3), timezone.now() - timedelta(days=2)),
            (user1, 'Deploy to PythonAnywhere', 'Set up live demo', 'high', 'pending', cats[('alice', 'Work')], today + timedelta(days=5), None),
            (user2, 'Lab report', 'Physics lab write-up', 'high', 'in_progress', cats[('bob', 'Study')], today + timedelta(days=3), None),
            (user2, 'Renew gym membership', '', 'low', 'completed', cats[('bob', 'Fitness')], today - timedelta(days=2), timezone.now() - timedelta(days=3)),
        ]
        task_count = 0
        for user, title, desc, priority, task_status, cat, due, completed_at in task_data:
            _, created = Task.objects.get_or_create(
                user=user, title=title,
                defaults={
                    'description': desc, 'priority': priority, 'status': task_status,
                    'category': cat, 'due_date': due, 'completed_at': completed_at,
                }
            )
            if created:
                task_count += 1
        self.stdout.write(f'  Tasks: {Task.objects.count()} ({task_count} new)')

        # ── Time Logs ──
        tl_data = [
            (user1, 'Django API development', cats[('alice', 'Work')], 120, today),
            (user1, 'Django API development', cats[('alice', 'Work')], 90, today - timedelta(days=1)),
            (user1, 'Django API development', cats[('alice', 'Work')], 150, today - timedelta(days=2)),
            (user1, 'Writing tests', cats[('alice', 'Work')], 60, today),
            (user1, 'REST lectures review', cats[('alice', 'Learning')], 45, today - timedelta(days=1)),
            (user1, 'Reading (book)', cats[('alice', 'Learning')], 40, today),
            (user1, 'Morning run', cats[('alice', 'Health')], 30, today),
            (user1, 'Morning run', cats[('alice', 'Health')], 35, today - timedelta(days=1)),
            (user1, 'Meditation', cats[('alice', 'Health')], 15, today),
            (user1, 'Meal prep', cats[('alice', 'Personal')], 45, today - timedelta(days=2)),
            (user1, 'Django API development', cats[('alice', 'Work')], 180, today - timedelta(days=3)),
            (user1, 'Report writing', cats[('alice', 'Work')], 90, today - timedelta(days=4)),
            (user1, 'REST lectures review', cats[('alice', 'Learning')], 60, today - timedelta(days=5)),
            (user2, 'Gym workout', cats[('bob', 'Fitness')], 75, today),
            (user2, 'Physics revision', cats[('bob', 'Study')], 120, today),
            (user2, 'Physics revision', cats[('bob', 'Study')], 90, today - timedelta(days=1)),
        ]
        tl_count = 0
        for user, title, cat, mins, d in tl_data:
            _, created = TimeLog.objects.get_or_create(
                user=user, title=title, date=d,
                defaults={'category': cat, 'duration_minutes': mins}
            )
            if created:
                tl_count += 1
        self.stdout.write(f'  Time logs: {TimeLog.objects.count()} ({tl_count} new)')

        self.stdout.write(self.style.SUCCESS(
            f'\nDatabase seeded successfully!\n'
            f'Demo accounts:\n'
            f'  alice / demopass123  (primary demo user, rich data)\n'
            f'  bob   / demopass123  (secondary user, less data)\n'
        ))
