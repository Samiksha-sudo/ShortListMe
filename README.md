# ShortlistMe

AI-tailored CVs: upload a CV and a job description, get the same CV rewritten for the role.

## Run locally
```
cp .env.example .env
./start.sh            # API on :8000, web on :5173
```
or with Docker: `docker compose up --build`

## Tests
```
cd backend && .venv/Scripts/python -m pytest
```

## Layout
- `backend/` FastAPI, SQLAlchemy, Alembic
- `frontend/` Vite, React, TypeScript
- `storage/` uploaded files (git-ignored)

Secrets live in `.env` (git-ignored). Never commit tokens.
