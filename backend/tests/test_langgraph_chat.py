from app.services.langgraph_chat import (
    _build_friend_context,
    _enforce_reply_quality,
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


def test_build_friend_context_includes_long_term_memory():
    context = _build_friend_context(
        {
            "distress_score": 0.25,
            "mood_today": None,
            "recent_messages": [{"role": "user", "content": "Mình lại mất ngủ."}],
            "long_term_memories": ["Bạn từng căng thẳng vì deadline.", "Đi bộ 10 phút từng giúp bạn dịu hơn."],
        }
    )
    assert "Long-term memory về người dùng" in context
    assert "deadline" in context
