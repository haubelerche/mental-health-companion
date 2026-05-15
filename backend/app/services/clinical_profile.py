"""Shared helpers for ClinicalProfile rows and screening persistence contracts."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.services.db.models import ClinicalProfile
from app.services.utils import make_id

SCREENING_QUESTION_TEXT: dict[str, tuple[str, ...]] = {
    "phq9": (
        "Ít hứng thú hoặc ít thấy vui trong các hoạt động",
        "Cảm thấy buồn, chán nản hoặc tuyệt vọng",
        "Khó ngủ, ngủ không ngon hoặc ngủ quá nhiều",
        "Cảm thấy mệt mỏi hoặc thiếu năng lượng",
        "Ăn không ngon miệng hoặc ăn quá nhiều",
        "Cảm thấy tồi về bản thân hoặc thất bại",
        "Khó tập trung vào mọi việc",
        "Di chuyển hoặc nói chuyện chậm bất thường",
        "Có ý nghĩ tự làm hại bản thân",
    ),
    "gad7": (
        "Cảm thấy lo lắng, bất an hoặc căng thẳng",
        "Không thể ngừng hoặc kiểm soát được lo lắng",
        "Lo lắng quá mức về nhiều thứ khác nhau",
        "Khó thư giãn",
        "Bứt rứt đến mức khó ngồi yên",
        "Dễ khó chịu hoặc cáu kỉnh",
        "Cảm thấy sợ hãi như điều gì đó tồi tệ sắp xảy ra",
    ),
    "dass21": (
        "Khó có thể thư giãn",
        "Bị khô miệng",
        "Gần như không thể thấy một cảm giác vui vẻ hay tích cực nào",
        "Bị khó thở (ví dụ: thở gấp, hụt hơi dù không làm việc nặng)",
        "Thấy khó bắt tay vào công việc",
        "Có xu hướng phản ứng quá mức với các tình huống",
        "Bị run rẩy (ví dụ: run tay)",
        "Thấy mình đang tiêu phí quá nhiều năng lượng thần kinh",
        "Lo lắng về những tình huống có thể làm mình hoảng loạn và làm trò cười cho thiên hạ",
        "Thấy bản thân chẳng có gì để mong đợi phía trước",
        "Thấy bản thân dễ bị kích động",
        "Thấy khó thư giãn",
        "Cảm thấy thất vọng và buồn chán",
        "Không chấp nhận được bất cứ việc gì ngăn cản mình tiếp tục công việc đang làm",
        "Thấy mình gần như phát hoảng",
        "Không thể thấy nhiệt tình với bất cứ việc gì",
        "Thấy bản thân không có giá trị gì nhiều với tư cách là một con người",
        "Thấy mình khá dễ mếch lòng/nhạy cảm",
        "Nghe thấy tiếng nhịp tim dù không làm việc nặng (ví dụ: nhịp tim tăng, nhịp tim bỏ nhịp)",
        "Thấy sợ hãi vô cớ",
        "Thấy cuộc đời vô nghĩa",
    ),
    "mdq": (
        "Thấy quá vui vẻ hoặc hưng phấn đến mức người khác thấy không bình thường hoặc gặp rắc rối",
        "Dễ cáu kỉnh đến mức la hét hoặc tranh cãi, đánh nhau",
        "Tự tin hơn bình thường rất nhiều",
        "Ngủ ít hơn bình thường rất nhiều nhưng vẫn thấy khỏe",
        "Nói nhiều hơn hoặc nói nhanh hơn bình thường",
        "Ý nghĩ chạy dồn dập trong đầu hoặc không thể làm chậm tâm trí lại",
        "Dễ bị phân tâm bởi những thứ xung quanh đến mức khó tập trung",
        "Có nhiều năng lượng hơn bình thường",
        "Năng động hơn hoặc làm nhiều việc hơn bình thường",
        "Hòa đồng hoặc hướng ngoại hơn bình thường (ví dụ: gọi điện lúc nửa đêm)",
        "Quan tâm đến tình dục nhiều hơn bình thường",
        "Làm những việc bất thường hoặc rủi ro, dại dột",
        "Tiêu xài tiền bạc gây rắc rối cho bản thân hoặc gia đình",
        "Các biểu hiện trên xảy ra cùng một thời điểm",
        "Mức độ rắc rối gây ra (công việc, gia đình, pháp lý...)",
    ),
    "pcl5": (
        "Những ký ức lặp đi lặp lại, gây khó chịu và không mong muốn về trải nghiệm căng thẳng",
        "Những giấc mơ lặp đi lặp lại, gây khó chịu về trải nghiệm căng thẳng",
        "Bỗng nhiên cảm thấy hoặc hành động như thể trải nghiệm căng thẳng đang thực sự xảy ra lần nữa",
        "Cảm thấy rất buồn phiền khi có điều gì đó nhắc bạn nhớ về trải nghiệm căng thẳng",
        "Có những phản ứng cơ thể mạnh mẽ khi có điều gì đó nhắc bạn nhớ về trải nghiệm căng thẳng",
        "Né tránh những ký ức, suy nghĩ hoặc cảm xúc liên quan đến trải nghiệm căng thẳng",
        "Né tránh những lời nhắc nhở từ bên ngoài về trải nghiệm căng thẳng (người, địa điểm, đồ vật...)",
        "Khó nhớ lại những phần quan trọng của trải nghiệm căng thẳng",
        "Có niềm tin tiêu cực mạnh mẽ về bản thân, người khác hoặc thế giới",
        "Tự trách mình hoặc người khác về trải nghiệm căng thẳng hoặc những gì đã xảy ra sau đó",
        "Có những cảm xúc tiêu cực mạnh mẽ như sợ hãi, kinh hoàng, tức giận, tội lỗi hoặc xấu hổ",
        "Mất hứng thú với các hoạt động mà bạn từng yêu thích",
        "Cảm thấy xa cách hoặc bị cắt đứt liên lạc với những người khác",
        "Khó trải nghiệm những cảm xúc tích cực",
        "Hành vi cáu kỉnh, bùng nổ tức giận hoặc hành động hung hăng",
        "Chấp nhận quá nhiều rủi ro hoặc làm những việc có thể gây hại cho bản thân",
        "Luôn trong trạng thái 'siêu cảnh giác' hoặc đề phòng",
        "Cảm thấy giật mình hoặc dễ bị hoảng hốt",
        "Khó tập trung",
        "Khó ngủ hoặc khó duy trì giấc ngủ",
    ),
}

SCREENING_ANSWER_LABELS: dict[int, str] = {
    0: "Không hề / Không bao giờ",
    1: "Một chút / Vài ngày",
    2: "Trung bình / Hơn nửa số ngày",
    3: "Nhiều / Gần như mỗi ngày",
    4: "Rất nhiều / Cực kỳ",
}

SCREENING_QUESTION_TEXT_VERSION = {
    "phq9": "phq9_vi_v1",
    "gad7": "gad7_vi_v1",
    "dass21": "dass21_vi_v1",
    "mdq": "mdq_vi_v1",
    "pcl5": "pcl5_vi_v1",
}
SCREENING_ANSWER_OPTIONS_VERSION = "likert_0_3_vi_v1"


def compute_screening_severity(instrument_id: str, raw_score: int) -> str:


    if instrument_id == "phq9":
        if raw_score <= 4: return "minimal"
        if raw_score <= 9: return "mild"
        if raw_score <= 14: return "moderate"
        if raw_score <= 19: return "moderately_severe"
        return "severe"
    if instrument_id == "gad7":
        if raw_score <= 4: return "minimal"
        if raw_score <= 9: return "mild"
        if raw_score <= 14: return "moderate"
        return "severe"
    if instrument_id == "dass21":
        # Note: This is usually handled per subscale, returning a general summary here
        return "assessed"
    if instrument_id == "mdq":
        return "positive" if raw_score >= 7 else "negative"
    if instrument_id == "pcl5":
        return "high_risk" if raw_score >= 33 else "low_risk"
    raise ValueError(f"unsupported instrument_id: {instrument_id}")


def build_screening_answer_payload(
    *,
    user_id: str,
    instrument_id: str,
    answers: dict[str, int],
    submitted_at: datetime,
    session_id: str | None = None,
    locale: str = "vi-VN",
) -> dict[str, Any]:
    questions = SCREENING_QUESTION_TEXT.get(instrument_id)
    if questions is None:
        raise ValueError(f"unsupported instrument_id: {instrument_id}")

    responses: list[dict[str, Any]] = []
    for question_key, answer_value in sorted(answers.items(), key=lambda item: item[0]):
        question_index = int(question_key.removeprefix("q"))
        if question_index < 0 or question_index >= len(questions):
            raise ValueError(f"unexpected question key: {question_key}")
        value = int(answer_value)
        if value not in SCREENING_ANSWER_LABELS:
            raise ValueError(f"unexpected answer value: {value}")
        responses.append(
            {
                "question_id": question_key,
                "question_key": question_key,
                "question_order": question_index,
                "question_text": questions[question_index],
                "answer_value": value,
                "answer_label": SCREENING_ANSWER_LABELS[value],
            }
        )

    return {
        "user_id": user_id,
        "screening_type": instrument_id,
        "instrument_id": instrument_id,
        "submitted_at": submitted_at.isoformat() + "Z",
        "session_id": session_id,
        "locale": locale,
        "question_text_version": SCREENING_QUESTION_TEXT_VERSION[instrument_id],
        "answer_options_version": SCREENING_ANSWER_OPTIONS_VERSION,
        "submitted_answer_map": {key: int(value) for key, value in sorted(answers.items())},
        "responses": responses,
    }


def apply_screening_to_clinical_profile(
    *,
    profile: ClinicalProfile,
    instrument_id: str,
    raw_score: int,
    scored_at: datetime,
) -> None:
    coverage = {
        "covered": True,
        "item_count": len(SCREENING_QUESTION_TEXT[instrument_id]),
        "score_type": "questionnaire",
        "instrument_id": instrument_id,
    }
    if instrument_id == "phq9":
        profile.phq9_score = min(27, raw_score)
        profile.phq9_coverage = coverage
    elif instrument_id == "gad7":
        profile.gad7_score = min(21, raw_score)
        profile.gad7_coverage = coverage
    elif instrument_id == "dass21":
        # raw_score here should be a sum of subscores if passed as such, 
        # or we might need to handle subscores specifically. 
        # For now, following the 'save same as PHQ9' instruction:
        profile.dass21_depression_score = raw_score # Simplification
        profile.dass21_coverage = coverage
    elif instrument_id == "mdq":
        profile.mdq_score = raw_score
        profile.mdq_coverage = coverage
    elif instrument_id == "pcl5":
        profile.pcl5_score = raw_score
        profile.pcl5_coverage = coverage
    else:
        raise ValueError(f"unsupported instrument_id: {instrument_id}")
    profile.score_source = "questionnaire"
    profile.model_version = "questionnaire_v1"
    profile.last_scored_at = scored_at
    profile.updated_at = scored_at


def get_or_create_clinical_profile(db: Session, user_id: str) -> ClinicalProfile:
    row = db.scalar(select(ClinicalProfile).where(ClinicalProfile.user_id == user_id))
    if row:
        return row
    row = ClinicalProfile(profile_id=make_id("clin"), user_id=user_id)
    db.add(row)
    db.flush()
    return row
