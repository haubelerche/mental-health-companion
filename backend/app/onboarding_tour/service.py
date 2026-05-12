from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.services.db.models import OnboardingTourState, User, UserProfile
from app.services.utils import get_now

TourStatus = Literal[
    "not_started",
    "available",
    "in_progress",
    "paused_for_safety",
    "completed",
    "skipped",
    "dismissed",
]

ALLOWED_STATUSES: set[str] = {
    "not_started",
    "available",
    "in_progress",
    "paused_for_safety",
    "completed",
    "skipped",
    "dismissed",
}


@dataclass(frozen=True)
class OnboardingTourStep:
    step_id: str
    route: str
    target_anchor_id: str | None
    title: str
    body: str
    primary_cta: str
    secondary_cta: str | None
    allow_skip: bool
    requires_navigation: bool
    action_kind: str


BASE_FIRST_RUN_STEPS: tuple[OnboardingTourStep, ...] = (
    OnboardingTourStep(
        "welcome",
        "/serene",
        None,
        "Để mình dẫn bạn đi một vòng",
        "Chào bạn. Mình sẽ dẫn bạn đi quanh ứng dụng một vòng nhé để đỡ phải mò mà dùng cho nhanh ấy :3",
        "Dẫn mình đi",
        "Để mình tự khám phá",
        True,
        False,
        "read_only",
    ),
    OnboardingTourStep(
        "home_today",
        "/serene",
        "home-today-card",
        "Hôm nay nên bắt đầu ở đâu",
        "Đây là góc để bắt đầu mỗi ngày. Mình sẽ chỉ bạn vài lối vào nhỏ: check-in cảm xúc, đọc một mẩu tri thức, hoặc quay lại cuộc trò chuyện gần nhất.",
        "Tiếp tục",
        None,
        True,
        True,
        "read_only",
    ),
    OnboardingTourStep(
        "mood_checkin",
        "/serene",
        "mood-checkin-card",
        "Cho mình biết hôm nay bạn thế nào",
        "Check-in cảm xúc là cách nhẹ nhất để bắt đầu. Chọn một mức thôi cũng được, không cần giải thích dài.",
        "Thử check-in",
        "Để sau",
        True,
        True,
        "optional_try",
    ),
    OnboardingTourStep(
        "chat_intro",
        "/serene/chat",
        "chat-input",
        "Nơi bạn kể chuyện",
        "Ở đây bạn có thể kể chuyện tự nhiên. Kể lộn xộn cũng được, mình sẽ cùng bạn tháo mớ bòng bong đó từng chút một.",
        "Tiếp tục",
        None,
        True,
        True,
        "navigate",
    ),
    OnboardingTourStep(
        "chat_style",
        "/serene/chat",
        "sidebar-chat",
        "Bạn có thể chọn nhân dạng, tính cách cho mình đó nhé!",
        "Mỗi nhân vật có một cách nói chuyện riêng. Khi đổi nhân vật, cuộc trò chuyện sẽ đi theo đúng giọng và ngữ cảnh của nhân vật đó.",
        "Tiếp tục",
        None,
        True,
        True,
        "read_only",
    ),
    OnboardingTourStep(
        "memory_cards",
        "/serene/chat",
        "chat-memory-tab",
        "Mình chỉ nhớ những điều bạn muốn mình nhớ",
        "Nếu sau này mình rút ra một điều hữu ích để nhớ thì nó sẽ nằm ở tab Ký ức nhá. Bạn có thể giữ lại hoặc xoá bất cứ lúc nào.",
        "Đã hiểu",
        None,
        True,
        True,
        "read_only",
    ),
    OnboardingTourStep(
        "rewards_intro",
        "/serene/rewards",
        "sidebar-rewards",
        "Tim không thưởng cho spam chat",
        "Tim là điểm khích lệ cho những việc có ích như check-in, chăm sóc lối sống của chính mình, trau dồi tri thức, viết thư lan tỏa điều tích cực.",
        "Tiếp tục",
        None,
        True,
        True,
        "navigate",
    ),
    OnboardingTourStep(
        "knowledge_intro",
        "/serene/resources",
        "sidebar-resources",
        "Hiểu bản thân, không tự chẩn đoán",
        "Phần này giúp bạn hiểu các pattern cảm xúc bằng ngôn ngữ dễ đọc. Nó không dùng để chẩn đoán, chỉ giúp bạn có thêm cách nhìn.",
        "Tiếp tục",
        None,
        True,
        True,
        "navigate",
    ),
    OnboardingTourStep(
        "safety_help",
        "/serene/support",
        "sidebar-help",
        "Khi cuộc sống khó khăn hơn trước",
        "Nếu có lúc vấn đề của bạn nặng nề hơn bình thường, mình sẽ ưu tiên an toàn của bạn trước và gợi ý bạn kết nối với hỗ trợ ngoài đời.",
        "Tiếp tục",
        None,
        True,
        True,
        "navigate",
    ),
    OnboardingTourStep(
        "finish",
        "/serene",
        None,
        "Chọn điểm bắt đầu",
        "Xong rồi. Bạn muốn bắt đầu bằng check-in, hay vào Chat kể thử một chút?",
        "Check-in cảm xúc",
        "Để mình tự khám phá",
        True,
        True,
        "read_only",
    ),
)

