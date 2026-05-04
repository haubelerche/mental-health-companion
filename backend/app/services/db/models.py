from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    BIGINT,
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.services.db.session import Base

try:
    from pgvector.sqlalchemy import Vector
except ImportError:  # pragma: no cover
    Vector = None


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    disclaimer_accepted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    analytics_opt_in: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    data_retention_days: Mapped[int] = mapped_column(Integer, default=90, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    last_active: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    policy_acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    policy_version_ack: Mapped[str | None] = mapped_column(String(32), nullable=True)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    token_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(45))
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class EmailVerificationToken(Base):
    __tablename__ = "email_verification_tokens"

    token_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    resend_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_sent_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    token_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class Conversation(Base):
    __tablename__ = "conversations"

    session_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"), nullable=False)
    message_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    last_message_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime)
    hard_deleted_at: Mapped[datetime | None] = mapped_column(DateTime)
    anonymous_summary: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    summarized_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        CheckConstraint("role IN ('user','assistant')", name="chk_role"),
        CheckConstraint(
            "tone_cam_xuc IS NULL OR tone_cam_xuc IN ('ho_tro','xac_nhan','vui_tuoi','lam_diu')",
            name="chk_tone",
        ),
        CheckConstraint("length(content) <= 2000", name="chk_content_length"),
    )

    message_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("conversations.session_id"), nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tone_cam_xuc: Mapped[str | None] = mapped_column(String(20))
    sos_triggered: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class MoodCheckin(Base):
    __tablename__ = "mood_checkins"
    __table_args__ = (UniqueConstraint("user_id", "logged_date", name="uq_mood_per_day"),)

    checkin_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"), nullable=False)
    mood: Mapped[str] = mapped_column(String(50), nullable=False)
    emoji: Mapped[str | None] = mapped_column(String(10))
    emotions: Mapped[list[Any] | None] = mapped_column(JSON)
    triggers: Mapped[list[Any] | None] = mapped_column(JSON)
    note: Mapped[str | None] = mapped_column(Text)
    logged_date: Mapped[date] = mapped_column(Date, nullable=False)
    logged_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime)


class ClinicalProfile(Base):
    __tablename__ = "clinical_profiles"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_clinical_user"),
        CheckConstraint("phq9_score IS NULL OR (phq9_score >= 0 AND phq9_score <= 27)", name="chk_phq9"),
        CheckConstraint("gad7_score IS NULL OR (gad7_score >= 0 AND gad7_score <= 21)", name="chk_gad7"),
        CheckConstraint("crisis_level >= 0 AND crisis_level <= 5", name="chk_crisis_level"),
    )

    profile_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"), nullable=False)
    phq9_score: Mapped[int | None] = mapped_column(Integer)
    gad7_score: Mapped[int | None] = mapped_column(Integer)
    phq9_coverage: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    gad7_coverage: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    crisis_level: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_scored_at: Mapped[datetime | None] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class CrisisLog(Base):
    __tablename__ = "crisis_logs"

    log_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("conversations.session_id"), nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"), nullable=False)
    muc_do: Mapped[str] = mapped_column(String(20), nullable=False)
    context_summary: Mapped[str | None] = mapped_column(Text)
    reviewed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    triggered_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime)
    reviewed_by: Mapped[str | None] = mapped_column(String(50))


class JournalPrompt(Base):
    __tablename__ = "journal_prompts"

    prompt_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class JournalEntry(Base):
    __tablename__ = "journal_entries"
    __table_args__ = (CheckConstraint("length(content) <= 10000", name="chk_journal_length"),)

    journal_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"), nullable=False)
    prompt_id: Mapped[str | None] = mapped_column(ForeignKey("journal_prompts.prompt_id"))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime)


