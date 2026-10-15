# Deployment handover: Equinox on Google Cloud (`team-shika-equinox`)

**For:** Joely's AI assistant (and Joely). **From:** Hong Yi's session, 2026-10-15. **Goal:** put the Equinox web app on the internet using the Google Cloud console, Firebase and Cloud Run. Deadline for the hackathon is 16 Oct 2026, so take the simplest path in each step.

Read this whole file first. Do the steps in order. Every step ends with a check; do not move on until the check passes.
**Never put a secret in the repo, in a chat message, or in a command line that is logged.** Secrets go into Secret Manager only.

---

## 1. What we are building

```
Browser ──► Firebase Hosting  team-shika-equinox.web.app   (the React app, static files)
               │  /api/**  (rewrite)
               ▼
          Cloud Run service  equinox-api      (FastAPI, scheduler OFF, scales 1 to 5)
          Cloud Run service  equinox-worker   (same image, scheduler ON, exactly 1 instance, CPU always on)
          Cloud Run job      equinox-migrate  (same image, runs `alembic upgrade head`, run by hand)
               │
               ├─► Supabase Postgres (stays where it is; reached over the internet with DATABASE_URL)
               ├─► Supabase Storage  (private buckets: smart-health-originals, food-images)
               ├─► Vertex AI / Gemini (Google API key, already working)
               └─► Workato webhooks (calendar reminders and e-mail; Joely owns the recipes)
```

