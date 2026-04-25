from app.services.chat_context import _apply_recent_message_token_guard


def _mk_turn(idx: int, content: str) -> dict:
    role = "user" if idx % 2 else "assistant"
    return {"role": role, "content": content, "sos_triggered": False, "created_at": f"2026-01-01T00:00:0{idx}Z"}


def test_token_guard_keeps_all_when_under_budget():
    turns = [_mk_turn(1, "xin chao"), _mk_turn(2, "mình vẫn nhớ cuộc trò chuyện này")]
    out = _apply_recent_message_token_guard(turns, token_budget=999)
    assert out == turns


def test_token_guard_prefers_newest_turns_when_over_budget():
    turns = [
        _mk_turn(1, "turn 1 " * 40),
        _mk_turn(2, "turn 2 " * 40),
        _mk_turn(3, "turn 3 " * 40),
        _mk_turn(4, "turn 4 " * 40),
        _mk_turn(5, "turn 5 " * 40),
        _mk_turn(6, "turn 6 " * 40),
    ]
    out = _apply_recent_message_token_guard(turns, token_budget=200, min_messages=4)
    # Must keep continuity tail.
    assert len(out) >= 4
    assert out[-1]["content"].startswith("turn 6")
    assert out[-2]["content"].startswith("turn 5")
    # Oldest turns are dropped first.
    assert not any(t["content"].startswith("turn 1") for t in out)


def test_token_guard_keeps_min_messages_even_if_budget_tight():
    turns = [_mk_turn(i, f"turn {i} " * 60) for i in range(1, 7)]
    out = _apply_recent_message_token_guard(turns, token_budget=20, min_messages=4)
    assert len(out) == 4
    assert out[0]["content"].startswith("turn 3")
    assert out[-1]["content"].startswith("turn 6")
