# API.md — API Design Conventions

## Base URL
- Development: `http://localhost:8000/api/v1`
- Production: `https://your-backend.onrender.com/api/v1`

---

## Response Format

All endpoints return consistent JSON shapes.

### Success (single object)
```json
{
  "status": "success",
  "data": { ... }
}
```

### Success (list)
```json
{
  "status": "success",
  "data": [ ... ],
  "total": 250,
  "page": 1,
  "limit": 20
}
```

### Error
```json
{
  "detail": "Member not found"
}
```
FastAPI handles error format automatically via HTTPException.

---

## Authentication Header
Every protected request must include:
```
Authorization: Bearer <access_token>
```

---

## Pagination
All list endpoints support:
```
GET /members?skip=0&limit=20&search=John&status=active
```

Standard query params:
- `skip` — offset (default 0)
- `limit` — page size (default 20, max 100)
- `search` — optional keyword search
- `status` — optional status filter

---

## HTTP Status Codes

| Code | When to Use |
|---|---|
| 200 | Successful GET, PUT |
| 201 | Successful POST (created) |
| 204 | Successful DELETE (no content) |
| 400 | Bad request / validation error |
| 401 | Not authenticated |
| 403 | Authenticated but not authorized |
| 404 | Resource not found |
| 422 | Pydantic validation failure |
| 500 | Unexpected server error |

---

## All Endpoints Summary

### Auth
```
POST   /auth/login
POST   /auth/register
GET    /auth/me
POST   /auth/change-password
```

### Members
```
GET    /members
POST   /members
GET    /members/{id}
PUT    /members/{id}
DELETE /members/{id}
POST   /members/{id}/photo
GET    /members/family/{family_id}
GET    /members/export
```

### Families
```
GET    /families?search=Asante&limit=100
POST   /families
GET    /families/{id}
```

### Attendance
```
GET    /attendance/sessions
POST   /attendance/sessions
GET    /attendance/sessions/{id}
POST   /attendance/sessions/{id}/mark
GET    /attendance/member/{id}
GET    /attendance/summary
```

Attendance sessions now support `session_start_time`, which is used for punctuality calculations.

### Finance / Giving
```
GET    /donations
POST   /donations
GET    /donations/{id}
GET    /donations/member/{id}
GET    /donations/batches
POST   /donations/batches
POST   /donations/batches/{id}/close
GET    /donations/funds
POST   /donations/funds
POST   /donations/funds/bootstrap
GET    /donations/expense-categories
POST   /donations/expense-categories
POST   /donations/expense-categories/bootstrap
GET    /donations/expenses
POST   /donations/expenses
GET    /donations/reports/monthly
GET    /donations/reports/annual
GET    /donations/member/{id}/statement
```

Current implementation uses `/donations` as the giving API. Product language and future design should treat this as the first part of the broader church `Finance` module.
Funds may enforce member linkage. Example: `tithe` requires a member, while `offering` does not.
The UI calls finance batches **Service Batches**. A batch is opened for one service or event, giving entries are attached to it, and an authorised finance user closes it after reviewing the total. Closed batches reject new giving entries.

### Departments
```
GET    /groups
POST   /groups
PUT    /groups/{id}
DELETE /groups/{id}
GET    /groups/{id}/members
POST   /groups/{id}/members
DELETE /groups/{id}/members/{member_id}
```

### Events
```
GET    /events
POST   /events
PUT    /events/{id}
DELETE /events/{id}
POST   /events/{id}/register
GET    /events/{id}/registrations
POST   /events/{id}/remind
```

### Communication
```
POST   /communication/sms
POST   /communication/email
GET    /communication/history
GET    /communication/reminders
POST   /communication/reminders
PUT    /communication/reminders/{id}
DELETE /communication/reminders/{id}
POST   /communication/reminders/run-due
POST   /communication/announcement
GET    /communication/announcements
PUT    /communication/announcements/{id}
DELETE /communication/announcements/{id}
```

Communication audience values are `all_members`, `active_members`,
`inactive_members`, `department`, and (for targeted workflows)
`selected_members`. `all_members` includes every membership status; recipients
without a phone number are omitted from SMS delivery.

### Pastoral and Audit
```
GET    /pastoral                        # list and filter care records
GET    /pastoral/summary                # open, overdue, due today, completed
GET    /pastoral/attendance-risks       # members needing a care plan
GET    /pastoral/assignees              # eligible care owners
POST   /pastoral                        # create and assign a care plan
PUT    /pastoral/{id}                   # edit, complete, or reopen
GET    /audit
```

Superadmins and secretaries can create, assign, and manage all pastoral care
records. Group leaders can view and update only care assigned to them.

### Reports
```
GET    /reports/dashboard
GET    /reports/attendance/monthly
GET    /reports/donations/monthly
GET    /reports/expenses/monthly
GET    /reports/members/growth
GET    /reports/export/members
GET    /reports/export/donations
```

---

## CORS

Allowed origins (set in main.py):
- `http://localhost:5173` (Vite dev)
- `https://*.vercel.app` (production)

---

## API Docs

FastAPI auto-generates interactive docs at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

Use these to test all endpoints during development.
