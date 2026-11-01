# ShortlistMe

AI-assisted CV tailoring: upload a CV, paste a job description, and get a version of the CV rewritten for that role.

> **Status: in development.** ShortlistMe runs locally and has not been publicly launched or deployed.

## Features

- Account sign-up and login
- Upload and manage CVs
- Add job descriptions and match a CV against them
- AI-generated tailoring and rewrite suggestions
- Stripe-based billing endpoints

## Tech stack

| Layer | Technology |
| --- | --- |
| Backend | Django 5.2, Django REST Framework, Django migrations (gunicorn in production) |
| Frontend | Vite, React, TypeScript |
| AI | Gemini or OpenAI, configured by environment variable |
| Payments | Stripe |
| Email | SMTP |
| Tooling | Docker Compose |

## Project structure

```
backend/
  manage.py
  config/       Django settings, urls, wsgi
  app/
    api/        auth, billing, cvs, jds, matches, rewrites, tailoring, health
    services/
    models/
    migrations/ Django migrations
frontend/
  src/          pages and UI components
docker-compose.yml
.env.example
```

## Getting started

1. Copy `.env.example` to `.env` and fill in your own LLM, SMTP and Stripe values. Never commit `.env`.
2. Start the stack:

   ```bash
   docker compose up --build
   ```

3. API: http://localhost:8000 · Web app: http://localhost:5173

Database migrations run automatically when the backend container starts (`python manage.py migrate`). To run the backend without Docker:

```bash
cd backend
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 8000
```

## Migration note

The backend was migrated from FastAPI, SQLAlchemy and Alembic to Django and Django REST Framework. The REST API paths are unchanged, the Alembic history was replaced by `app/migrations/0001_initial.py`, and the Dockerfile now serves `config.wsgi` with gunicorn.

## Tests

The backend has a test suite (152 tests). Run it from `backend/` with `pytest` (uses `pytest-django`, configured in `pytest.ini`).

## High-level design (HLD)

```mermaid
flowchart LR
    U[User browser] --> W[Web app<br/>Vite + React + TS]
    W -->|REST /JSON| A[API<br/>Django + DRF]
    A --> DB[(SQL database<br/>Django ORM + migrations)]
    A --> FS[(File storage<br/>uploaded CVs)]
    A -->|prompts| L[LLM provider<br/>Gemini or OpenAI]
    A -->|checkout, portal| S[Stripe]
    S -->|signed webhook| A
    A --> M[SMTP mailer<br/>password reset]
```

Main flow:

1. The user signs up and uploads a `.docx` CV. The API validates and parses it into structured blocks.
2. The user adds a job description.
3. The user starts a tailoring job. The API returns `202` straight away and runs the pipeline in the background.
4. The web app polls the job until it is `done`, then shows the match score, the proposed edits and any edits that were dropped.
5. The user exports the edited CV as `.docx` or `.pdf`.

Design decisions:

- **Asynchronous tailoring.** LLM calls are slow, so `POST /tailoring` queues a job and the client polls `GET /tailoring/{id}`.
- **Edits are checked.** Proposed rewrites pass through a validator before they reach the user. Edits that fail are returned separately as `dropped`.
- **Usage limits and billing** are enforced server-side, with Stripe as the source of subscription state through webhooks.

## Low-level design (LLD)

### API surface

All routes are under `/v1`, except `GET /health`. Routers are listed with their path below the prefix.

| Router | Endpoints |
| --- | --- |
| `auth` | `POST /signup`, `/login`, `/refresh`, `/logout`, `/forgot-password`, `/reset-password`, `DELETE /account` |
| `cvs` | `POST /` (upload), `GET /{id}`, `POST /{id}/export.docx`, `POST /{id}/export.pdf` |
| `jds` | `POST /`, `GET /{id}`, `POST /{id}/analysis` |
| `matches` | `POST /` |
| `rewrites` | `POST /` |
| `tailoring` | `POST /` (returns 202), `GET /{job_id}` |
| `billing` | `GET /` (usage), `POST /checkout`, `POST /portal`, `POST /webhook` |
| `health` | `GET /health` |

### Data model

| Table / model | Notable columns |
| --- | --- |
| `User` | `id` (UUID), `email` (unique), `password_hash`, `stripe_customer_id`, `subscription_status`, `created_at` |
| `CV` | owner, stored file key, `parsed` (structured JSON) |
| `JobDescription` / `JDAnalysis` | job description text and its structured analysis |
| `TailoringJob` | `user_id`, `cv_id`, `jd_id`, `status`, `step`, `error`, `result` (JSON), timestamps |
| `RefreshToken`, `PasswordResetToken` | token records, stored hashed |

