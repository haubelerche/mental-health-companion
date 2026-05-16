"""Golden unit tests for AdvisorSelector.

Pure unit tests — no DB, no network, no async fixtures.
All routing decisions are constructed directly with RoutingDecision
to isolate the selector from FastNeedRouter.
"""

from __future__ import annotations

import pytest

from app.services.advisor_selector import AdvisorSelector
from app.services.schemas.routing import AdvisorSelection, RoutingDecision

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DIRECT = RoutingDecision(
    route_tier="fast",
    should_call_advisors=False,
    reason_codes=[],
)

_ADVISOR = RoutingDecision(
    route_tier="advisor_assisted",
    should_call_advisors=True,
    reason_codes=["complex"],
)

_selector = AdvisorSelector()


def _select(message: str, routing: RoutingDecision = _ADVISOR) -> AdvisorSelection:
    return _selector.select(routing=routing, user_message=message)


# ---------------------------------------------------------------------------
# Test 1 — small_talk_routes_direct
# ---------------------------------------------------------------------------

def test_small_talk_routes_direct() -> None:
    """Greeting-like messages with should_call_advisors=False yield no advisors."""
    for msg in ("hi", "chào", "Hello", "Chào bạn nhé"):
        result = _select(msg, routing=_DIRECT)
        assert result.advisor_ids == [], f"Expected [] for greeting '{msg}', got {result.advisor_ids}"


# ---------------------------------------------------------------------------
# Test 2 — memory_recall_routes_direct
# ---------------------------------------------------------------------------

def test_memory_recall_routes_direct() -> None:
    """Memory recall questions should not load advisors (direct route)."""
    msg = "cậu nhớ tôi là ai không?"
    result = _select(msg, routing=_DIRECT)
    assert result.advisor_ids == [], f"Expected [] for memory recall, got {result.advisor_ids}"


# ---------------------------------------------------------------------------
# Test 3 — long_self_blame_routes_empathy_and_cbt
# ---------------------------------------------------------------------------

def test_long_self_blame_routes_empathy_and_cbt() -> None:
    """Long message with self-blame keywords → cbt_pattern_advisor and empathy_advisor."""
    msg = (
        "Mình cảm thấy mệt mỏi và tuyệt vọng quá. "
        "Lỗi tại mình hết, mình tự trách bản thân mãi. "
        "Không biết phải làm sao nữa, cứ buồn hoài."
    )
    result = _select(msg, routing=_ADVISOR)
    assert "cbt_pattern_advisor" in result.advisor_ids, (
        f"Expected cbt_pattern_advisor in {result.advisor_ids}"
    )
    assert "empathy_advisor" in result.advisor_ids, (
        f"Expected empathy_advisor in {result.advisor_ids}"
    )
    assert len(result.advisor_ids) <= 2, f"Max 2 advisors, got {result.advisor_ids}"


# ---------------------------------------------------------------------------
# Test 4 — planning_deadline_routes_strategy
# ---------------------------------------------------------------------------

def test_planning_deadline_routes_strategy() -> None:
    """Planning/deadline keywords → strategy_resource_advisor."""
    msg = "Mình cần kế hoạch học tập vì deadline đang đến gần quá."
    result = _select(msg, routing=_ADVISOR)
    assert "strategy_resource_advisor" in result.advisor_ids, (
        f"Expected strategy_resource_advisor in {result.advisor_ids}"
    )
    assert len(result.advisor_ids) <= 2


# ---------------------------------------------------------------------------
# Test 5 — nutrition_sleep_stress_routes_nutrition
# ---------------------------------------------------------------------------

def test_nutrition_sleep_stress_routes_nutrition() -> None:
    """Food/nutrition keywords → nutrition_support_advisor."""
    for msg in ("bỏ bữa sáng mấy ngày rồi", "ăn uống không đều"):
        result = _select(msg, routing=_ADVISOR)
        assert "nutrition_support_advisor" in result.advisor_ids, (
            f"Expected nutrition_support_advisor for '{msg}', got {result.advisor_ids}"
        )


# ---------------------------------------------------------------------------
# Test 6 — multi_intent_long_story_max_two_advisors
# ---------------------------------------------------------------------------

def test_multi_intent_long_story_max_two_advisors() -> None:
    """Message with deadline + emotional overload → at most 2 advisors selected."""
    msg = (
        "Mình cảm thấy quá tải và kiệt sức vì deadline dồn dập. "
        "Cần kế hoạch để xử lý mấy hạn nộp này, nhưng cũng mệt lắm, "
        "không biết mình còn chịu đựng được bao lâu nữa. "
        "Ăn uống cũng không ổn, bỏ bữa liên tục."
    )
    result = _select(msg, routing=_ADVISOR)
    assert len(result.advisor_ids) <= 2, (
        f"Expected at most 2 advisors, got {len(result.advisor_ids)}: {result.advisor_ids}"
    )
    assert len(result.advisor_ids) >= 1, "Expected at least 1 advisor for complex message"


# ---------------------------------------------------------------------------
# Test 7 — no_questions_asked_routes_direct
# ---------------------------------------------------------------------------

def test_no_questions_asked_routes_direct() -> None:
    """Supportive/passive mode request with should_call_advisors=False → no advisors."""
    msg = "đừng hỏi nhiều, chỉ ở đây nghe tôi thôi"
    result = _select(msg, routing=_DIRECT)
    assert result.advisor_ids == [], f"Expected [] for passive-mode message, got {result.advisor_ids}"