| Thing | Name / value |
|---|---|
| Web app name (use everywhere) | `team-shika-equinox` |
| Google Cloud project | `smart-health-510414` (Joely's; the Vertex key already works there). If Joely prefers a new project, also create a new Vertex API key and update `GOOGLE_CLOUD_PROJECT`. |
| Region | `asia-southeast1` (Singapore) for everything |
| Firebase Hosting site id | `team-shika-equinox` → `https://team-shika-equinox.web.app` (also `.firebaseapp.com`) |
| Artifact Registry repo | `equinox` (Docker), region `asia-southeast1` |
| Container image | `asia-southeast1-docker.pkg.dev/smart-health-510414/equinox/api:<git sha>` |
| Cloud Run services | `equinox-api`, `equinox-worker` |
| Cloud Run job | `equinox-migrate` |
| Runtime service account | `equinox-run@smart-health-510414.iam.gserviceaccount.com` |
| Build service account | `equinox-build@smart-health-510414.iam.gserviceaccount.com` |

### Defaults I chose (change only if Joely says so)
1. **Hosting:** Firebase Hosting for the frontend, Cloud Run for the backend (not Cloud Run for both).
2. **One environment:** production only, no separate UAT. The git tag/branch to deploy is `main` after the team approves the push.
3. **Domain:** the free `*.web.app` address. A custom domain is optional and is step 11.
4. **Launch mode:** demo launch. The app has **no real login** (see section 12). Do not advertise the URL widely or put real patient data in it.
5. **Gemini credentials:** keep the existing Vertex API key (`GOOGLE_API_KEY`), stored in Secret Manager. The runtime service account is not used for Gemini.
6. **Who runs the console steps:** Joely (owner of the project). The AI prepares the files and gives Joely exact clicks/commands.
7. **Database:** stays on Supabase. Hong Yi's connection to it was down while this was written, so the first migration check (step 6) must be run by someone whose connection reaches it.

---

## 2. Before you start: get the code ready (do not skip)

1. Work from the `dev` branch of the repo, **after** it is rebased on `origin/dev` (it contains Joely's commit `82a027b`, the optional Cloud Vision reader). Hong Yi has 3 local commits not yet pushed (`3d19d4a`, `84f0866`, `709a094`); Hong Yi pushes them when the team says go. Deploy from `main` only after the pull request is merged. Until then, a test deploy from `dev` is fine.
2. Check the head migration is `0040`: `cd services/api && alembic heads` (one line, `0040`).
3. Check that the backend tests pass: `cd services/api && python -m pytest tests/unit -q` (expect about 2880 passed; two tests in `tests/db` need the database and may fail if the connection is down).
4. Check that the frontend builds: `cd apps/web && npm ci && npm run build` (creates `apps/web/dist`; the big chunk warning is normal).
5. Tools Joely needs on the machine: `gcloud` (Google Cloud CLI), `firebase-tools` (`npm i -g firebase-tools`), Docker is **not** needed (Cloud Build builds the image).

---

## 3. Facts about the app that decide how it is deployed

- **Frontend:** React + Vite. `npm run build` makes static files in `apps/web/dist`. It calls the API at `/api/v1` (same origin), so with a Hosting rewrite it needs **no** `VITE_API_URL` and **no** CORS. It is a single page app: every unknown path must serve `index.html`.
- **Backend:** FastAPI. Entry point `app.main:app`, source root `services/api` (the code imports `app.…`, so run uvicorn with `--app-dir services/api` or set the working directory to `services/api`). Health check: `GET /health` returns `{"status":"ok","demo_mode":true}`. All other routes are under `/api/v1`.
- **In-process scheduler (APScheduler).** The same process can run background jobs: reminders tick, e-mails, dish pictures, nightly learning, calendar top-up. It is switched by `SCHEDULER_ENABLED`. If it runs in every API instance, jobs run many times (duplicate e-mails!). So:
  - `equinox-api`: `SCHEDULER_ENABLED=false`, scales freely.
  - `equinox-worker`: `SCHEDULER_ENABLED=true`, **min instances 1, max instances 1**, "CPU always allocated" (no CPU throttling), otherwise the jobs freeze between requests. The worker still serves HTTP (Cloud Run requires a listening port) but nobody calls it except the health check.
- **Database:** every call opens its own connection to Postgres (`psycopg`, no pool). Supabase's pooler handles this; use the **pooled** connection string (port 6543 or the Supabase "session pooler" address) in `DATABASE_URL`, not the direct one, and set Cloud Run `--max-instances 5` on the API with `--concurrency 40` so the database is not flooded.
- **Alembic** reads `DATABASE_URL` from the environment. Migrations are never run automatically on startup. Run them with the Cloud Run job (step 6) before a release that adds one. **Never run a migration without Hong Yi's say-so**; a safety hook in this project blocks it on purpose.
- **Pictures of dishes** are generated by the worker and kept in the private Supabase bucket `food-images`; the API serves them. Cap `AI_CAP_VERTEX_IMAGE` = 60 a day.
- **OCR for medicine labels:** two readers. Google Cloud Vision is Joely's chosen first-choice reader and is switched on by the env var `SCAN_OCR_ENGINE=vision`; the code default is `local` (offline RapidOCR, `requirements-scan.txt`, `SCAN_OCR_ENABLED=true`), which is also the automatic fallback when Vision cannot be used. **Set `SCAN_OCR_ENGINE=vision` on both Cloud Run services only after Joely confirms she wants it live.** Vision refuses API keys and uses application default credentials: on Cloud Run that is the runtime service account `equinox-run`, so enable `vision.googleapis.com` (step 1) and make sure the project is billed. Do not set `GOOGLE_APPLICATION_CREDENTIALS` on Cloud Run. Keep RapidOCR in the image so a scan never fails because Vision was unreachable.
- **Python:** the Dockerfile uses 3.12 (the repo was developed on 3.13; both work).

---

## 4. Step-by-step

### Step 1: Project, billing, APIs
In the Google Cloud console (project `smart-health-510414`):
1. Billing must be on. Create a **budget** at S$15/month with alerts at 50 %, 90 %, 100 % (Billing → Budgets & alerts).
2. Enable these APIs (APIs & Services → Library, or `gcloud services enable …`):
   `run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com secretmanager.googleapis.com firebase.googleapis.com firebasehosting.googleapis.com iam.googleapis.com cloudresourcemanager.googleapis.com monitoring.googleapis.com logging.googleapis.com vision.googleapis.com`
3. Check: `gcloud services list --enabled` shows them.

### Step 2: Service accounts and permissions (IAM)
Create two service accounts (IAM & Admin → Service accounts):
- `equinox-run` (what the running container acts as). Roles: **Secret Manager Secret Accessor**, **Logs Writer**. Nothing else.
- `equinox-build` (what Cloud Build uses). Roles: **Cloud Build Service Account**, **Artifact Registry Writer**, **Cloud Run Admin**, **Service Account User** (on `equinox-run`), **Logs Writer**.

Check: IAM page lists both with only those roles. Do **not** give anybody Owner on a shared account for this.

### Step 3: Artifact Registry
Artifact Registry → Create repository: name `equinox`, format **Docker**, region `asia-southeast1`.
Check: the repo exists and is empty.

### Step 4: Secrets (Secret Manager)
Create each secret below (Secret Manager → Create secret), value pasted by Joely from her private `.env` (Hong Yi shares the values by a private channel, never in git or chat logs). Give `equinox-run` access (Accessor) on each.

| Secret name | Env var in the container | Needed by | Notes |
|---|---|---|---|
| `equinox-database-url` | `DATABASE_URL` | api, worker, migrate | Supabase **pooled** Postgres URL |
| `equinox-supabase-url` | `SUPABASE_URL` | api, worker | `https://<ref>.supabase.co` |
| `equinox-supabase-service-key` | `SUPABASE_SERVICE_KEY` | api, worker | service-role key, server only |
| `equinox-google-api-key` | `GOOGLE_API_KEY` | api, worker | Vertex express-mode API key |
| `equinox-open-router-key` | `OPEN_ROUTER_API_KEY` | api, worker | for the JEV guard (optional if JEV is off) |
| `equinox-workato-webhook-token` | `WORKATO_WEBHOOK_TOKEN` | api, worker | calendar webhook |
| `equinox-workato-email-token` | `WORKATO_EMAIL_WEBHOOK_TOKEN` | api, worker | e-mail webhook |
| `equinox-notify-secret` | `NOTIFY_SECRET` | api, worker | any long random string; generate a new one for production |

Plain (non-secret) env vars, set on the services (not in Secret Manager):

| Env var | Value |
|---|---|
| `APP_NAME` | `Equinox` |
| `APP_BASE_URL` | `https://team-shika-equinox.web.app` |
| `API_PUBLIC_URL` | `https://team-shika-equinox.web.app` (the API is reached through Hosting, same address) |
| `DEMO_MODE` | `true` for the demo launch (see section 12) |
| `CORS_ORIGINS` | `https://team-shika-equinox.web.app,https://team-shika-equinox.firebaseapp.com` |
| `GOOGLE_CLOUD_PROJECT` | `smart-health-510414` |
| `GOOGLE_CLOUD_REGION` | `global` |
| `LLM_VISION_MODEL`, `LLM_CHAT_MODEL` | `gemini-3.8-flash` (already the default) |
| `FOOD_IMAGE_MODEL` | `gemini-2.5-flash-image` (default) |
| `STORAGE_BUCKET` | `smart-health-originals` |
| `FOOD_IMAGE_BUCKET` | `food-images` |
| `SCAN_OCR_ENABLED` | `true` |
| `EMAIL_DAILY_CAP` | keep the repo default unless Hong Yi says otherwise |
| `WORKATO_WEBHOOK_URL`, `WORKATO_CALENDAR_REMOVE_URL`, `WORKATO_EMAIL_WEBHOOK_URL` | the recipe URLs once Joely has built the recipes (they are blank until then; the app works without them, reminders just are not sent) |
| `WORKATO_TOKEN_HEADER`, `WORKATO_EMAIL_WEBHOOK_TOKEN_HEADER` | the header names the recipes expect |
| `SCHEDULER_ENABLED` | `false` on `equinox-api`, `true` on `equinox-worker` |

The exact list and defaults are in `services/api/app/core/config.py` and `services/api/app/core/settings.py`; `.env.example` at the repo root lists every name. If a name there is missing from this table, copy it with a safe default and tell Hong Yi.
**Do not** set `GOOGLE_APPLICATION_CREDENTIALS` (no key file is needed).

Check: `gcloud secrets list` shows the eight secrets; none printed to the screen.

### Step 5: Add the Docker files to the repo (new files)
Create these in the repo (a pull request, not on `main` directly).

**`services/api/Dockerfile`**
```dockerfile
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /srv
# system libs RapidOCR / OpenCV need
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
COPY requirements.txt requirements-scan.txt requirements-db.txt ./
RUN pip install -r requirements.txt -r requirements-scan.txt -r requirements-db.txt
COPY . .
ENV PORT=8080
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
```
Build context is `services/api` (so `app`, `alembic`, `alembic.ini` are at `/srv`). If `pip install` fails on a package, fix the pin in the matching `requirements*.txt` and tell Hong Yi; do not drop `requirements-scan.txt` silently (that disables medicine scanning).

**`services/api/.dockerignore`**
```
.env
.env.*
**/__pycache__
.pytest_cache
tests
scripts
*.md
```

**`cloudbuild.yaml`** (repo root)
```yaml
substitutions:
  _REGION: asia-southeast1
  _REPO: equinox
  _RUN_SA: equinox-run@smart-health-510414.iam.gserviceaccount.com
steps:
  - id: build
    name: gcr.io/cloud-builders/docker
    args: ['build', '-t', '${_REGION}-docker.pkg.dev/$PROJECT_ID/${_REPO}/api:$SHORT_SHA', '-t', '${_REGION}-docker.pkg.dev/$PROJECT_ID/${_REPO}/api:latest', 'services/api']
  - id: push
    name: gcr.io/cloud-builders/docker
    args: ['push', '--all-tags', '${_REGION}-docker.pkg.dev/$PROJECT_ID/${_REPO}/api']
  - id: deploy-api
    name: gcr.io/google.com/cloudsdktool/cloud-sdk
    entrypoint: gcloud
    args:
      - run
      - deploy
      - equinox-api
      - --image=${_REGION}-docker.pkg.dev/$PROJECT_ID/${_REPO}/api:$SHORT_SHA
      - --region=${_REGION}
      - --service-account=${_RUN_SA}
      - --allow-unauthenticated
      - --min-instances=0
      - --max-instances=5
      - --concurrency=40
      - --memory=1Gi
      - --cpu=1
      - --timeout=120
      - --set-env-vars=^@^APP_NAME=Equinox@APP_BASE_URL=https://team-shika-equinox.web.app@API_PUBLIC_URL=https://team-shika-equinox.web.app@DEMO_MODE=true@SCHEDULER_ENABLED=false@SCAN_OCR_ENABLED=true@GOOGLE_CLOUD_PROJECT=$PROJECT_ID@CORS_ORIGINS=https://team-shika-equinox.web.app,https://team-shika-equinox.firebaseapp.com
      - --update-secrets=DATABASE_URL=equinox-database-url:latest,SUPABASE_URL=equinox-supabase-url:latest,SUPABASE_SERVICE_KEY=equinox-supabase-service-key:latest,GOOGLE_API_KEY=equinox-google-api-key:latest,OPEN_ROUTER_API_KEY=equinox-open-router-key:latest,WORKATO_WEBHOOK_TOKEN=equinox-workato-webhook-token:latest,WORKATO_EMAIL_WEBHOOK_TOKEN=equinox-workato-email-token:latest,NOTIFY_SECRET=equinox-notify-secret:latest
  - id: deploy-worker
    name: gcr.io/google.com/cloudsdktool/cloud-sdk
    entrypoint: gcloud
    args:
      - run
      - deploy
      - equinox-worker
      - --image=${_REGION}-docker.pkg.dev/$PROJECT_ID/${_REPO}/api:$SHORT_SHA
      - --region=${_REGION}
      - --service-account=${_RUN_SA}
      - --no-allow-unauthenticated
      - --min-instances=1
      - --max-instances=1
      - --no-cpu-throttling
      - --memory=1Gi
      - --cpu=1
      - --set-env-vars=^@^APP_NAME=Equinox@APP_BASE_URL=https://team-shika-equinox.web.app@API_PUBLIC_URL=https://team-shika-equinox.web.app@DEMO_MODE=true@SCHEDULER_ENABLED=true@SCAN_OCR_ENABLED=true@GOOGLE_CLOUD_PROJECT=$PROJECT_ID
      - --update-secrets=DATABASE_URL=equinox-database-url:latest,SUPABASE_URL=equinox-supabase-url:latest,SUPABASE_SERVICE_KEY=equinox-supabase-service-key:latest,GOOGLE_API_KEY=equinox-google-api-key:latest,OPEN_ROUTER_API_KEY=equinox-open-router-key:latest,WORKATO_WEBHOOK_TOKEN=equinox-workato-webhook-token:latest,WORKATO_EMAIL_WEBHOOK_TOKEN=equinox-workato-email-token:latest,NOTIFY_SECRET=equinox-notify-secret:latest
images:
  - ${_REGION}-docker.pkg.dev/$PROJECT_ID/${_REPO}/api:$SHORT_SHA
options:
  logging: CLOUD_LOGGING_ONLY
serviceAccount: projects/$PROJECT_ID/serviceAccounts/equinox-build@$PROJECT_ID.iam.gserviceaccount.com
```
The `^@^` prefix changes the separator so the comma in `CORS_ORIGINS` is not split. Add the plain `WORKATO_*_URL` and header-name variables to both `--set-env-vars` lists once they exist (use `--update-env-vars` in a follow-up, not by editing secrets).

**`firebase.json`** (repo root)
```json
{
  "hosting": {
    "site": "team-shika-equinox",
    "public": "apps/web/dist",
    "ignore": ["firebase.json", "**/.*", "**/node_modules/**"],
    "rewrites": [
      { "source": "/api/**", "run": { "serviceId": "equinox-api", "region": "asia-southeast1" } },
      { "source": "/health", "run": { "serviceId": "equinox-api", "region": "asia-southeast1" } },
      { "source": "**", "destination": "/index.html" }
    ],
    "headers": [
      { "source": "/assets/**", "headers": [{ "key": "Cache-Control", "value": "public, max-age=31536000, immutable" }] },
      { "source": "/index.html", "headers": [{ "key": "Cache-Control", "value": "no-cache" }] }
    ]
  }
}
```
The rewrite order matters: API first, then the catch-all.

**`.firebaserc`** (repo root)
```json
{ "projects": { "default": "smart-health-510414" } }
```

### Step 6: Migration job (run by hand, never automatically)
1. First build and push once so the image exists (step 7, build part). Then create the job:
```
gcloud run jobs create equinox-migrate --region asia-southeast1 \
  --image asia-southeast1-docker.pkg.dev/smart-health-510414/equinox/api:latest \
  --service-account equinox-run@smart-health-510414.iam.gserviceaccount.com \
  --set-secrets DATABASE_URL=equinox-database-url:latest \
  --command alembic --args "upgrade,head" --max-retries 0 --task-timeout 600
```
(`alembic.ini` is at the image root `/srv`, which is the working directory.)
2. **Do not execute the job** until Hong Yi confirms. The Supabase database is already at revision `0040` (Hong Yi applied 0039 and 0040 by hand), so for the first launch the job should report "nothing to do". To check without changing anything, run a second job or a one-off with `--args "current"`; the answer must be `0040 (head)`.

### Step 7: First build and deploy of the backend
1. Connect the repository: Cloud Build → Triggers → Connect repository (GitHub, the Equinox repo). Joely authorises the Cloud Build GitHub app.
2. Create a trigger: name `equinox-deploy`, event **Push to a branch**, branch `^main$`, config file `cloudbuild.yaml`, service account `equinox-build`, region `asia-southeast1`.
3. For the very first deploy, run it by hand from the repo root:
   `gcloud builds submit --config cloudbuild.yaml --region asia-southeast1 --substitutions SHORT_SHA=manual1 .`
4. Check:
   - `gcloud run services list --region asia-southeast1` shows `equinox-api` and `equinox-worker`.
   - `curl https://<equinox-api url>/health` gives `{"status":"ok","demo_mode":true}`.
   - `equinox-worker` is **not** public (the health check from Cloud Run is internal).
   - Logs (Logging → Logs Explorer, `resource.type="cloud_run_revision"`) show "scheduler started" on the worker and **not** on the API.

### Step 8: Frontend on Firebase Hosting
1. Console → Firebase (firebase.google.com → Add project → choose the existing project `smart-health-510414`). Accept the terms, skip Analytics.
2. Hosting → Get started → Add another site: site id `team-shika-equinox`.
3. On the machine: `firebase login`, then from the repo root:
```
cd apps/web && npm ci && npm run build && cd ../..
firebase deploy --only hosting --project smart-health-510414
```
4. Check:
   - `https://team-shika-equinox.web.app` opens the app (Mr Tan's example record).
   - `https://team-shika-equinox.web.app/health` returns the JSON (proves the rewrite to Cloud Run).
   - Reloading on a deep link such as `/insights/glucose` shows the page, not a 404.

### Step 9: Smoke test (the launch checklist)
Open the live site on a laptop and a phone and check:
- [ ] Home loads with Mr Tan's example data; no red error banners.
- [ ] Insights → Glucose, Food, Medication open and show charts.
- [ ] Log → Meal suggestions shows dishes; pictures appear within a few minutes (the worker makes them).
- [ ] Creating a new user (avatar menu) works, and logging a meal for that user works.
- [ ] A medicine photo scan returns a result (this tests OCR memory; if the API restarts with an out-of-memory error, raise `--memory` to 2Gi).
- [ ] Doctor brief page, its print view, and a shared doctor link (open in a private window) show the same four charts and filters.
- [ ] Browser console has no CORS errors; Network tab shows `/api/v1/...` calls returning 200.
- [ ] Logs: no repeated errors in `equinox-api`; `equinox-worker` shows the scheduler jobs running once per tick.

### Step 10: Monitoring and safety nets
- Monitoring → Uptime checks: HTTPS GET `https://team-shika-equinox.web.app/health` every 5 minutes, alert to Joely's and Hong Yi's e-mails.
- Monitoring → Alerting: Cloud Run `equinox-worker` instance count = 0 for 5 minutes; 5xx rate above 5 % on `equinox-api` for 10 minutes.
- Budget alert is from step 1.
- The Gemini pictures and chat have daily caps in the app (`AI_CAP_*`); do not raise them without asking.

### Step 11: Custom domain (optional)
Firebase Hosting → Add custom domain, follow the DNS records shown, wait for the certificate (HTTPS is automatic). Then add the new origin to `CORS_ORIGINS` and `APP_BASE_URL` and redeploy both services.

---

## 5. Releasing later, and rolling back

- **Release:** merge to `main`. The Cloud Build trigger builds and deploys both Cloud Run services. The frontend is deployed separately by `firebase deploy --only hosting` (or add a final Cloud Build step later).
- **Order when a release has a migration:** (1) Hong Yi approves, (2) run `equinox-migrate`, (3) deploy the new code. Migrations in this repo are additive, so old code keeps working during the gap.
- **Rollback of the backend:** Cloud Run → service → Revisions → pick the previous revision → **Manage traffic → 100 %**. Takes seconds; do it for both services.
- **Rollback of the frontend:** Firebase console → Hosting → Release history → previous release → Rollback.
- **Emergency stop:** Cloud Run → `equinox-worker` → set max instances 0 (stops all e-mails and background AI use at once).

---

## 6. Cost notes
Firebase Hosting free tier covers this. Cloud Run API scales to zero when unused; the worker costs a small fixed amount (1 instance running all the time, about S$10 to 15 a month). Gemini use is capped in the app. Cloud Build free tier covers the builds. Keep an eye on the budget alert.

---

## 7. Known risks (read and do not "fix" without asking Hong Yi)
1. **No real authentication.** The app picks the user from the `X-User` header; anyone can send any value. Fine for a demo with example data. Not fine for real patients. Do not market the URL; do not let people enter real health data. Real login is a later task.
2. **`DEMO_MODE=true`.** Mr Tan's example record is read-only for everyone, and new users are anonymous. Do not turn it off without a plan.
3. **CORS defaults to localhost.** The `CORS_ORIGINS` value above is mandatory in production if the browser calls the API directly; with the Hosting rewrite it is not used, but keep it correct.
4. **Scheduler must run exactly once.** Never set `SCHEDULER_ENABLED=true` on `equinox-api`, never run more than 1 worker instance. Otherwise people get duplicate e-mails and reminders.
5. **DB connections are per request** (no pool). Keep API `max-instances` at 5 and use the pooled Supabase URL.
6. **Big frontend file** (about 1.7 MB before compression). Acceptable for the demo; a code-splitting task is in the backlog.
7. **New screen text is English only.** The language switcher shows other languages for older text only.
8. **Image generation relies on the Vertex API key**, not the service account. If the key is rotated, update the secret and redeploy (or create a new secret version; services read `:latest` at start).
9. **The Supabase database was unreachable from Hong Yi's network** while this was prepared. Verify the pooled `DATABASE_URL` connects from Cloud Run (the `/health` endpoint does not touch the database; open the Home page to prove it).
10. **Untracked folder `docs/demo-video/`** is Hong Yi's local work; do not commit or deploy it.

---

## 8. What to report back
When done, add a session log at `docs/handover/sessions/joely_<date>_<time>.md` (template: `docs/handover/session-log-template.md`) listing: the Cloud Run service URLs, the revision ids deployed, the Hosting release id, the secrets created (names only), the trigger name, the uptime check, and anything in the checklist that failed. Send Hong Yi the live URL `https://team-shika-equinox.web.app`.

## 9. If something is unclear
Ask Hong Yi; do not guess on: secrets values, the database, migrations, turning off `DEMO_MODE`, or adding real login.