TOUR_COPY_OVERRIDES: dict[str, dict[str, str | None]] = {
    "welcome": {
        "title": "Mình sẽ dẫn bạn đi tham quan ứng dụng",
        "body": "Chào bạn. Mình sẽ dẫn bạn tham quan ứng dụng để bạn biết lúc nào nên dùng phần nào.",
        "primary_cta": "Tiếp theo",
        "secondary_cta": None,
    },
    "home_today": {
        "title": "Hôm nay nên bắt đầu ở đâu",
        "body": "Đây là góc bắt đầu mỗi ngày. Bạn sẽ: check-in cảm xúc, đọc một mẩu tri thức, hoặc quay lại cuộc trò chuyện gần nhất.",
        "primary_cta": "Tiếp theo",
        "secondary_cta": None,
    },
    "mood_checkin": {
        "title": "Cho mình biết hôm nay bạn thế nào",
        "body": "Check-in cảm xúc là cách nhẹ nhất để bắt đầu. Chỉ cần nói ra cảm xúc hiện tại của bạn là được, không cần phải mô tả dài nếu bạn không muốn.",
        "primary_cta": "Tiếp theo",
        "secondary_cta": None,
    },
    "chat_intro": {
        "title": "Nơi bạn kể chuyện",
        "body": "Ở đây bạn có thể kể chuyện tự nhiên. Kể lộn xộn cũng được, mình sẽ cùng bạn tâm sự, giãi bày từng chút.",
        "primary_cta": "Tiếp theo",
        "secondary_cta": None,
    },
    "chat_style": {
        "title": "Bạn muốn mình trở thành nhân dạng nào?",
        "body": "Bạn có thể chọn cách mình trò chuyện: thân thiện, trang trọng, hoặc tò mò hơn.",
        "primary_cta": "Tiếp theo",
        "secondary_cta": None,
    },
    "memory_cards": {
        "title": "Mình sẽ chỉ nhớ những điều bạn muốn mình nhớ",
        "body": "Nếu sau này mình rút ra một điều hữu ích để nhớ, nó sẽ nằm ở tab Ký ức. Bạn có thể giữ, sửa hoặc xoá.",
        "primary_cta": "Tiếp theo",
        "secondary_cta": None,
    },
    "rewards_intro": {
        "title": "Mình không thưởng cho spam heart",
        "body": "Tim là điểm khích lệ cho những việc có ích như check-in, chăm cơ thể, đọc tri thức, viết thư an toàn hoặc quay lại đều đặn.",
        "primary_cta": "Tiếp theo",
        "secondary_cta": None,
    },
    "knowledge_intro": {
        "title": "Hiểu bản thân, không tự chẩn đoán",
        "body": "Phần này giúp bạn hiểu các pattern cảm xúc bằng ngôn ngữ dễ đọc. Nó không dùng để chẩn đoán, chỉ giúp bạn có thêm cách nhìn.",
        "primary_cta": "Tiếp theo",
        "secondary_cta": None,
    },
    "safety_help": {
        "title": "Khi mọi thứ nặng hơn bình thường",
        "body": "Nếu có lúc mọi thứ quá nặng, mình sẽ ưu tiên an toàn trước và gợi ý bạn kết nối với hỗ trợ ngoài đời.",
        "primary_cta": "Tiếp theo",
        "secondary_cta": None,
    },
    "finish": {
        "title": "Chọn điểm bắt đầu",
        "body": "Xong rồi. Bạn có thể bắt đầu bằng check-in, hoặc vào Chat kể thử một chút.",
        "primary_cta": "Tiếp theo",
        "secondary_cta": None,
    },
}


