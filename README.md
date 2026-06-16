# Balligh+ Backend — FastAPI + PostgreSQL

Backend API for **Balligh+** — منصة الإبلاغ الذكي عن مشاكل الأحياء

## Stack

| Layer | Tech |
|---|---|
| Framework | FastAPI 0.111 |
| ORM | SQLAlchemy 2.0 |
| Migrations | Alembic |
| Database | PostgreSQL |
| Auth | JWT (python-jose) + bcrypt |
| Uploads | python-multipart + Pillow |

---
-- psql -U balligh_user -h localhost -d balligh_db -W

uvicorn main:app --host 0.0.0.0 --port 8000## Project Structure

```
balligh_backend/
├── main.py                  # FastAPI app entry point
├── seed.py                  # Sample data seeder
├── requirements.txt
├── alembic.ini
├── .env.example
├── alembic/
│   ├── env.py
│   └── versions/
│       └── 001_initial.py   # Initial migration (all tables)
├── uploads/                 # Stored images
└── app/
    ├── core/
    │   ├── config.py        # Settings (pydantic-settings)
    │   └── security.py      # JWT + password hashing + auth deps
    ├── db/
    │   └── database.py      # SQLAlchemy engine & session
    ├── models/
    │   ├── user.py
    │   ├── report.py        # Report, ReportImage, StatusHistory
    │   ├── comment.py
    │   ├── vote.py
    │   └── notification.py
    ├── schemas/             # Pydantic schemas (request/response)
    │   ├── user.py
    │   ├── report.py
    │   ├── comment.py
    │   └── notification.py
    ├── services/            # Business logic
    │   ├── report_service.py
    │   └── notification_service.py
    └── api/routes/
        ├── auth.py
        ├── users.py
        ├── reports.py
        ├── notifications.py
        └── admin.py
```

---

## Setup

### 1. Prerequisites

- Python 3.11+
- PostgreSQL running locally (or Docker)

### 2. Create & activate virtual env

```bash
python -m venv .venv
source .venv/bin/activate      # Linux / Mac
.venv\Scripts\activate         # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment

```bash
cp .env.example .env
# Edit .env and set your DATABASE_URL, SECRET_KEY, etc.
```

### 5. Create the PostgreSQL database

```sql
CREATE DATABASE balligh_db;
```

### 6. Run Alembic migrations

```bash
alembic upgrade head
```

### 7. Seed sample data (optional)

```bash
python seed.py
```

### 8. Start the server

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Swagger UI: http://localhost:8000/docs  
ReDoc: http://localhost:8000/redoc

---

## API Endpoints

### Auth
| Method | URL | Description |
|---|---|---|
| POST | `/api/auth/register` | Register new citizen |
| POST | `/api/auth/login` | Citizen login → JWT |
| POST | `/api/auth/admin/login` | Admin login → JWT |

### Reports (Public + Auth)
| Method | URL | Description |
|---|---|---|
| GET | `/api/reports` | List reports (filter: status, category, wilaya, search, page) |
| GET | `/api/reports/map` | All geo-tagged reports for the map |
| GET | `/api/reports/mine` | My reports (auth required) |
| POST | `/api/reports` | Submit new report with images (auth required) |
| GET | `/api/reports/{id}` | Report detail |
| POST | `/api/reports/{id}/vote` | Vote on a report (auth required) |
| POST | `/api/reports/{id}/comments` | Add comment (auth required) |

### Users (Auth)
| Method | URL | Description |
|---|---|---|
| GET | `/api/users/me` | My profile + stats |
| PATCH | `/api/users/me/password` | Change password |

### Notifications (Auth)
| Method | URL | Description |
|---|---|---|
| GET | `/api/notifications` | My notifications |
| POST | `/api/notifications/mark-read` | Mark all as read |
| GET | `/api/notifications/unread-count` | Unread count |
| GET | `/api/notifications/admin` | Admin notifications |
| POST | `/api/notifications/admin/mark-read` | Mark admin notifs as read |

### Admin (Admin JWT)
| Method | URL | Description |
|---|---|---|
| GET | `/api/admin/stats` | Dashboard statistics + charts data |
| GET | `/api/admin/reports` | All reports with filters |
| PATCH | `/api/admin/reports/{id}/status` | Update status & priority |
| DELETE | `/api/admin/reports/{id}` | Delete report |
| POST | `/api/admin/reports/{id}/reply` | Post official comment |
| GET | `/api/admin/users` | List all users |
| PATCH | `/api/admin/users/{id}/ban` | Toggle ban |
| DELETE | `/api/admin/users/{id}` | Delete user |
| DELETE | `/api/admin/comments/{id}` | Delete comment |
| GET | `/api/admin/export/csv` | Download CSV export |

### Static files
- `GET /uploads/{filename}` — serve uploaded images

---

## Authentication

Bearer token in the `Authorization` header:
```
Authorization: Bearer <token>
```

**Demo accounts (after seeding):**
- Citizen: `ahmed@example.com` / `citizen1`
- Citizen: `fatima@example.com` / `citizen2`
- Admin password: `admin123`

---

## Database Schema

```
users ──< reports ──< report_images
            │    ──< status_history
            │    ──< comments
            │    ──< votes
            │    ──< notifications (report_id FK)
         ──< comments
         ──< votes
         ──< notifications (target_user_id FK)
```

---

## Create a new migration (after model changes)

```bash
alembic revision --autogenerate -m "describe your change"
alembic upgrade head
```
# blg-fast
