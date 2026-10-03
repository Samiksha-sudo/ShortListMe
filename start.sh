#!/usr/bin/env bash
# Runs backend (8000) and frontend (5173) locally without Docker.
set -e
cd "$(dirname "$0")"
[ -f .env ] || cp .env.example .env
(cd backend && .venv/Scripts/python -m uvicorn app.main:app --reload --port 8000) &
(cd frontend && npm run dev) &
wait