### Tailoring job state machine

```
status: queued -> running -> done | failed
step:   queued -> analysing -> matching -> rewriting -> done
```

`services/tailoring.run` is the single entry point. It records progress on the job row after each step and never raises: an `LLMError` or any other failure is saved on the job as `failed` with a user-safe message.

### Service layer (`backend/app/services`)

| Module | Responsibility |
| --- | --- |
| `parsing/docx_parser`, `parsing/locator` | Turn a `.docx` into structured blocks and locate text within them |
| `docx_validation` | Reject invalid uploads (`InvalidCV`) |
| `jd_analysis` | Extract structured requirements from a job description |
| `matching` | Compare CV against the requirements and mark each item covered, weak or a gap; compute the score |
| `rewriting` | Ask the LLM for proposed edits (`propose`) |
| `validator` | Check each edit against the original CV (numbers, names, seniority and other tokens) so rewrites cannot add facts |
| `exporting` | Apply accepted edits to the original `.docx`; render a PDF |
| `llm` | Provider call with `generate`, `generate_json` and `generate_model` (schema-validated output) |
| `security` | Password hashing, access and refresh tokens |
| `login_limiter`, `rate_limiter` | Failed-login blocking and request rate limiting |
| `billing` | Usage counting, Stripe checkout and portal URLs, webhook signature check, applying events |
| `background` | Run a task after the response (daemon thread, or inline in tests) |
| `mailer`, `storage` | SMTP sending; reading and writing stored files |

### Django files (`backend/`)

| File | Purpose |
| --- | --- |
| `manage.py` | Django entry point: `migrate`, `runserver`, `createsuperuser` and so on |
| `config/settings.py` | Django and DRF settings. Reads values from `app/core/config.py` (the `.env` file): secret key from `jwt_secret`, CORS origins, and the SQLite database from `DATABASE_URL` (the `sqlite:///` form is kept so existing `.env` files still work). Only `contenttypes`, `rest_framework`, `corsheaders` and `app` are installed: no sessions, admin or Django auth. DRF auth and permission classes are empty because auth is our own JWT check; `APPEND_SLASH` is off so routes match exactly |
| `config/urls.py` | The route table. Every endpoint is a plain `path()` under `/v1/...` (plus `/health`) pointing at a function in `app/api/` |
| `config/wsgi.py` | WSGI entry point that gunicorn serves (`config.wsgi:application`) |
| `app/apps.py` | Registers the `app` package as the Django app (label `app`) |
| `app/models/` | Django ORM models (`User`, `CV`, `JobDescription`, `JDAnalysis`, `TailoringJob`, `RefreshToken`, `PasswordResetToken`). `User`, `CV`, `JobDescription` and `TailoringJob` use UUID string keys; the token tables and `JDAnalysis` are keyed by a hash |
| `app/migrations/0001_initial.py` | Single initial migration. It replaces the old Alembic history. The Dockerfile runs `migrate --fake-initial` at start-up, so a database created by Alembic is adopted rather than rebuilt |
| `app/api/deps.py` | The `@endpoint(methods, auth=...)` decorator that wraps DRF's `api_view`. `auth` is `None` (public), `"user"`, `"llm"` or `"upload"`; the last two add a per-user rate limit. Also holds `current_user_id` (Bearer JWT check) and `owned` (returns a row only if it belongs to the caller, so a missing and someone else's row both answer 404) |
| `app/api/errors.py` | `ApiError(status, detail)` and the DRF exception handler. Errors come back as `{"detail": ...}`, which is the shape the frontend reads; pydantic validation errors become `422`. `parse(Model, data)` validates a request body against a pydantic schema |
| `app/services/background.py` | `run(fn, *args)` runs work after the response is sent, on a daemon thread, and logs any exception. When `BACKGROUND_SYNC` is set (tests) it runs inline. Tailoring jobs use it, so `POST /v1/tailoring` can return `202` straight away |
| `pytest.ini` | Points pytest-django at `config.settings` |
| `tests/client.py` | httpx-style wrapper over Django's test client, so tests read as plain HTTP calls |

Request flow: gunicorn -> `config.wsgi` -> `config/urls.py` -> an `@endpoint` view in `app/api/` -> `app/services/` -> Django ORM. Pydantic is still used for request and response schemas (`app/schemas`) and for validating LLM output.

### Frontend

- Pages: `Landing`, `SignUp`, `Login`, `ForgotPassword`, `ResetPassword`, `Dashboard`, `UploadCV`, `AddJD`, `Tailor`.
- `api.ts` wraps the REST calls; `session.ts` holds the signed-in session.

## Status and roadmap

In development. Public deployment and launch are not done yet.
