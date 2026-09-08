#!/usr/bin/env bash
# Bootstraps a local frontend dev environment.
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -f ".env.local" ]; then
  echo "NEXT_PUBLIC_API_URL=http://localhost:8000/api" > .env.local
  echo "Created frontend/.env.local — add NEXT_PUBLIC_SUPABASE_* values when ready."
fi

npm install
echo "Starting Next.js on http://localhost:3000 ..."
npm run dev
