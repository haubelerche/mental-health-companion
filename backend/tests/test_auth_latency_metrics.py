from __future__ import annotations

from app.services.auth_latency_metrics import observe_auth_latency, reset_auth_latency_metrics


def test_auth_latency_tracker_computes_p95_and_sla_window():
    reset_auth_latency_metrics()
    samples = [600.0, 700.0, 750.0, 900.0, 1100.0, 1300.0, 1400.0, 1500.0, 1700.0, 1800.0]
    snapshot = None
    for value in samples:
        snapshot = observe_auth_latency(flow="login", duration_ms=value, success=True)

    assert snapshot is not None
    assert snapshot.flow == "login"
    assert snapshot.count >= 10
    assert snapshot.p95_ms >= 1700.0
    assert snapshot.target_p95_ms == 1200.0
    assert snapshot.within_sla is False
    assert snapshot.should_log is True