class Resource(Base):
    __tablename__ = "resources"

    resource_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    format: Mapped[str] = mapped_column(String(20), nullable=False)
    duration_sec: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    thumbnail_key: Mapped[str | None] = mapped_column(String(500))
    tags: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class Bookmark(Base):
    __tablename__ = "bookmarks"
    __table_args__ = (UniqueConstraint("user_id", "resource_id", name="uq_bookmark"),)

    bookmark_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"), nullable=False)
    resource_id: Mapped[str] = mapped_column(ForeignKey("resources.resource_id"), nullable=False)
    bookmarked_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class PlayEvent(Base):
    __tablename__ = "play_events"
    __table_args__ = (
        CheckConstraint("event IN ('started','paused','completed')", name="chk_event"),
        CheckConstraint("duration_sec >= 0", name="chk_duration_non_negative"),
        CheckConstraint("percent >= 0 AND percent <= 100", name="chk_percent_range"),
    )

    event_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"), nullable=False)
    resource_id: Mapped[str] = mapped_column(ForeignKey("resources.resource_id"), nullable=False)
    event: Mapped[str] = mapped_column(String(20), nullable=False)
    duration_sec: Mapped[int] = mapped_column(Integer, nullable=False)
    percent: Mapped[int] = mapped_column(Integer, nullable=False)
    tracked_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class ConversationMemory(Base):
    __tablename__ = "conversation_memories"
    __table_args__ = (
        CheckConstraint(
            "importance_score IS NULL OR (importance_score >= 0 AND importance_score <= 1)",
            name="chk_importance",
        ),
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="chk_confidence",
        ),
    )

    memory_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"), nullable=False)
    session_id: Mapped[str | None] = mapped_column(
        ForeignKey("conversations.session_id", ondelete="SET NULL")
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    memory_type: Mapped[str | None] = mapped_column(String(50))
    if Vector is not None:
        embedding: Mapped[Any] = mapped_column(Vector(1536), nullable=False)
    else:
        embedding: Mapped[list[float]] = mapped_column(JSON, nullable=False)
    importance_score: Mapped[float | None] = mapped_column(Float)
    confidence: Mapped[float | None] = mapped_column(Float)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class AdminAuditLog(Base):
    __tablename__ = "admin_audit_log"

    audit_id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    admin_id: Mapped[str] = mapped_column(String(50), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_accessed: Mapped[str | None] = mapped_column(String(255))
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class UserProfile(Base):
    __tablename__ = "user_profiles"

    user_id: Mapped[str] = mapped_column(String(50), ForeignKey("users.user_id"), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    profile: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class UserProfileSnapshot(Base):
    __tablename__ = "user_profile_snapshots"

    snapshot_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"), nullable=False)
    profile: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class CounselingKnowledge(Base):
    __tablename__ = "counseling_knowledge"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    response: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="mental_health_v1")
    if Vector is not None:
        embedding: Mapped[Any] = mapped_column(Vector(1536), nullable=True)
    else:
        embedding: Mapped[list[float] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class SyncOutbox(Base):
    __tablename__ = "sync_outbox"

    outbox_id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.user_id"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


# ---------------------------------------------------------------------------
# Heart Economy (Plan 03)
# ---------------------------------------------------------------------------

class HeartWallet(Base):
    __tablename__ = "heart_wallets"
    __table_args__ = (
        CheckConstraint("balance >= 0", name="chk_wallet_balance_nonneg"),
        CheckConstraint("lifetime_earned >= 0", name="chk_wallet_earned_nonneg"),
        CheckConstraint("lifetime_spent >= 0", name="chk_wallet_spent_nonneg"),
    )

    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"), primary_key=True)
    balance: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    lifetime_earned: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    lifetime_spent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    daily_earned_today: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    daily_earned_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class HeartRewardEvent(Base):
    __tablename__ = "heart_reward_events"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_reward_idempotency"),
        CheckConstraint("amount > 0", name="chk_reward_amount_pos"),
    )

    event_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    source_tab: Mapped[str] = mapped_column(String(50), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(20), default="granted", nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class StreakState(Base):
    __tablename__ = "streak_states"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"), primary_key=True)
    current_mood_checkin_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    longest_mood_checkin_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_mood_checkin_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_7d_bonus_streak_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class NutritionMealCheckin(Base):
    __tablename__ = "nutrition_meal_checkins"
    __table_args__ = (
        UniqueConstraint("user_id", "meal_date", "meal_slot", name="uq_nutrition_slot"),
        CheckConstraint(
            "meal_slot IN ('breakfast', 'lunch', 'dinner')",
            name="chk_meal_slot",
        ),
    )

    checkin_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"), nullable=False)
    meal_date: Mapped[date] = mapped_column(Date, nullable=False)
    meal_slot: Mapped[str] = mapped_column(String(20), nullable=False)
    items_text: Mapped[str] = mapped_column(Text, nullable=False)
    photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    mood_before: Mapped[str | None] = mapped_column(String(50), nullable=True)
    mood_after: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reward_event_id: Mapped[str | None] = mapped_column(ForeignKey("heart_reward_events.event_id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class TherapyLetter(Base):
    """Personal long-form therapeutic letter (tab Thư). Distinct from the social letters table."""

    __tablename__ = "therapy_letters"

    letter_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"), nullable=False)
    recipient_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    letter_text: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    word_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending_review", nullable=False)
    reward_event_id: Mapped[str | None] = mapped_column(ForeignKey("heart_reward_events.event_id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


# ---------------------------------------------------------------------------
# Reward Store (Plan 04)
# ---------------------------------------------------------------------------

class HeartSpendEvent(Base):
    __tablename__ = "heart_spend_events"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_spend_idempotency"),
        CheckConstraint("amount > 0", name="chk_spend_amount_pos"),
    )

    event_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"), nullable=False)
    item_id: Mapped[str] = mapped_column(String(100), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(20), default="spent", nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class RewardStoreItem(Base):
    __tablename__ = "reward_store_items"
    __table_args__ = (
        CheckConstraint("price_hearts >= 100 AND price_hearts <= 10000", name="chk_price_range"),
        CheckConstraint("tier >= 1", name="chk_tier_pos"),
    )

    item_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    item_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    subtitle: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price_hearts: Mapped[int] = mapped_column(Integer, nullable=False)
    tier: Mapped[int] = mapped_column(Integer, nullable=False)
    icon_key: Mapped[str | None] = mapped_column(String(100), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict, nullable=False)
    requirements: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class UserInventoryItem(Base):
    __tablename__ = "user_inventory_items"
    __table_args__ = (UniqueConstraint("user_id", "item_id", name="uq_inventory_item"),)

    inventory_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"), nullable=False)
    item_id: Mapped[str] = mapped_column(ForeignKey("reward_store_items.item_id"), nullable=False)
    acquired_source: Mapped[str] = mapped_column(String(50), nullable=False)
    spend_event_id: Mapped[str | None] = mapped_column(ForeignKey("heart_spend_events.event_id"), nullable=True)
    acquired_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict, nullable=False)


# ---------------------------------------------------------------------------
# Persona Unlock Progression (Plan 05)
# ---------------------------------------------------------------------------

class PersonaUnlockState(Base):
    __tablename__ = "persona_unlock_states"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"), primary_key=True)
    persona_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    unlocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    unlocked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    unlock_source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    required_hearts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    progress: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    requirements: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    boundary_accepted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


# ---------------------------------------------------------------------------
# Memory Cards (Plan 06)
# ---------------------------------------------------------------------------

class MemoryCard(Base):
    __tablename__ = "memory_cards"
    __table_args__ = (
        CheckConstraint(
            "memory_type IN ('preference','emotional_pattern','coping_history',"
            "'current_stressor','nutrition_pattern','kindness_pattern','persona_preference')",
            name="chk_memory_type",
        ),
        CheckConstraint(
            "status IN ('pending_user_review','active','edited_by_user',"
            "'deleted_by_user','rejected_by_guardrail')",
            name="chk_memory_status",
        ),
        CheckConstraint(
            "safety_review_status IN ('pending','approved','rejected')",
            name="chk_safety_review_status",
        ),
    )

    card_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
    )
    source_session_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    memory_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(
        String(30), default="pending_user_review", nullable=False
    )
    safety_review_status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False
    )
    personalization_disabled: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, default=dict, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


# ---------------------------------------------------------------------------
# Knowledge Unlocks (Plan 07)
# ---------------------------------------------------------------------------

class KnowledgePack(Base):
    __tablename__ = "knowledge_packs"
    __table_args__ = (
        CheckConstraint(
            "price_hearts IS NULL OR (price_hearts >= 100 AND price_hearts <= 10000)",
            name="chk_kp_price_range",
        ),
    )

    pack_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    price_hearts: Mapped[int | None] = mapped_column(Integer, nullable=True)
    required_item_id: Mapped[str | None] = mapped_column(
        ForeignKey("reward_store_items.item_id"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class KnowledgeCard(Base):
    __tablename__ = "knowledge_cards"

    card_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    pack_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_packs.pack_id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    estimated_read_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reflection_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)


class UserKnowledgeProgress(Base):
    __tablename__ = "user_knowledge_progress"
    __table_args__ = (
        UniqueConstraint("user_id", "card_id", name="uq_user_card_progress"),
    )

    progress_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
    )
    pack_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_packs.pack_id"), nullable=False
    )
    card_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_cards.card_id"), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reward_event_id: Mapped[str | None] = mapped_column(
        ForeignKey("heart_reward_events.event_id"), nullable=True
    )


class MemoryCardAuditEvent(Base):
    __tablename__ = "memory_card_audit_events"

    event_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    memory_card_id: Mapped[str] = mapped_column(
        ForeignKey("memory_cards.card_id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
    )
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    old_value: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    new_value: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


# ---------------------------------------------------------------------------
# WebSocket Notifications (Phase 08)
# ---------------------------------------------------------------------------

class UserNotificationPreference(Base):
    """User notification settings (opt-in/out by event type)"""

    __tablename__ = "user_notification_preferences"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True
    )
    letter_replied: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    letter_reported: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    memory_card_review: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    reward_earned: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    persona_unlocked: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    knowledge_completed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class UserNotification(Base):
    """Notification history (retained for 30 days or user-configured retention)"""

    __tablename__ = "user_notifications"
    __table_args__ = (
        CheckConstraint(
            "notification_type IN ('letter.replied','letter.reported','memory.review',"
            "'reward.earned','persona.unlocked','knowledge.completed','system')",
            name="chk_notification_type",
        ),
    )

    notification_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
    )
    notification_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    data_json: Mapped[dict[str, Any]] = mapped_column(
        "data", JSON, default=dict, nullable=False
    )
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    action_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
