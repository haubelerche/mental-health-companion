from app.services.response_planner import build_response_plan
from app.services.safety_output_validator import count_questions, has_markdown


FORBIDDEN = (
    "tôi rất tiếc khi nghe",
    "cảm xúc của bạn là hoàn toàn hợp lệ",
    "bạn không đơn độc",
    "mọi chuyện rồi sẽ ổn",
    "hãy suy nghĩ tích cực",
    "bạn thật dũng cảm khi chia sẻ",
    "tôi luôn ở đây để hỗ trợ bạn",
    "bạn nên tìm kiếm sự giúp đỡ chuyên nghiệp",
)


def test_response_is_short_and_context_specific():
    plan = build_response_plan(
        user_message="mai deadline rồi mà t chưa làm gì",
        candidate_text="Tôi hiểu rằng bạn đang cảm thấy rất buồn và áp lực.",
        distress_score=0.35,
    )

    lowered = plan.visible_text.lower()
    assert (
        "điều bạn vừa kể" in lowered
        or "deadline" in lowered
        or "quá tải" in lowered
        or "nhiều thứ" in lowered
    )
    assert len(plan.visible_text.split(".")) <= 4


def test_no_generic_therapy_script_phrases():
    plan = build_response_plan(
        user_message="tự nhiên thấy mình kém cỏi ghê",
        candidate_text="Cảm xúc của bạn là hoàn toàn hợp lệ. Bạn không đơn độc.",
        distress_score=0.5,
    )

    lowered = plan.visible_text.lower()
    assert all(phrase not in lowered for phrase in FORBIDDEN)


def test_max_one_question_per_response():
    plan = build_response_plan(
        user_message="hôm nay mệt quá",
        candidate_text="Nghe hôm nay bạn mệt thật. Bạn mệt vì việc nhiều quá hả? Có chuyện nào khác không?",
        distress_score=0.25,
    )

    assert count_questions(plan.visible_text) <= 1


def test_response_reflects_user_context_detail():
    plan = build_response_plan(
        user_message="mấy hôm nay mất ngủ nên đầu óc rối tung",
        candidate_text="Bạn không đơn độc. Mọi chuyện rồi sẽ " + "ổn.",
        distress_score=0.62,
    )

    assert "mất ngủ" in plan.visible_text


def test_final_text_has_no_markdown_for_emotional_chat():
    plan = build_response_plan(
        user_message="t thấy mọi thứ rối tung lên hết",
        candidate_text="- Mình nghe bạn đang quá tải thật.\n- Bạn thử thở chậm lại nhé.",
        distress_score=0.65,
    )

    assert not has_markdown(plan.visible_text)
