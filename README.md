# Productivity & Habit Analytics API

A RESTful web API that tracks tasks, habits, time logs, and completion patterns, offering endpoints for streak calculations, productivity heatmaps, and behavioural summaries. Built with Django and Django REST Framework for COMP3011 Web Services and Web Data coursework at the University of Leeds.

## Tech Stack

- **Language:** Python 3
- **Framework:** Django 4.2 + Django REST Framework 3.14
- **Database:** SQLite (SQL-based, as required by the brief)
- **Authentication:** Token-based (DRF TokenAuthentication)

## Setup Instructions

```bash
git clone <repository-url>
cd productivity_api
python -m venv venv && source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py makemigrations tracker
python manage.py migrate
python manage.py seed_data
python manage.py runserver
```

Access the API at `http://127.0.0.1:8000/api/`

Demo accounts created by `seed_data`:
- `alice / demopass123` (primary user with rich data)
- `bob / demopass123` (secondary user)

## API Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/register/` | Register new user | No |
| POST | `/api/login/` | Login, get token | No |
| GET/POST | `/api/categories/` | List / create categories | Yes |
| GET/PUT/DELETE | `/api/categories/<id>/` | Category detail / update / delete | Owner |
| GET/POST | `/api/habits/` | List / create habits | Yes |
| GET/PUT/DELETE | `/api/habits/<id>/` | Habit detail / update / delete | Owner |
| GET/POST | `/api/habits/<id>/entries/` | List / log habit completions | Owner |
| GET/DELETE | `/api/habits/<id>/entries/<eid>/` | View / remove entry | Owner |
| GET/POST | `/api/tasks/` | List / create tasks | Yes |
| GET/PUT/DELETE | `/api/tasks/<id>/` | Task detail / update / delete | Owner |
| GET/POST | `/api/timelogs/` | List / create time logs | Yes |
| GET/PUT/DELETE | `/api/timelogs/<id>/` | Time log detail / update / delete | Owner |
| GET | `/api/analytics/streaks/` | Current + longest streaks per habit | Yes |
| GET | `/api/analytics/heatmap/?days=30` | Activity counts by date | Yes |
| GET | `/api/analytics/summary/?period=week` | Behavioural summary | Yes |

## Key Features

- **HATEOAS links** in all resource responses for REST-compliant discoverability
- **Pagination** on all list endpoints (10 items per page)
- **Server-side analytics** — streaks, heatmaps, and summaries computed entirely by the server
- **Owner-only permissions** — users can only access and modify their own data
- **Query filters** — habits by active status, tasks by status/priority, timelogs by category/date range
- **Automatic timestamps** — `completed_at` auto-managed on task status transitions
- **Comprehensive validation** — date formats, future dates, duplicates, category ownership, choice fields

## Testing

```bash
python manage.py test tracker -v 2
```

The test suite contains 149 automated tests covering authentication, CRUD, validation, ownership, analytics, HATEOAS links, pagination, model constraints, and edge cases.

## API Documentation

See [API_DOCUMENTATION.pdf](API_DOCUMENTATION.pdf) in this repository.

## Admin Panel

Access `http://127.0.0.1:8000/admin/` to manage data. Create a superuser with:

```bash
python manage.py createsuperuser
```
