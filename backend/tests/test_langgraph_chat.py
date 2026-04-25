from app.services.langgraph_chat import (
    _build_friend_context,
    _enforce_reply_quality,
    _should_skip_cold_start_profile,
    _rule_based_reply,
    _sanitize_assistant_reply,
    get_chat_graph,
)


def test_supervisor_skips_analyst_on_light_greeting():
    graph = get_chat_graph()
    out = graph.invoke(
        {
            "user_message": "chao may",
            "recent_messages": [],
            "mood_today": None,
            "distress_score": 0.1,
            "crisis_route_finalized": False,
            "analyst_calls_this_turn": 0,
            "routing_history": [],
        }
    )
    assert out["routing_history"][0] == "supervisor"
    assert "analyst" not in out["routing_history"]
    assert "friend" in out["routing_history"]
    assert out["reply"]


def test_supervisor_routes_analyst_when_distress_high():
    graph = get_chat_graph()
    out = graph.invoke(
        {
            "user_message": "Minh dang rat ap luc va khong on",
            "recent_messages": [],
            "mood_today": {"mood": "stressed", "emoji": ":("},
            "distress_score": 0.7,
            "crisis_route_finalized": False,
            "analyst_calls_this_turn": 0,
            "routing_history": [],
        }
    )
    assert out["routing_history"][0] == "supervisor"
    assert "analyst" in out["routing_history"]
    assert out["analyst_calls_this_turn"] == 1


def test_supervisor_respects_analyst_cap():
    graph = get_chat_graph()
    out = graph.invoke(
        {
            "user_message": "Minh thay khong on",
            "recent_messages": [],
            "mood_today": {"mood": "stressed"},
            "distress_score": 0.9,
            "crisis_route_finalized": False,
            "analyst_calls_this_turn": 2,
            "routing_history": [],
        }
    )
    assert "analyst" not in out["routing_history"]
    assert out["supervisor_reason"] == "analyst_cap_reached"


def test_persona_sanitizer_blocks_may_tao_reply():
    safe = _sanitize_assistant_reply("Mày cứ nói đi, tao nghe.")
    lowered = safe.lower()
    assert "mày" not in lowered
    assert "tao" not in lowered


def test_persona_sanitizer_blocks_may_without_tao():
    safe = _sanitize_assistant_reply("May co van de gi noi tao nghe.")
    lowered = safe.lower()
    assert "may " not in lowered


def test_rule_based_reply_handles_violent_phrase():
    reply = _rule_based_reply("toi muon giet no")
    assert reply is not None
    assert "nguy hiểm" in reply


def test_enforce_reply_quality_expands_short_reply():
    improved = _enforce_reply_quality("Mình hiểu.", "Mình đang rối quá", distress_score=0.3)
    assert len(improved.split()) >= 25
    assert "?" in improved


def test_enforce_reply_quality_keeps_long_empathic_reply():
    original = (
        "Mình nghe bạn đang rất bức xúc vì cảm giác bị đặt vào vùng mập mờ và phải tự đoán ý người ta liên tục, "
        "nên mệt và bất an là điều rất dễ hiểu. Nếu bạn muốn, mình có thể cùng bạn tách rõ điều bạn cần nhất trong mối quan hệ này "
        "để bạn bớt rối hơn ngay lúc này, bạn muốn bắt đầu từ phần nào trước?"
    )
    assert _enforce_reply_quality(original, "toi on", distress_score=0.2) == original


def test_enforce_reply_quality_handles_separation_grief():
    improved = _enforce_reply_quality(
        "Mình hiểu.",
        "mình sắp phải chia xa những người bạn mới quen và mình rất buồn",
        distress_score=0.25,
    )
    lowered = improved.lower()
    assert "chia xa" in lowered
    assert "buồn" in lowered or "buon" in lowered
    assert "?" in improved


def test_build_friend_context_tier2_omits_longterm_memory():
    """Tier 2 (medium distress < 0.65) skips long-term memory to reduce tokens."""
    context = _build_friend_context(
        {
            "distress_score": 0.25,
            "mood_today": None,
            "recent_messages": [{"role": "user", "content": "Mình lại mất ngủ."}],
            "long_term_memories": ["Bạn từng căng thẳng vì deadline.", "Đi bộ 10 phút từng giúp bạn dịu hơn."],
        }
    )
    # Tier 2: recent transcript is present, but long-term memory is excluded.
    assert "mất ngủ" in context
    assert "deadline" not in context


def test_build_friend_context_recall_includes_memory_even_when_low_distress():
    context = _build_friend_context(
        {
            "user_message": "Bạn còn nhớ tôi là ai không?",
            "distress_score": 0.12,
            "mood_today": None,
            "recent_messages": [{"role": "user", "content": "Mình từng kể là mình mất ngủ vì deadline."}],
            "long_term_memories": ["Bạn từng mất ngủ vì deadline và thấy đi bộ ngắn giúp dịu hơn."],
            "mem0_facts": ["Người dùng thích được lắng nghe trước khi nhận lời khuyên."],
        }
    )

    assert "Ký ức liên quan" in context
    assert "deadline" in context
    assert "đi bộ" in context


def test_build_friend_context_tier3_includes_longterm_memory():
    """Tier 3 (high distress ≥ 0.65) includes long-term memory for full context."""
    context = _build_friend_context(
        {
            "distress_score": 0.70,
            "mood_today": {"mood": "stressed", "emoji": ":("},
            "recent_messages": [{"role": "user", "content": "Mình lại mất ngủ."}],
            "long_term_memories": ["Bạn từng căng thẳng vì deadline.", "Đi bộ 10 phút từng giúp bạn dịu hơn."],
            "mem0_facts": [],
        }
    )
    assert "deadline" in context
    assert "Tóm tắt session gần" in context


def test_should_skip_cold_start_profile_for_short_low_distress_turn():
    assert _should_skip_cold_start_profile(
        user_message="ok",
        distress_score=0.12,
        mem0_facts=[],
        long_term_memories=[],
        user_traits={},
    ) is True


def test_should_not_skip_cold_start_profile_for_meaningful_distress_turn():
    assert _should_skip_cold_start_profile(
        user_message="Mình đang kiệt sức vì áp lực kéo dài và không biết bắt đầu từ đâu",
        distress_score=0.48,
        mem0_facts=[],
        long_term_memories=[],
        user_traits={},
    ) is False
