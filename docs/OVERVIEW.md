# OVERVIEW.md — Project Overview & Conventions

## Project
**Asafo — multi-tenant church management SaaS** (forked from the Living Spring CMS)
Developer: John Evans Okyere | Accra, Ghana | 2026

A web-based church management platform for managing members, attendance, finance, groups, events, and communication.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React.js + Tailwind CSS + ShadCN UI |
| Backend | FastAPI (Python 3.11+) |
| ORM | SQLAlchemy + Alembic (migrations) |
| Database | PostgreSQL (hosted on Supabase) |
| Auth | JWT (python-jose + passlib/bcrypt) |
| File Storage | Cloudinary |
| Email | SendGrid |
| SMS | Arkesel or Moolre REST API |
| Frontend Hosting | Vercel |
| Backend Hosting | Render |

---

## Project Folder Structure

```
church-cms/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app entry point
│   │   ├── core/
│   │   │   ├── config.py            # Settings from .env
│   │   │   ├── security.py          # JWT, password hashing
│   │   │   └── dependencies.py      # Reusable FastAPI dependencies
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── auth.py
│   │   │       ├── members.py
│   │   │       ├── attendance.py
│   │   │       ├── donations.py          # Current finance/giving API module (to expand into broader finance domain)
│   │   │       ├── groups.py
│   │   │       ├── events.py
│   │   │       ├── communication.py
│   │   │       └── reports.py
│   │   ├── models/                  # SQLAlchemy models (one file per module)
│   │   ├── schemas/                 # Pydantic schemas (one file per module)
│   │   ├── crud/                    # DB operations (one file per module)
│   │   ├── services/                # External providers and background workflows
│   │   └── db/
│   │       └── database.py          # DB engine and session
│   ├── alembic/                     # Migrations
│   ├── .env                         # Environment variables (never commit)
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/              # Reusable UI components
│   │   ├── pages/                   # One folder per module
│   │   ├── hooks/                   # Custom React hooks
│   │   ├── services/                # Axios API calls
│   │   ├── store/                   # Zustand global state
│   │   └── utils/                   # Helper functions
│   ├── .env.local                   # Frontend env vars
│   └── package.json
```

---

## Environment Variables

### Backend `.env`
```env
DATABASE_URL=postgresql://postgres:PASSWORD@db.xxxx.supabase.co:5432/postgres
SECRET_KEY=your-very-long-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

CLOUDINARY_CLOUD_NAME=
CLOUDINARY_API_KEY=
CLOUDINARY_API_SECRET=

SENDGRID_API_KEY=
FROM_EMAIL=noreply@example.com

SMS_PROVIDER=arkesel
ARKESEL_API_KEY=
ARKESEL_SENDER_ID=CHURCH
ARKESEL_BASE_URL=https://sms.arkesel.com
MOOLRE_VAS_KEY=
MOOLRE_SENDER_ID=CHURCH
MOOLRE_BASE_URL=https://api.moolre.com
```

### Frontend `.env.local`
```env
VITE_API_BASE_URL=https://your-backend.onrender.com/api/v1
```

---

## Coding Conventions

### Backend
- All routes use prefix `/api/v1/`
- Route files use `APIRouter`
- Always use dependency injection for DB session and current user
- Return consistent response shapes: `{"status": "success", "data": ...}`
- Use HTTP status codes correctly (200, 201, 400, 401, 403, 404, 422)
- All timestamps stored in UTC

### Frontend
- Use `axios` for all API calls, configured in `src/services/api.js`
- Use Zustand for global state (auth user, sidebar state)
- Use React Query (`@tanstack/react-query`) for server state and caching
- Use ShadCN UI components as the base
- All pages are in `src/pages/<module>/`
- Keep components small and reusable
- Use Tailwind utility classes only — no custom CSS files
