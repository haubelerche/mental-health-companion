from app.api.v1.routers.chat import _should_load_memory_context
from app.services.langgraph_chat import _recent_transcript_hint


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
