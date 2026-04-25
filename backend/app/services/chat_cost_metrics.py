from __future__ import annotations

from dataclasses import dataclass
from threading import Lock


@dataclass
class CostSnapshot:
    total_turns: int
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    estimated_cost_usd: float


_lock = Lock()
_total_turns = 0
_total_input_tokens = 0
_total_output_tokens = 0

# Conservative blended estimate for GPT-4o-mini class traffic.
_USD_PER_1K_INPUT = 0.00015
_USD_PER_1K_OUTPUT = 0.00060


def observe_chat_usage(*, input_tokens: int, output_tokens: int) -> None:
    global _total_turns, _total_input_tokens, _total_output_tokens
    with _lock:
        _total_turns += 1
        _total_input_tokens += max(0, int(input_tokens))
        _total_output_tokens += max(0, int(output_tokens))


def get_chat_cost_snapshot() -> CostSnapshot:
    with _lock:
        total_tokens = _total_input_tokens + _total_output_tokens
        est_cost = (_total_input_tokens / 1000.0) * _USD_PER_1K_INPUT + (_total_output_tokens / 1000.0) * _USD_PER_1K_OUTPUT
        return CostSnapshot(
            total_turns=_total_turns,
            total_input_tokens=_total_input_tokens,
            total_output_tokens=_total_output_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=round(est_cost, 6),
        )