def _present_tour_step(step: OnboardingTourStep) -> dict[str, Any]:
    data = asdict(step)
    data.update(TOUR_COPY_OVERRIDES.get(step.step_id, {}))
    return data


def _now() -> datetime:
    return get_now().replace(tzinfo=None)


def _dedupe(values: list[Any] | None) -> list[str]:
    result: list[str] = []
    for value in values or []:
        text = str(value)
        if text not in result:
            result.append(text)
    return result


def safe_profile_summary(onboarding_profile: dict[str, Any] | None) -> dict[str, str]:
    profile = dict(onboarding_profile or {})
    summary: dict[str, str] = {}
    nickname = str(profile.get("nickname") or "").strip()
    if nickname:
        summary["display_name"] = nickname[:64]

    concern = str(profile.get("primary_concern") or "").strip()
    practice_ids = [str(item) for item in profile.get("practice_ids") or []]
    if concern:
        summary["support_goal"] = concern[:64]
    elif "better_sleep" in practice_ids:
        summary["support_goal"] = "sleep"
    elif "mood_tracking" in practice_ids:
        summary["support_goal"] = "stress"
    elif practice_ids:
        summary["support_goal"] = practice_ids[0][:64]
    else:
        summary["support_goal"] = "general"

    emotional_state = str(profile.get("emotional_state") or "")
    summary["preferred_style"] = "quiet" if emotional_state == "difficult_recently" else "warm"
    return summary


def build_first_run_tour_plan(
    user: User,
    onboarding_profile: dict[str, Any] | None,
    feature_flags: dict[str, bool] | None = None,
) -> list[dict[str, Any]]:
    del user, onboarding_profile
    flags = feature_flags or {}
    steps = list(BASE_FIRST_RUN_STEPS)
    if flags.get("rewards_store_enabled", True) is False:
        steps = [step for step in steps if step.step_id != "rewards_intro"]
    if flags.get("memory_cards_enabled", True) is False:
        steps = [step for step in steps if step.step_id != "memory_cards"]
    if flags.get("knowledge_unlocks_enabled", True) is False:
        steps = [step for step in steps if step.step_id != "knowledge_intro"]
    return [_present_tour_step(step) for step in steps]


def get_onboarding_profile(db: Session, user_id: str) -> dict[str, Any]:
    row = db.scalar(select(UserProfile).where(UserProfile.user_id == user_id))
    profile_data = dict(row.profile or {}) if row else {}
    return dict(profile_data.get("onboarding") or {})


def get_or_create_tour_state(db: Session, user_id: str) -> OnboardingTourState:
    state = db.scalar(select(OnboardingTourState).where(OnboardingTourState.user_id == user_id))
    if state is None:
        state = OnboardingTourState(
            user_id=user_id,
            status="not_started",
            variant="first_run",
            completed_step_ids=[],
            skipped_step_ids=[],
            metadata_json={},
        )
        db.add(state)
        db.flush()
    return state


