# Supabase CI Setup

## Context

Backend CI requires a real PostgreSQL/Supabase database for integration paths that cannot be represented by SQLite. The workflow intentionally uses a dedicated CI secret instead of the production `DATABASE_URL` to prevent accidental migrations or destructive test activity against production data.

## Required GitHub Secret

Create this repository secret under `Settings -> Secrets and variables -> Actions`:

| Secret | Required | Purpose |
|---|---:|---|
| `CI_SUPABASE_DATABASE_URL` | Yes for same-repo PRs | Dedicated Supabase/PostgreSQL URL used by backend CI migrations and tests |

Use a dedicated CI database, Supabase branch, or separate Supabase project. Do not point this secret at production.

## Recommended URL

Prefer the Supabase transaction pooler URL on port `6543`:

```text
postgresql://postgres.<project-ref>:<password>@aws-0-<region>.pooler.supabase.com:6543/postgres
```

Avoid the session pooler/direct port `5432` for CI. This project caps session-pooler connections at runtime, but CI can still hit Supabase `EMAXCONNSESSION` under parallel test load.

## CI Behavior

The PR workflow runs `scripts/ci_backend_tests.sh`.

For same-repository PRs:

1. Fails fast if `CI_SUPABASE_DATABASE_URL` is missing.
2. Creates required schemas and `pgcrypto` extension if absent.
3. Runs `alembic upgrade head` from `backend/`.
4. Runs `python backend/scripts/verify_db_schema.py`.
5. Runs `pytest backend/tests -q`.

For fork PRs:

1. GitHub does not expose repository secrets.
2. CI runs the DB-optional backend test path with `pytest backend/tests -q -m "not real_db"`.

## Local Verification

```bash
export CI_SUPABASE_DATABASE_URL="postgresql://..."
bash scripts/ci_backend_tests.sh
```

On PowerShell:

```powershell
$env:CI_SUPABASE_DATABASE_URL = "postgresql://..."
bash scripts/ci_backend_tests.sh
```
