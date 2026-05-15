"""Test AdvisorSelector's context-aware fallback logic."""
from __future__ import annotations

from app.services.advisor_selector import AdvisorSelector
from app.services.schemas.routing import RoutingDecision


def _routing_advisor() -> RoutingDecision:
    return RoutingDecision(
        route_tier="advisor_assisted",
        reason_codes=["repeated_self_blame"],
        should_call_advisors=True,
    )


def test_short_ack_after_emotional_recent_gets_empathy_advisor():
    """A short ack after 2+ emotional messages should pick empathy_advisor, not reflection_advisor."""
    recent = [
        "Mình căng thẳng quá, cảm thấy kiệt sức rồi",
        "Không biết mình có ổn không",
    ]
    selection = AdvisorSelector().select(
        routing=_routing_advisor(),
        user_message="ừ",
        recent_user_messages=recent,
    )
    assert "empathy_advisor" in selection.advisor_ids, (
        "Short ack after emotional context must select empathy_advisor, "
        f"got: {selection.advisor_ids}"
    )


def test_no_keyword_match_and_no_recent_context_gets_reflection():
    """Without any signal, reflection_advisor is the safe fallback."""
    selection = AdvisorSelector().select(
        routing=_routing_advisor(),
        user_message="không biết",
        recent_user_messages=[],
    )
    assert "reflection_advisor" in selection.advisor_ids


def test_recent_self_blame_adds_cbt_advisor():
    """Two recent self-blame messages should add cbt_pattern_advisor even for short current message."""
    recent = [
        "Mình cứ tự trách mình mãi, lỗi do mình hết",
        "Thấy mình vô dụng quá",
    ]
    selection = AdvisorSelector().select(
        routing=_routing_advisor(),
        user_message="vâng",
        recent_user_messages=recent,
    )
    assert (
        "cbt_pattern_advisor" in selection.advisor_ids
        or "empathy_advisor" in selection.advisor_ids
    ), (
        f"Recent self-blame context must produce a relevant advisor, got: {selection.advisor_ids}"
    )


def test_max_two_advisors_still_enforced_with_context():
    """Context-aware fallback must not exceed MAX_ADVISORS_PER_TURN=2."""
    recent = [
        "Mình vừa cãi nhau với gia đình, deadline gấp, ăn uống thất thường, cảm thấy kiệt sức",
        "Lỗi tại mình hết thôi, mình vô dụng",
    ]
    selection = AdvisorSelector().select(
        routing=_routing_advisor(),
        user_message="ừ mình hiểu",
        recent_user_messages=recent,
    )
    assert len(selection.advisor_ids) <= 2, (
        f"Context-aware path must still cap at 2 advisors, got: {selection.advisor_ids}"
    )
