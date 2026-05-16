#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

export PYTHONPATH="${PYTHONPATH:-backend}"
export SERENE_BACKEND_TESTING="${SERENE_BACKEND_TESTING:-1}"
export JWT_DEV_SECRET="${JWT_DEV_SECRET:-serene-ci-jwt-secret-please-change}"

is_fork_pr="${IS_FORK_PR:-false}"
require_real_db="${CI_REQUIRE_REAL_DB:-true}"
ci_db_url="${CI_SUPABASE_DATABASE_URL:-${DATABASE_URL:-}}"

if [[ -z "$ci_db_url" ]]; then
  if [[ "$is_fork_pr" == "true" || "$require_real_db" != "true" ]]; then
    echo "::notice::CI_SUPABASE_DATABASE_URL is not available; running DB-optional backend tests only."
    pytest backend/tests -q -m "not real_db"
    exit 0
  fi

  echo "::error::CI_SUPABASE_DATABASE_URL is required for same-repository backend CI."
  echo "::error::Create a dedicated Supabase CI database and add its transaction-pooler URL as the GitHub Actions secret CI_SUPABASE_DATABASE_URL."
  exit 1
fi

if [[ "$ci_db_url" == sqlite* ]]; then
  echo "::error::CI_SUPABASE_DATABASE_URL must point to PostgreSQL/Supabase, not SQLite."
  exit 1
fi

if [[ "$ci_db_url" == *":5432/"* || "$ci_db_url" == *":5432?"* ]]; then
  echo "::warning::CI_SUPABASE_DATABASE_URL appears to use Supabase session pooler/direct port 5432. Prefer transaction pooler port 6543 to avoid EMAXCONNSESSION."
fi

export DATABASE_URL="$ci_db_url"
export AUTO_CREATE_SCHEMA="${AUTO_CREATE_SCHEMA:-false}"
export BACKGROUND_WORKERS_ENABLED="${BACKGROUND_WORKERS_ENABLED:-false}"
export IDLE_SUMMARIZER_ENABLED="${IDLE_SUMMARIZER_ENABLED:-false}"
export NOTIFICATION_OUTBOX_WORKER_ENABLED="${NOTIFICATION_OUTBOX_WORKER_ENABLED:-false}"
export NEO4J_GRAPH_OUTBOX_WORKER_ENABLED="${NEO4J_GRAPH_OUTBOX_WORKER_ENABLED:-false}"
export VOICE_TTS_WORKER_ENABLED="${VOICE_TTS_WORKER_ENABLED:-false}"
export RANDOM_PROACTIVE_VOICE_ENABLED="${RANDOM_PROACTIVE_VOICE_ENABLED:-false}"

python - <<'PY'
import os
import sys

from sqlalchemy import create_engine, text

url = os.environ["DATABASE_URL"]
engine = create_engine(
    url,
    connect_args={"options": "-c search_path=app,extensions", "connect_timeout": 15},
    pool_pre_ping=True,
)

try:
    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS app"))
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS extensions"))
        conn.execute(text("SET search_path TO app, extensions"))
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA extensions"))
except Exception as exc:
    print(f"::error::Supabase CI database preflight failed: {exc}")
    sys.exit(1)
finally:
    engine.dispose()

print("Supabase CI database preflight OK")
PY

(
  cd backend
  alembic upgrade head
)

python backend/scripts/verify_db_schema.py
pytest backend/tests -q
