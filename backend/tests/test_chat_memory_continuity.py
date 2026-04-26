from app.api.v1.routers.chat import _should_load_memory_context
from app.services.langgraph_chat import _build_friend_context, _recent_transcript_hint, _should_skip_cold_start_profile


def test_should_load_memory_context_for_recall_question():
    recent = [{"role": "user", "content": "Mình vừa kể chuyện gia đình"}, {"role": "assistant", "content": "Mình đang nghe bạn"}]
    assert _should_load_memory_context("bạn còn nhớ tôi là ai không", recent) is True


def test_should_load_memory_context_for_long_session():
    recent = [
        {"role": "user", "content": "1"},
        {"role": "assistant", "content": "2"},
        {"role": "user", "content": "3"},
        {"role": "assistant", "content": "4"},
    ]
    assert _should_load_memory_context("ok", recent) is True


def test_should_load_memory_context_false_for_new_short_turn():
    recent = [{"role": "user", "content": "chào"}]
    assert _should_load_memory_context("ok", recent) is False


def test_recent_transcript_hint_keeps_last_turns():
    state = {
        "recent_messages": [
            {"role": "user", "content": "turn 1"},
            {"role": "assistant", "content": "turn 2"},
            {"role": "user", "content": "turn 3"},
            {"role": "assistant", "content": "turn 4"},
        ]
    }
    hint = _recent_transcript_hint(state, max_turns=3, max_chars_per_turn=20)
    assert "turn 1" not in hint
    assert "assistant: turn 2" in hint
    assert "user: turn 3" in hint
    assert "assistant: turn 4" in hint


def test_recall_context_includes_memory_even_when_low_distress():
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
