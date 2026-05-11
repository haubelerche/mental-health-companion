# Python Environment Rebuild Report

## Context

Project root: `C:\Users\Admin\Desktop\A20-App-039`

Target environment: `serene-py314`

Target Python: `3.14`

Conda executable: `C:\Users\Admin\anaconda3\Scripts\conda.exe`

## Files Changed

| File | Change |
|---|---|
| `requirements.txt` | Rebuilt as the canonical backend Python dependency manifest. |
| `backend/requirements.txt` | Converted to `-r ../requirements.txt` to avoid divergent backend dependency manifests. |
| `environment.yml` | Added Conda environment definition for `serene-py314`. |
| `.vscode/settings.json` | Pointed VS Code at the new Conda interpreter and enabled pytest discovery for `backend/tests`. |

## Import Scan Scope

| Scope | Result |
|---|---|
| `backend/app/**/*.py` | Scanned direct imports. |
| `backend/tests/**/*.py` | Scanned direct imports, including ignored local test files present in the workspace. |
| `requirements*.txt` | Compared root and backend manifests. |
| `pyproject.toml`, `setup.cfg`, `environment*.yml` | No project-level Python build config existed before this change, except the newly created `environment.yml`. |

## Packages Added

| Package | Reason |
|---|---|
| `asyncpg` | Directly imported by backend core database workers and profile services. |
| `authlib` | Directly imported by OAuth client code. |
| `elevenlabs>=1.0.0` | Directly imported by TTS renderer code. |
| `jsonschema` | Directly imported by profile validation service. |
| `langfuse>=2.0.0` | Directly imported by Langfuse tracing service. |
| `mem0ai` | Provides direct `mem0` import used by memory service. |
| `numpy` | Directly imported by retrieval and embedding logic. |
| `opentelemetry-api==1.41.1` | Pinned to keep observability packages on one release train. |
| `opentelemetry-exporter-otlp-proto-grpc==1.41.1` | Pinned to keep exporter and SDK versions aligned. |
| `opentelemetry-exporter-otlp-proto-http==1.41.1` | Pinned to satisfy Langfuse/exporter alignment without drift. |
| `opentelemetry-proto==1.41.1` | Pinned to the same OpenTelemetry release train. |
| `opentelemetry-sdk==1.41.1` | Pinned to match exporter requirements. |
| `opentelemetry-semantic-conventions==0.62b1` | Pinned to the matching instrumentation/semantic-conventions train. |
| `prometheus-client` | Directly imported by async outbox worker metrics. |
| `rank-bm25` | Directly imported by counseling retriever. |
| `supabase` | Preserved because `backend/tests/test_db.py` imports `src.database`, which imports `supabase`. |

## Packages Removed

| Package | Reason |
|---|---|
| `anthropic` | No direct import found in `backend/app` or `backend/tests`. |
| `langchain-core>=0.3.0` | No direct import found; it is now pulled transitively by `langgraph` when required. |
| `langchain-openai>=0.2.0` | No direct import found in inspected backend scope. |
| `pypdf` | No direct import found in inspected backend scope. |

## Packages Preserved Without Direct Import

| Package | Rationale |
|---|---|
| `alembic` | Migration CLI/runtime dependency for `backend/alembic`. |
| `email-validator` | Runtime support for Pydantic `EmailStr`. |
| `psycopg[binary]` | SQLAlchemy PostgreSQL driver and direct import through `src.database.test_connection`. |
| `PyJWT[crypto]` | Auth/security dependency alongside `python-jose`. |
| `uvicorn[standard]` | ASGI server dependency for FastAPI deployment. |

## Compatibility Risks

| Risk | Assessment | Recommendation |
|---|---|---|
| Python 3.14 ecosystem maturity | `--only-binary=:all:` dry-run succeeded for the current graph, including compiled packages such as `pydantic-core`, `sqlalchemy`, `numpy`, `asyncpg`, `grpcio`, `psycopg-binary`, and `cryptography`. | Continue with `serene-py314` for development; use `serene-py312` as fallback if a future dependency introduces a missing CPython 3.14 wheel. |
| Supabase resolver downgrade | Pip selected `supabase==2.25.1`, not latest `2.30.0`, due to transitive dependency resolution. | Pin `supabase==2.25.1` explicitly if deterministic installs become mandatory, or retest newer Supabase SDK versions when project code requires newer APIs. |
| Pip cache warnings | Pip emitted `Cache entry deserialization failed, entry ignored`; installation still succeeded. | Operationally low risk; clearing pip cache is optional and not required for this environment. |

No package lacked a Python 3.14 wheel under `--only-binary=:all:`.

## Commands Run

```powershell
cd "C:\Users\Admin\Desktop\A20-App-039"

& "C:\Users\Admin\anaconda3\Scripts\conda.exe" create -n serene-py314 python=3.14 pip setuptools wheel -c conda-forge -y

& "C:\Users\Admin\anaconda3\Scripts\conda.exe" run -n serene-py314 python -m pip install --upgrade pip setuptools wheel

& "C:\Users\Admin\anaconda3\Scripts\conda.exe" run -n serene-py314 python -m pip install --dry-run --only-binary=:all: -r requirements.txt

& "C:\Users\Admin\anaconda3\Scripts\conda.exe" run -n serene-py314 python -m pip install --only-binary=:all: -r requirements.txt

& "C:\Users\Admin\anaconda3\Scripts\conda.exe" run -n serene-py314 python -m pip check

& "C:\Users\Admin\anaconda3\Scripts\conda.exe" run -n serene-py314 python -m pipdeptree --warn fail

& "C:\Users\Admin\anaconda3\Scripts\conda.exe" run -n serene-py314 python -m pip install --only-binary=:all: pipdeptree

& "C:\Users\Admin\anaconda3\Scripts\conda.exe" run -n serene-py314 python -m pipdeptree --warn fail

& "C:\Users\Admin\anaconda3\Scripts\conda.exe" run -n serene-py314 python -c "import sys; import fastapi; import pydantic; import pydantic_core; import sqlalchemy; import alembic; import redis; import neo4j; import pytest; print(sys.executable); print('fastapi', fastapi.__version__); print('pydantic', pydantic.__version__); print('pydantic_core', pydantic_core.__version__); print('sqlalchemy', sqlalchemy.__version__); print('ok')"

& "C:\Users\Admin\anaconda3\Scripts\conda.exe" run -n serene-py314 python -m pip check
```

The first `pipdeptree --warn fail` attempt failed because `pipdeptree` was not installed in the new environment. It was installed as environment verification tooling and intentionally left out of backend `requirements.txt`.

## Verification Output

### `python -m pip check`

```text
No broken requirements found.
```

### `python -m pipdeptree --warn fail`

```text
Exit code: 0
No dependency conflict warnings were reported.
```

### Targeted Imports

```text
C:\Users\Admin\anaconda3\envs\serene-py314\python.exe
fastapi 0.136.1
pydantic 2.13.4
pydantic_core 2.46.4
sqlalchemy 2.0.49
ok
```
