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
}

SCREENING_ANSWER_LABELS: dict[int, str] = {
    0: "Không bao giờ",
    1: "Vài ngày",
    2: "Hơn nửa số ngày",
    3: "Gần như mỗi ngày",
}

SCREENING_QUESTION_TEXT_VERSION = {
    "phq9": "phq9_vi_v1",
    "gad7": "gad7_vi_v1",
}
SCREENING_ANSWER_OPTIONS_VERSION = "likert_0_3_vi_v1"


def compute_screening_severity(*, instrument_id: str, raw_score: int) -> str:
    if instrument_id == "phq9":
        if raw_score <= 4:
            return "minimal"
        if raw_score <= 9:
            return "mild"
        if raw_score <= 14:
            return "moderate"
        if raw_score <= 19:
            return "moderately_severe"
        return "severe"
    if instrument_id == "gad7":
        if raw_score <= 4:
            return "minimal"
        if raw_score <= 9:
            return "mild"
        if raw_score <= 14:
            return "moderate"
        return "severe"
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
