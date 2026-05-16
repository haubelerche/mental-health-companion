"""Golden routing fixture tests — PR-03.

Each case maps a specific user turn type to the expected route and advisor selection.
These tests assert deterministic routing outcomes without LLM calls.
"""
from __future__ import annotations

import pytest

from app.services.advisor_selector import AdvisorSelector
from app.services.chat_orchestrator import ChatOrchestrator
from app.services.fast_need_router import FastNeedRouter
from app.services.schemas.routing import RoutingDecision


# ---------------------------------------------------------------------------
# 1. Small talk / greeting → direct route, NO advisors
# ---------------------------------------------------------------------------

def test_small_talk_routes_direct_no_advisors():
    routing = FastNeedRouter().route(
        user_message="hôm nay chán quá",
        recent_user_messages=[],
    )
    assert routing.route_tier in {"fast", "service_only"}
    assert routing.should_call_advisors is False


def test_greeting_routes_direct():
    routing = FastNeedRouter().route(
        user_message="ê chào buổi sáng",
        recent_user_messages=[],
    )
    assert routing.route_tier in {"fast", "service_only"}
    assert routing.should_call_advisors is False


def test_short_ack_routes_fast():
    routing = FastNeedRouter().route(
        user_message="ok thanks",
        recent_user_messages=[],
    )
    assert routing.route_tier == "fast"


# ---------------------------------------------------------------------------
# 2. Memory recall → direct, no heavy advisor
# ---------------------------------------------------------------------------

def test_memory_recall_routes_direct():
    route_tier, advisor_ids = ChatOrchestrator.resolve_route_and_advisors(
        raw_text="cậu nhớ tôi là ai không",
        previous_user_messages=[],
    )
    assert route_tier in {"fast", "service_only"}
    assert "empathy_advisor" not in advisor_ids
    assert "cbt_pattern_advisor" not in advisor_ids


def test_memory_recall_multi_session_stays_direct():
    route_tier, advisor_ids = ChatOrchestrator.resolve_route_and_advisors(
        raw_text="lần trước tôi kể chuyện gì mà bạn còn nhớ không",
        previous_user_messages=["tôi tên Hậu"],
    )
    assert route_tier in {"fast", "service_only"}


# ---------------------------------------------------------------------------
# 3. Long self-blame story → empathy or cbt advisor
# ---------------------------------------------------------------------------

LONG_SELF_BLAME = (
    "Mình thấy mọi lỗi đều do mình gây ra. Deadline dồn, ăn uống thất thường, "
    "mình cứ tự trách bản thân hoài mà không biết làm gì. Lỗi tại mình hết."
)


def test_long_self_blame_routes_to_advisor():
    route_tier, advisor_ids = ChatOrchestrator.resolve_route_and_advisors(
        raw_text=LONG_SELF_BLAME,
        previous_user_messages=[],
    )
    assert route_tier == "advisor_assisted"
    cbt_or_empathy = {"cbt_pattern_advisor", "empathy_advisor", "reflection_advisor"}
    assert any(a in cbt_or_empathy for a in advisor_ids)


def test_long_self_blame_max_two_advisors():
    _, advisor_ids = ChatOrchestrator.resolve_route_and_advisors(
        raw_text=LONG_SELF_BLAME,
        previous_user_messages=[],
    )
    assert len(advisor_ids) <= 2


def test_cbt_advisor_selected_for_explicit_self_blame():
    routing = RoutingDecision(
        route_tier="advisor_assisted",
        reason_codes=["complex"],
        should_call_advisors=True,
    )
    out = AdvisorSelector().select(
        routing=routing,
        user_message="lo tai minh, tu trach ban than, minh vo dung qua",
        recent_user_messages=[],
    )
    assert "cbt_pattern_advisor" in out.advisor_ids


# ---------------------------------------------------------------------------
# 4. Planning / deadline → strategy advisor
# ---------------------------------------------------------------------------

def test_planning_request_routes_to_strategy_advisor():
    routing = RoutingDecision(
        route_tier="advisor_assisted",
        reason_codes=["explicit_analysis_request"],
        should_call_advisors=True,
    )
    out = AdvisorSelector().select(
        routing=routing,
        user_message="minh can ke hoach cu the cho tuan nay de khong tre deadline",
        recent_user_messages=[],
    )
    assert "strategy_resource_advisor" in out.advisor_ids


