#!/usr/bin/env bash
# Bootstraps a local backend dev environment.
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv .venv
fi

source .venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt

if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "Created backend/.env from .env.example — fill in real values before connecting to Supabase."
fi

echo "Starting FastAPI on http://localhost:8000 ..."
uvicorn app.main:app --reload --port 8000
