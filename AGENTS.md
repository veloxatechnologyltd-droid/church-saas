# AGENTS.md — Codex Instructions for Living Spring Church Management System

You are an AI coding agent working on the **Living Spring International Church Management System** — a full-stack web application built by **John Evans Okyere**, based in Accra, Ghana.

> **SaaS conversion in progress:** this repo is the multi-tenant fork. Read `SAAS_CHECKLIST.md` and work through it in order.

Before writing any code, read ALL instruction files in the `docs/` folder in this order:

1. `docs/OVERVIEW.md` — Project structure, stack, and conventions
2. `docs/DATABASE.md` — Database schema and models
3. `docs/AUTH.md` — Authentication and role-based access
4. `docs/BACKEND.md` — FastAPI backend conventions and patterns
5. `docs/FRONTEND.md` — React + Tailwind frontend conventions
6. `docs/MODULES.md` — All feature modules and their requirements
7. `docs/API.md` — API design conventions and endpoint patterns
8. `docs/DESIGN.md` — **UI/UX design system, colors, components, and page specs (read before touching any frontend file)**
9. `docs/SAAS.md` — **Multi-tenant architecture: tenancy, memberships, branches, roles, local dev setup. Where it conflicts with the docs above, SAAS.md and `SAAS_CHECKLIST.md` win.**

---

## General Rules

- Always follow the conventions defined in the docs above
- Never install packages not listed in `requirements.txt` or `package.json` without confirming
- Always write clean, well-commented code
- Never hardcode secrets — use `.env` variables
- Always validate inputs using Pydantic (backend) and proper form handling (frontend)
- Write modular code — one file per module/feature
- After completing a task, briefly summarize what was done and what to do next

## Project Root Structure

```
church-cms/
├── AGENTS.md                  ← You are here
├── docs/                      ← Read all files here first
│   ├── OVERVIEW.md
│   ├── DATABASE.md
│   ├── AUTH.md
│   ├── BACKEND.md
│   ├── FRONTEND.md
│   ├── MODULES.md
│   └── API.md
├── backend/                   ← FastAPI app
└── frontend/                  ← React app
```