def test_explicit_help_request_routes_advisor_assisted():
    route_tier, advisor_ids = ChatOrchestrator.resolve_route_and_advisors(
        raw_text="bạn phân tích giúp mình một phương án nhỏ cho tuần này được không?",
        previous_user_messages=[],
    )
    assert route_tier == "advisor_assisted"


# ---------------------------------------------------------------------------
# 5. Nutrition/sleep signal → nutrition support advisor only when relevant
# ---------------------------------------------------------------------------

def test_nutrition_signal_routes_to_nutrition_advisor():
    routing = RoutingDecision(
        route_tier="advisor_assisted",
        reason_codes=["service_domain"],
        should_call_advisors=True,
    )
    out = AdvisorSelector().select(
        routing=routing,
        user_message="hom nay bo bua sang va chieu, khong biet an gi",
        recent_user_messages=[],
    )
    assert "nutrition_support_advisor" in out.advisor_ids


def test_pure_stress_without_food_keyword_no_nutrition_advisor():
    routing = RoutingDecision(
        route_tier="advisor_assisted",
        reason_codes=["complex"],
        should_call_advisors=True,
    )
    out = AdvisorSelector().select(
        routing=routing,
        user_message="minh stress qua vi deadline va qua tai",
        recent_user_messages=[],
    )
    assert "nutrition_support_advisor" not in out.advisor_ids


# ---------------------------------------------------------------------------
# 6. Multi-intent → at most 2 advisors, highest priority ones
# ---------------------------------------------------------------------------

MULTI_INTENT = (
    "tôi vừa cãi nhau với gia đình, mai deadline, tối qua chỉ ngủ 4 tiếng, "
    "bo bua ca ngay, giờ không biết làm gì"
)


def test_multi_intent_caps_at_two_advisors():
    _, advisor_ids = ChatOrchestrator.resolve_route_and_advisors(
        raw_text=MULTI_INTENT,
        previous_user_messages=[],
    )
    assert len(advisor_ids) <= 2


def test_multi_intent_selects_most_relevant_advisors():
    routing = RoutingDecision(
        route_tier="advisor_assisted",
        reason_codes=["multi_domain_signal"],
        should_call_advisors=True,
    )
    out = AdvisorSelector().select(
        routing=routing,
        user_message="vua bo bua vua tre deadline vua tu trach minh rat te",
        recent_user_messages=[],
    )
    assert len(out.advisor_ids) <= 2
    assert len(out.advisor_ids) >= 1


# ---------------------------------------------------------------------------
# 7. User says do-not-ask → direct route, question count enforced downstream
# ---------------------------------------------------------------------------

def test_listen_only_request_routes_fast():
    routing = FastNeedRouter().route(
        user_message="đừng hỏi nhiều, chỉ ở đây nghe tôi thôi",
        recent_user_messages=[],
    )
    assert routing.route_tier in {"fast", "service_only"}


def test_resolve_route_listen_only():
    route_tier, advisor_ids = ChatOrchestrator.resolve_route_and_advisors(
        raw_text="khong can phan tich gi, chi lang nghe thoi nhe",
        previous_user_messages=[],
    )
    assert route_tier in {"fast", "service_only"}
    assert advisor_ids == []


# ---------------------------------------------------------------------------
# 8. Safety boundary message → safety_policy_layer advisor first
# ---------------------------------------------------------------------------

def test_diagnostic_question_routes_safety_policy_advisor():
    routing = RoutingDecision(
        route_tier="advisor_assisted",
        reason_codes=["clinical_boundary"],
        should_call_advisors=True,
    )
    out = AdvisorSelector().select(
        routing=routing,
        user_message="co phai minh bi tram cam hay roi loan lo au khong",
        recent_user_messages=[],
    )
    assert out.advisor_ids[0] == "safety_policy_layer"


# ---------------------------------------------------------------------------
# 9. Max hop count: visited-set prevents repeated same advisor
# ---------------------------------------------------------------------------

def test_advisor_ids_are_unique_no_duplicates():
    routing = RoutingDecision(
        route_tier="advisor_assisted",
        reason_codes=["complex"],
        should_call_advisors=True,
    )
    out = AdvisorSelector().select(
        routing=routing,
        user_message="minh tu trach va cam thay lo au lien tuc",
        recent_user_messages=[],
    )
    assert len(out.advisor_ids) == len(set(out.advisor_ids)), "Duplicate advisors selected"
