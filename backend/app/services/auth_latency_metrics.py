from __future__ import annotations

import math
import threading
from collections import deque
from dataclasses import dataclass


@dataclass(frozen=True)
class AuthLatencySnapshot:
    flow: str
    count: int
    success_count: int
    success_rate: float
    p95_ms: float
    avg_ms: float
    target_p95_ms: float
    within_sla: bool
    should_log: bool


class _RollingAuthLatencyTracker:
    def __init__(self, *, flow: str, target_p95_ms: float, window_size: int = 200, log_every: int = 20) -> None:
        self.flow = flow
        self.target_p95_ms = float(target_p95_ms)
        self.window_size = max(20, int(window_size))
        self.log_every = max(1, int(log_every))
        self._lock = threading.Lock()
        self._durations_ms: deque[float] = deque(maxlen=self.window_size)
        self._success_flags: deque[int] = deque(maxlen=self.window_size)

    def observe(self, *, duration_ms: float, success: bool) -> AuthLatencySnapshot:
        dur = max(0.0, float(duration_ms))
        with self._lock:
            self._durations_ms.append(dur)
            self._success_flags.append(1 if success else 0)
            count = len(self._durations_ms)
            success_count = sum(self._success_flags)
            avg_ms = sum(self._durations_ms) / count
            p95_ms = _percentile(self._durations_ms, 0.95)
            success_rate = success_count / count
            within_sla = p95_ms <= self.target_p95_ms
            should_log = (count % self.log_every == 0) or (not within_sla)
            return AuthLatencySnapshot(
                flow=self.flow,
                count=count,
                success_count=success_count,
                success_rate=success_rate,
                p95_ms=p95_ms,
                avg_ms=avg_ms,
                target_p95_ms=self.target_p95_ms,
                within_sla=within_sla,
                should_log=should_log,
            )

    def snapshot(self) -> AuthLatencySnapshot:
        with self._lock:
            count = len(self._durations_ms)
            if count == 0:
                return AuthLatencySnapshot(
                    flow=self.flow,
                    count=0,
                    success_count=0,
                    success_rate=0.0,
                    p95_ms=0.0,
                    avg_ms=0.0,
                    target_p95_ms=self.target_p95_ms,
                    within_sla=True,
                    should_log=False,
                )
            success_count = sum(self._success_flags)
            avg_ms = sum(self._durations_ms) / count
            p95_ms = _percentile(self._durations_ms, 0.95)
            return AuthLatencySnapshot(
                flow=self.flow,
                count=count,
                success_count=success_count,
                success_rate=success_count / count,
                p95_ms=p95_ms,
                avg_ms=avg_ms,
                target_p95_ms=self.target_p95_ms,
                within_sla=p95_ms <= self.target_p95_ms,
                should_log=False,
            )

    def reset(self) -> None:
        with self._lock:
            self._durations_ms.clear()
            self._success_flags.clear()


def _percentile(values: deque[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = max(0, min(len(ordered) - 1, math.ceil(len(ordered) * q) - 1))
    return float(ordered[idx])


_LOGIN_TRACKER = _RollingAuthLatencyTracker(flow="login", target_p95_ms=1200.0)
_SIGNUP_TRACKER = _RollingAuthLatencyTracker(flow="signup", target_p95_ms=1500.0)


def observe_auth_latency(*, flow: str, duration_ms: float, success: bool) -> AuthLatencySnapshot:
    if flow == "login":
        return _LOGIN_TRACKER.observe(duration_ms=duration_ms, success=success)
    if flow == "signup":
        return _SIGNUP_TRACKER.observe(duration_ms=duration_ms, success=success)
    raise ValueError(f"Unsupported auth flow '{flow}'")


def get_auth_latency_snapshot(*, flow: str) -> AuthLatencySnapshot:
    if flow == "login":
        return _LOGIN_TRACKER.snapshot()
    if flow == "signup":
        return _SIGNUP_TRACKER.snapshot()
    raise ValueError(f"Unsupported auth flow '{flow}'")


def reset_auth_latency_metrics() -> None:
    _LOGIN_TRACKER.reset()
    _SIGNUP_TRACKER.reset()