def make_tour_available_after_onboarding(db: Session, user_id: str) -> OnboardingTourState:
    state = get_or_create_tour_state(db, user_id)
    if state.status not in {"completed", "skipped", "dismissed"}:
        state.status = "available"
        state.variant = "first_run"
        state.current_step_id = "welcome"
        state.last_seen_at = _now()
        state.updated_at = _now()
    return state


def serialize_tour_state(db: Session, user: User, state: OnboardingTourState) -> dict[str, Any]:
    onboarding_profile = get_onboarding_profile(db, user.user_id)
    steps = build_first_run_tour_plan(user, onboarding_profile, state.metadata_json.get("feature_flags", {}))
    return {
        "status": state.status,
        "current_step_id": state.current_step_id,
        "steps": steps,
        "completed_step_ids": _dedupe(state.completed_step_ids),
        "skipped_step_ids": _dedupe(state.skipped_step_ids),
        "variant": state.variant,
        "safe_profile_summary": safe_profile_summary(onboarding_profile),
    }


def start_tour(db: Session, user: User, variant: str = "first_run") -> OnboardingTourState:
    state = get_or_create_tour_state(db, user.user_id)
    state.status = "in_progress"
    state.variant = variant or "first_run"
    state.current_step_id = "welcome"
    state.dismissed_at = None
    state.completed_at = None
    state.last_seen_at = _now()
    state.updated_at = _now()
    return state


def progress_tour(
    db: Session,
    user: User,
    step_id: str,
    skipped: bool = False,
    next_step_id: str | None = None,
) -> OnboardingTourState:
    state = get_or_create_tour_state(db, user.user_id)
    onboarding_profile = get_onboarding_profile(db, user.user_id)
    step_ids = [step["step_id"] for step in build_first_run_tour_plan(user, onboarding_profile, {})]
    if step_id not in step_ids:
        raise AppError("TOUR_STEP_INVALID", "Tour step không hợp lệ", 400)
    if next_step_id is not None and next_step_id not in step_ids:
        raise AppError("TOUR_STEP_INVALID", "Tour step tiếp theo không hợp lệ", 400)

    completed = _dedupe(state.completed_step_ids)
    skipped_ids = _dedupe(state.skipped_step_ids)
    if skipped:
        if step_id not in skipped_ids:
            skipped_ids.append(step_id)
    elif step_id not in completed:
        completed.append(step_id)

    state.status = "in_progress"
    state.completed_step_ids = completed
    state.skipped_step_ids = skipped_ids
    if next_step_id is not None:
        state.current_step_id = next_step_id
    else:
        index = step_ids.index(step_id)
        state.current_step_id = step_ids[index + 1] if index + 1 < len(step_ids) else "finish"
    state.last_seen_at = _now()
    state.updated_at = _now()
    return state


def complete_tour(db: Session, user: User) -> OnboardingTourState:
    state = get_or_create_tour_state(db, user.user_id)
    state.status = "completed"
    state.current_step_id = "finish"
    state.completed_at = state.completed_at or _now()
    state.last_seen_at = _now()
    state.updated_at = _now()
    return state


def skip_tour(db: Session, user: User) -> OnboardingTourState:
    state = get_or_create_tour_state(db, user.user_id)
    state.status = "skipped"
    state.current_step_id = state.current_step_id or "welcome"
    state.last_seen_at = _now()
    state.updated_at = _now()
    return state


def dismiss_tour(db: Session, user: User) -> OnboardingTourState:
    state = get_or_create_tour_state(db, user.user_id)
    state.status = "dismissed"
    state.dismissed_at = state.dismissed_at or _now()
    state.last_seen_at = _now()
    state.updated_at = _now()
    return state
