# STAGING.md — a copy of production for testing releases

Never test migrations or billing changes on production first. Staging is the same code with its
own database, its own Vercel projects and **test** keys.

## One-time setup

1. **Database:** in Neon, create a branch of the production project named `staging` (Neon branches
   copy-on-write; reset it from `main` whenever you want fresh data). Copy its connection string.
2. **API service:** on Render create a second Blueprint instance (or a manual web service named `ekklesia-api-staging` with the same build/start commands as `render.yaml`) pointing at the `staging` branch, then set:
   `DATABASE_URL` (staging branch), `ENVIRONMENT=staging`, a **different** `SECRET_KEY`,
   `CORS_ORIGINS`/`FRONTEND_BASE_URL` (staging frontend URL), `BILLING_PROVIDER=fake` (or `seevplus`
   with a *sandbox* `SEEVPLUS_API_KEY`; the key decides sandbox vs live), `SMS_PROVIDER=console`,
   `EMAIL_BACKEND=console` (or SendGrid with a test sender), `CRON_SECRET`, `RATE_LIMIT_BACKEND=database`.
   `fake` billing is allowed outside `ENVIRONMENT=production`.
3. **Frontend project:** `cd frontend && vercel link --project ekklesia-church-staging`, set
   `VITE_API_BASE_URL=https://<staging render url>/api/v1`.
4. Create a platform admin on the staging DB:
   `PLATFORM_ADMIN_EMAIL=... PLATFORM_ADMIN_PASSWORD=... DATABASE_URL=<staging> python scripts/bootstrap_platform_admin.py`.
   Optional demo data: `python scripts/seed_demo.py` (synthetic churches) against the staging URL.

## Every release

```bash
cd backend && DATABASE_URL='<staging url>' alembic upgrade head   # rehearse the migration
git push origin HEAD:staging                 # Render deploys the staging API (pre-deploy runs the migration)
cd frontend && vercel deploy --yes
# smoke test: sign up a church, invite someone, buy a plan, close the account, reopen it
curl https://<staging api>/health/db
# only then repeat against production (docs/DEPLOYMENT.md "Release procedure")
```

Use a different directory link per environment (`vercel link`), or deploy with `--scope`/`--project`
flags, so a staging deploy can never go to the production project by accident.
