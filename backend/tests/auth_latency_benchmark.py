from __future__ import annotations

import argparse
import statistics
import sys
import time
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

_THIS = Path(__file__).resolve().parent   
_BACKEND_ROOT = _THIS.parent
_REPO_ROOT = _BACKEND_ROOT.parent
for _p in (_BACKEND_ROOT, _REPO_ROOT):
    _s = str(_p)
    if _s not in sys.path:
        sys.path.insert(0, _s)

from app.api.v1.routers import auth as auth_router
from app.services.db.session import Base
from app.main import app

LOGIN_P95_TARGET_MS = 1200
SIGNUP_P95_TARGET_MS = 1500


def _p95(samples: list[float]) -> float:
    if not samples:
        return 0.0
    # statistics.quantiles with n=100 gives percentiles; index 94 => 95th percentile.
    if len(samples) == 1:
        return samples[0]
    return statistics.quantiles(samples, n=100, method="inclusive")[94]


def _measure_ms(fn) -> float:
    started = time.perf_counter()
    fn()
    return round((time.perf_counter() - started) * 1000, 2)


def _describe(samples: list[float]) -> dict[str, float]:
    if not samples:
        return {"min": 0.0, "avg": 0.0, "p50": 0.0, "p95": 0.0, "max": 0.0}
    ordered = sorted(samples)
    mid = len(ordered) // 2
    p50 = ordered[mid] if len(ordered) % 2 == 1 else round((ordered[mid - 1] + ordered[mid]) / 2, 2)
    return {
        "min": ordered[0],
        "avg": round(sum(ordered) / len(ordered), 2),
        "p50": p50,
        "p95": round(_p95(ordered), 2),
        "max": ordered[-1],
    }


def run_benchmark(iterations: int) -> tuple[list[float], list[float]]:
    signup_latencies: list[float] = []
    login_latencies: list[float] = []

    auth_router.issue_access_token = lambda *_args, **_kwargs: "bench-access-token"
    auth_router.generate_refresh_token = lambda: "bench-refresh-token"
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)
    Base.metadata.create_all(bind=engine)

    def override_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[auth_router.get_db] = override_db

    try:
        with TestClient(app) as client:
            for _ in range(iterations):
                email = f"bench_{uuid4().hex[:12]}@example.com"
                password = "StrongPass#2026"

                def _signup_call() -> None:
                    resp = client.post(
                        "/v1/auth/signup",
                        json={
                            "display_name": "Bench User",
                            "email": email,
                            "password": password,
                            "disclaimer_accepted": True,
                        },
                    )
                    if resp.status_code != 201:
                        raise RuntimeError(f"signup failed: {resp.status_code} {resp.text}")

                def _login_call() -> None:
                    resp = client.post(
                        "/v1/auth/login",
                        json={"email": email, "password": password},
                    )
                    if resp.status_code != 200:
                        raise RuntimeError(f"login failed: {resp.status_code} {resp.text}")

                signup_latencies.append(_measure_ms(_signup_call))
                login_latencies.append(_measure_ms(_login_call))
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()

    return signup_latencies, login_latencies


def main() -> int:
    parser = argparse.ArgumentParser(description="Auth latency benchmark (signup/login) with p95 thresholds.")
    parser.add_argument("--iterations", type=int, default=30, help="Number of signup/login samples.")
    parser.add_argument(
        "--warmup",
        type=int,
        default=3,
        help="Warmup iterations excluded from p95 summary.",
    )
    parser.add_argument(
        "--fail-on-sla",
        action="store_true",
        help="Return non-zero exit code when p95 exceeds configured thresholds.",
    )
    args = parser.parse_args()

    total_iterations = max(1, args.iterations + max(0, args.warmup))
    signup_latencies, login_latencies = run_benchmark(total_iterations)
    warmup = max(0, args.warmup)
    sampled_signup = signup_latencies[warmup:]
    sampled_login = login_latencies[warmup:]
    signup_summary = _describe(sampled_signup)
    login_summary = _describe(sampled_login)

    print(f"warmup={warmup} measured_samples={len(sampled_signup)}")
    print(
        "signup "
        f"min={signup_summary['min']:.2f} avg={signup_summary['avg']:.2f} "
        f"p50={signup_summary['p50']:.2f} p95={signup_summary['p95']:.2f} max={signup_summary['max']:.2f} "
        f"target_p95<={SIGNUP_P95_TARGET_MS}"
    )
    print(
        "login  "
        f"min={login_summary['min']:.2f} avg={login_summary['avg']:.2f} "
        f"p50={login_summary['p50']:.2f} p95={login_summary['p95']:.2f} max={login_summary['max']:.2f} "
        f"target_p95<={LOGIN_P95_TARGET_MS}"
    )

    violated = []
    if signup_summary["p95"] > SIGNUP_P95_TARGET_MS:
        violated.append("signup_p95")
    if login_summary["p95"] > LOGIN_P95_TARGET_MS:
        violated.append("login_p95")

    if violated:
        print(f"SLA_CHECK=FAILED violated={','.join(violated)}")
        if args.fail_on_sla:
            return 1
        return 0

    print("SLA_CHECK=PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
