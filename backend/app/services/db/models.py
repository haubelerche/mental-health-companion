from __future__ import annotations
import os

from datetime import date, datetime
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import (
    BIGINT,
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Identity,
    Integer,
    String,
    TIMESTAMP,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON as SAJSON

from app.services.db.session import Base

try:
    from pgvector.sqlalchemy import Vector
except ImportError:  # pragma: no cover
    Vector = None

try:
    from sqlalchemy.dialects.postgresql import INET as PG_INET
    from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
    from sqlalchemy.dialects.postgresql import JSONB as PG_JSONB
except ImportError:  # pragma: no cover
    PG_INET = None
    PG_ARRAY = None
    PG_JSONB = None

JSONB_COMPAT = SAJSON()
if PG_JSONB is not None:  # pragma: no branch
    JSONB_COMPAT = JSONB_COMPAT.with_variant(PG_JSONB(astext_type=Text()), "postgresql")

TEXT_ARRAY_COMPAT = SAJSON()
if PG_ARRAY is not None:  # pragma: no branch
    TEXT_ARRAY_COMPAT = TEXT_ARRAY_COMPAT.with_variant(PG_ARRAY(Text()), "postgresql")

INET_COMPAT = String(45)
if PG_INET is not None:  # pragma: no branch
    INET_COMPAT = INET_COMPAT.with_variant(PG_INET(), "postgresql")

TIMESTAMP_COMPAT = DateTime


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


class UserIdentity(Base):
    __tablename__ = "user_identities"
    __table_args__ = (
        UniqueConstraint("provider", "provider_user_id", name="uq_user_identity_provider_uid"),
        UniqueConstraint("user_id", "provider", name="uq_user_identity_user_provider"),
    )

    identity_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    provider_user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_picture_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    provider_email_verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    token_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    ip_address: Mapped[str | None] = mapped_column(INET_COMPAT)
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
        CheckConstraint("length(content) <= 2000", name="chk_content_length"),
    )

    message_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("conversations.session_id"), nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    assistant_tone: Mapped[str | None] = mapped_column(
        String(20),
        CheckConstraint(
            "assistant_tone IN ('supportive','validating','cheerful','calming','mentor','neutral')",
            name="ck_messages_assistant_tone",
        ),
    )
    sos_triggered: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class MoodCheckin(Base):
    __tablename__ = "mood_checkins"
    __table_args__ = (
        UniqueConstraint("user_id", "logged_date", "time_bucket", name="uq_mood_checkin_bucket"),
    )

    checkin_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"), nullable=False)
    mood: Mapped[str] = mapped_column(String(50), nullable=False)
    emoji: Mapped[str | None] = mapped_column(String(10))
    emotions: Mapped[list[Any] | None] = mapped_column(JSON)
    triggers: Mapped[list[Any] | None] = mapped_column(JSON)
    source: Mapped[str] = mapped_column(
        String(20),
        CheckConstraint(
            "source IN ('self_report','imported','system')",
            name="ck_mood_checkins_source",
        ),
        default="self_report",
        server_default="self_report",
        nullable=False,
    )
    note: Mapped[str | None] = mapped_column(Text)
    logged_date: Mapped[date] = mapped_column(Date, nullable=False)
    logged_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime)
    time_bucket: Mapped[str] = mapped_column(String(20), nullable=False, default="other", server_default="other")


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
    dass21_depression_score: Mapped[int | None] = mapped_column(Integer)
    dass21_anxiety_score: Mapped[int | None] = mapped_column(Integer)
    dass21_stress_score: Mapped[int | None] = mapped_column(Integer)
    mdq_score: Mapped[int | None] = mapped_column(Integer)
    pcl5_score: Mapped[int | None] = mapped_column(Integer)
    dass21_coverage: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    mdq_coverage: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    pcl5_coverage: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    crisis_level: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    score_source: Mapped[Optional[str]] = mapped_column(
        String(30),
        CheckConstraint(
            "score_source IN ('self_report','questionnaire','analyst_inference','clinician_review','system')",
            name="ck_clinical_profiles_score_source",
        ),
        nullable=True,
    )
    model_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    last_scored_at: Mapped[datetime | None] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class ScreeningAnswer(Base):
    """Raw questionnaire answers — backend-only; never exposed to frontend."""

    __tablename__ = "screening_answers"
    __table_args__ = (
        CheckConstraint(
            "instrument_id IN ('phq9','gad7','dass21','mdq','pcl5')",
            name="ck_screening_answers_instrument",
        ),
        {"schema": "app"},
    )

    answer_id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
    )
    instrument_id: Mapped[str] = mapped_column(String(10), nullable=False)
    screening_type: Mapped[str] = mapped_column(String(10), nullable=False)
    question_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    question_key: Mapped[str | None] = mapped_column(String(32), nullable=True)
    answer_value: Mapped[int | None] = mapped_column(Integer, nullable=True)
    answer_label: Mapped[str | None] = mapped_column(String(120), nullable=True)
    question_text_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    answer_options_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    session_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    locale: Mapped[str] = mapped_column(String(16), nullable=False, default="vi-VN", server_default="vi-VN")
    raw_score: Mapped[int] = mapped_column(Integer, nullable=False)
    answers: Mapped[dict[str, Any]] = mapped_column(JSONB_COMPAT, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=func.now(), server_default=func.now(), nullable=False
    )


class CrisisLog(Base):
    __tablename__ = "crisis_logs"

    log_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("conversations.session_id"), nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"), nullable=False)
    severity_level: Mapped[str] = mapped_column(
        String(20),
        CheckConstraint(
            "severity_level IN ('low','moderate','high','imminent','unknown')",
            name="ck_crisis_logs_severity_level",
        ),
        nullable=False,
    )
    context_summary: Mapped[str | None] = mapped_column(Text)
    reviewed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    triggered_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime)
    reviewed_by: Mapped[str | None] = mapped_column(String(50))


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


class SessionSummaryArchive(Base):
    __tablename__ = "session_summaries_archive"

    archive_id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
    )
    session_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("conversations.session_id", ondelete="SET NULL"), nullable=True
    )
    summary: Mapped[dict[str, Any]] = mapped_column(JSONB_COMPAT, nullable=False)
    session_started_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP_COMPAT, nullable=True
    )
    dominant_emotion: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    sos_triggered: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    archived_at: Mapped[datetime] = mapped_column(
        TIMESTAMP_COMPAT, default=func.now(), server_default=func.now(), nullable=False
    )


class CanonicalMemoryCard(Base):
    __tablename__ = "memory_cards"
    __table_args__ = (
        CheckConstraint(
            "memory_type IN ("
            "'background','support_style','current_stressor','coping_history',"
            "'preference','persona_preference','nutrition_pattern','temporary_context',"
            "'event_memory','support_insight','relationship_context','goal_or_hope','emotional_pattern'"
            ")",
            name="chk_memory_type",
        ),
        CheckConstraint(
            "status IN ("
            "'pending_user_review','active','edited_by_user','deleted_by_user',"
            "'rejected_by_guardrail','merged_duplicate','deleted_by_system'"
            ")",
            name="chk_memory_status",
        ),
        CheckConstraint(
            "safety_review_status IN ('pending','approved','rejected')",
            name="chk_safety_review_status",
        ),
    )

    card_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    source_session_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    memory_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    canonical_key: Mapped[str | None] = mapped_column(String(120), nullable=True)
    normalized_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    mention_count: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    first_mentioned_at: Mapped[datetime | None] = mapped_column(TIMESTAMP_COMPAT, nullable=True)
    last_mentioned_at: Mapped[datetime | None] = mapped_column(TIMESTAMP_COMPAT, nullable=True)
    evidence_message_ids: Mapped[list[Any]] = mapped_column(JSONB_COMPAT, default=list, server_default="[]", nullable=False)
    display_category: Mapped[str | None] = mapped_column(String(80), nullable=True)
    subject: Mapped[str | None] = mapped_column(String(120), nullable=True)
    predicate: Mapped[str | None] = mapped_column(String(160), nullable=True)
    is_temporary: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="pending_user_review", server_default="pending_user_review", nullable=False)
    safety_review_status: Mapped[str] = mapped_column(String(30), default="pending", server_default="pending", nullable=False)
    personalization_disabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(TIMESTAMP_COMPAT, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB_COMPAT, default=dict, server_default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP_COMPAT, default=func.now(), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP_COMPAT, default=func.now(), server_default=func.now(), onupdate=func.now(), nullable=False)


class CanonicalMemoryCardAuditEvent(Base):
    __tablename__ = "memory_card_audit_events"

    event_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    memory_card_id: Mapped[str] = mapped_column(ForeignKey("memory_cards.card_id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    old_value: Mapped[dict[str, Any] | None] = mapped_column(JSONB_COMPAT, nullable=True)
    new_value: Mapped[dict[str, Any] | None] = mapped_column(JSONB_COMPAT, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP_COMPAT, default=func.now(), server_default=func.now(), nullable=False)


MemoryCard = CanonicalMemoryCard
MemoryCardAuditEvent = CanonicalMemoryCardAuditEvent


class SessionRiskSnapshot(Base):
    __tablename__ = "session_risk_snapshots"

    snapshot_id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        String, ForeignKey("conversations.session_id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
    )
    risk_score: Mapped[float] = mapped_column(
        Float,
        CheckConstraint("risk_score >= 0 AND risk_score <= 1", name="ck_session_risk_score"),
        nullable=False,
    )
    intent_severity: Mapped[float] = mapped_column(
        Float,
        CheckConstraint("intent_severity >= 0 AND intent_severity <= 1", name="ck_session_risk_severity"),
        nullable=False,
    )
    intent_immediacy: Mapped[float] = mapped_column(
        Float,
        CheckConstraint("intent_immediacy >= 0 AND intent_immediacy <= 1", name="ck_session_risk_immediacy"),
        nullable=False,
    )
    crisis_mode: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    escalation_flag: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    components: Mapped[dict[str, Any]] = mapped_column(
        JSONB_COMPAT, default=dict, server_default="{}", nullable=False
    )
    source: Mapped[str] = mapped_column(
        String(20),
        CheckConstraint(
            "source IN ('supervisor','sos_override','batch_recalc','system','safety_agent')",
            name="ck_session_risk_source",
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP_COMPAT, default=func.now(), server_default=func.now(), nullable=False
    )


class AnalystRun(Base):
    __tablename__ = "analyst_runs"

    run_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    run_type: Mapped[str] = mapped_column(
        String(40),
        CheckConstraint(
            "run_type IN ('turn','daily','rolling_3d','weekly','on_demand_dashboard','post_screening')",
            name="ck_analyst_runs_type",
        ),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(40),
        CheckConstraint(
            "status IN ('queued','running','completed','failed','skipped_insufficient_data','blocked_by_safety')",
            name="ck_analyst_runs_status",
        ),
        nullable=False,
        default="queued",
        server_default="queued",
    )
    window_start: Mapped[datetime] = mapped_column(TIMESTAMP_COMPAT, nullable=False)
    window_end: Mapped[datetime] = mapped_column(TIMESTAMP_COMPAT, nullable=False)
    data_cutoff_at: Mapped[datetime] = mapped_column(TIMESTAMP_COMPAT, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    input_summary: Mapped[dict[str, Any]] = mapped_column(JSONB_COMPAT, default=dict, server_default="{}", nullable=False)
    source_counts: Mapped[dict[str, Any]] = mapped_column(JSONB_COMPAT, default=dict, server_default="{}", nullable=False)
    missing_sources: Mapped[list[Any]] = mapped_column(JSONB_COMPAT, default=list, server_default="[]", nullable=False)
    model_version: Mapped[str | None] = mapped_column(String, nullable=True)
    feature_version: Mapped[str] = mapped_column(String, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP_COMPAT, default=func.now(), server_default=func.now(), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP_COMPAT, nullable=True)


class AnalystFeatureSnapshot(Base):
    __tablename__ = "analyst_feature_snapshots"

    snapshot_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    run_id: Mapped[str | None] = mapped_column(ForeignKey("analyst_runs.run_id", ondelete="SET NULL"), nullable=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    window_start: Mapped[datetime] = mapped_column(TIMESTAMP_COMPAT, nullable=False)
    window_end: Mapped[datetime] = mapped_column(TIMESTAMP_COMPAT, nullable=False)
    data_cutoff_at: Mapped[datetime] = mapped_column(TIMESTAMP_COMPAT, nullable=False)
    window_type: Mapped[str] = mapped_column(String(40), nullable=False)
    feature_version: Mapped[str] = mapped_column(String, nullable=False)
    features: Mapped[dict[str, Any]] = mapped_column(JSONB_COMPAT, nullable=False)
    source_counts: Mapped[dict[str, Any]] = mapped_column(JSONB_COMPAT, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP_COMPAT, default=func.now(), server_default=func.now(), nullable=False)


class AnalystSignal(Base):
    __tablename__ = "analyst_signals"

    signal_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    run_id: Mapped[str | None] = mapped_column(ForeignKey("analyst_runs.run_id", ondelete="SET NULL"), nullable=True)
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
    )
    session_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("conversations.session_id", ondelete="SET NULL"), nullable=True
    )
    message_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("messages.message_id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP_COMPAT, default=func.now(), server_default=func.now(), nullable=False
    )
    emotional_theme: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    suggested_focus: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    clinical_note_internal: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    risk_indicators: Mapped[list[Any]] = mapped_column(
        JSONB_COMPAT, default=list, server_default="[]", nullable=False
    )
    distress_score: Mapped[Optional[float]] = mapped_column(
        Float,
        CheckConstraint(
            "distress_score IS NULL OR (distress_score >= 0 AND distress_score <= 1)",
            name="ck_analyst_signals_distress",
        ),
        nullable=True,
    )
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    model_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    graph_context_used: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    source: Mapped[str] = mapped_column(
        String(30),
        CheckConstraint(
            "source IN ('analyst_node','batch_rollup','manual_review','system')",
            name="ck_analyst_signals_source",
        ),
        default="analyst_node",
        server_default="analyst_node",
        nullable=False,
    )
    display_allowed: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    raw_structured_output: Mapped[dict[str, Any]] = mapped_column(
        JSONB_COMPAT, default=dict, server_default="{}", nullable=False
    )


class InsightHypothesis(Base):
    __tablename__ = "insight_hypotheses"

    insight_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    run_id: Mapped[str | None] = mapped_column(ForeignKey("analyst_runs.run_id", ondelete="SET NULL"), nullable=True)
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP_COMPAT, default=func.now(), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP_COMPAT, default=func.now(), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    hypothesis_type: Mapped[str] = mapped_column(
        String(40),
        CheckConstraint(
            "hypothesis_type IN ('stress_pattern','sleep_disruption','social_withdrawal',"
            "'low_mood_trend','anxiety_like_worry_loop','coping_success','engagement_pattern','other',"
            "'mood_trend','trigger_pattern','nutrition_mood_link','sleep_energy_link',"
            "'coping_preference','support_style_preference','reflection_pattern',"
            "'data_quality_notice','screening_context_notice')",
            name="ck_insight_hyp_type",
        ),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    user_safe_summary: Mapped[str] = mapped_column(Text, nullable=False)
    internal_rationale: Mapped[dict[str, Any]] = mapped_column(
        JSONB_COMPAT, default=dict, server_default="{}", nullable=False
    )
    evidence_window_start: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP_COMPAT, nullable=True
    )
    evidence_window_end: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP_COMPAT, nullable=True
    )
    evidence_count: Mapped[int] = mapped_column(
        Integer,
        CheckConstraint("evidence_count >= 0", name="ck_insight_hyp_ev_count"),
        default=0,
        server_default="0",
        nullable=False,
    )
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    severity_band: Mapped[Optional[str]] = mapped_column(
        String(20),
        CheckConstraint(
            "severity_band IS NULL OR severity_band IN ('informational','low','moderate','medium','high')",
            name="ck_insight_hyp_severity",
        ),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        CheckConstraint(
            "status IN ('candidate','active','superseded','dismissed_by_user','expired','blocked_by_safety')",
            name="ck_insight_hyp_status",
        ),
        default="active",
        server_default="active",
        nullable=False,
    )
    display_allowed: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    source: Mapped[str] = mapped_column(
        String(30),
        CheckConstraint(
            "source IN ('analyst_pipeline','weekly_rollup','manual_review','system')",
            name="ck_insight_hyp_src",
        ),
        default="analyst_pipeline",
        server_default="analyst_pipeline",
        nullable=False,
    )


class InsightEvidence(Base):
    __tablename__ = "insight_evidence"

    evidence_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    insight_id: Mapped[str] = mapped_column(ForeignKey("insight_hypotheses.insight_id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    source_table: Mapped[str] = mapped_column(String, nullable=False)
    source_id: Mapped[str] = mapped_column(String, nullable=False)
    evidence_type: Mapped[str] = mapped_column(String, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(TIMESTAMP_COMPAT, nullable=False)
    user_safe_excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    numeric_value: Mapped[dict[str, Any] | None] = mapped_column(JSONB_COMPAT, nullable=True)
    weight: Mapped[float | None] = mapped_column(Float, nullable=True)
    sensitivity: Mapped[str] = mapped_column(
        String(20),
        CheckConstraint(
            "sensitivity IN ('low','medium','high','restricted')",
            name="ck_insight_evidence_sensitivity",
        ),
        default="medium",
        server_default="medium",
        nullable=False,
    )
    display_allowed: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP_COMPAT, default=func.now(), server_default=func.now(), nullable=False)


class AdminAuditLog(Base):
    __tablename__ = "admin_audit_log"
    if os.environ.get("SERENE_BACKEND_TESTING") == "1":
        __table_args__ = {}
    else:
        __table_args__ = {"schema": "app"}

    audit_id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    # admin_id is a virtual ID generated on-the-fly, not linked to app.users
    admin_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_accessed: Mapped[str | None] = mapped_column(String(255))
    ip_address: Mapped[str] = mapped_column(INET_COMPAT, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP_COMPAT, server_default=func.now(), nullable=False)


class UserProfile(Base):
    __tablename__ = "user_profiles"

    user_id: Mapped[str] = mapped_column(String(50), ForeignKey("users.user_id"), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    schema_version: Mapped[str] = mapped_column(String(10), default="v1", server_default="v1", nullable=False)
    last_active_session_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("conversations.session_id", ondelete="SET NULL"), nullable=True
    )
    summary_count: Mapped[int] = mapped_column(
        Integer,
        CheckConstraint("summary_count >= 0", name="ck_user_profiles_summary_count_gte0"),
        default=0,
        server_default="0",
        nullable=False,
    )
    profile: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class UserProfileSnapshot(Base):
    __tablename__ = "user_profile_snapshots"

    snapshot_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"), nullable=False)
    profile: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class OnboardingTourState(Base):
    __tablename__ = "onboarding_tour_states"
    __table_args__ = (
        CheckConstraint(
            "status IN ('not_started','available','in_progress','paused_for_safety','completed','skipped','dismissed')",
            name="ck_onboarding_tour_status",
        ),
    )

    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True)
    status: Mapped[str] = mapped_column(String(30), default="not_started", nullable=False)
    variant: Mapped[str] = mapped_column(String(50), default="first_run", nullable=False)
    current_step_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    completed_step_ids: Mapped[list[Any]] = mapped_column(JSONB_COMPAT, default=list, nullable=False)
    skipped_step_ids: Mapped[list[Any]] = mapped_column(JSONB_COMPAT, default=list, nullable=False)
    dismissed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP_COMPAT, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP_COMPAT, nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(TIMESTAMP_COMPAT, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB_COMPAT, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP_COMPAT, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP_COMPAT, server_default=func.now(), nullable=False)


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


class AdvisorCaseLibrary(Base):
    __tablename__ = "advisor_case_library"

    case_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    raw_case_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str] = mapped_column(Text, default="vi", nullable=False)
    user_context: Mapped[str] = mapped_column(Text, nullable=False)
    primary_problem: Mapped[str | None] = mapped_column(Text, nullable=True)
    topic_tags: Mapped[list[Any]] = mapped_column(TEXT_ARRAY_COMPAT, default=list, nullable=False)
    emotional_state_tags: Mapped[list[Any]] = mapped_column(TEXT_ARRAY_COMPAT, default=list, nullable=False)
    interaction_need: Mapped[str | None] = mapped_column(Text, nullable=True)
    cognitive_pattern_tags: Mapped[list[Any]] = mapped_column(TEXT_ARRAY_COMPAT, default=list, nullable=False)
    counseling_goal: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommended_approach: Mapped[str | None] = mapped_column(Text, nullable=True)
    intervention_steps: Mapped[list[Any]] = mapped_column(JSONB_COMPAT, default=list, nullable=False)
    reflection_questions: Mapped[list[Any]] = mapped_column(JSONB_COMPAT, default=list, nullable=False)
    do_say: Mapped[list[Any]] = mapped_column(JSONB_COMPAT, default=list, nullable=False)
    do_not_say: Mapped[list[Any]] = mapped_column(JSONB_COMPAT, default=list, nullable=False)
    risk_flags: Mapped[list[Any]] = mapped_column(TEXT_ARRAY_COMPAT, default=list, nullable=False)
    source_response_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    safety_review_status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str | None] = mapped_column(Text, nullable=True)
    advisor_domains: Mapped[list[Any]] = mapped_column(TEXT_ARRAY_COMPAT, default=list, nullable=False)
    safety_constraints: Mapped[dict[str, Any]] = mapped_column(JSONB_COMPAT, default=dict, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB_COMPAT, default=dict, nullable=False)
    reviewed_by: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP_COMPAT, nullable=True)
    if Vector is not None:
        embedding: Mapped[Any] = mapped_column(Vector(1536), nullable=True)
    else:
        embedding: Mapped[list[float] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP_COMPAT, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP_COMPAT, server_default=func.now(), nullable=False)


class AdvisorDomain(Base):
    __tablename__ = "advisor_domains"

    domain_id: Mapped[str] = mapped_column(Text, primary_key=True)
    runtime_advisor_id: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    max_cases_per_turn: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    latency_budget_ms: Mapped[int] = mapped_column(Integer, default=120, nullable=False)
    min_quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB_COMPAT, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP_COMPAT, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP_COMPAT, server_default=func.now(), nullable=False)


class AdvisorCaseDomainMap(Base):
    __tablename__ = "advisor_case_domain_map"

    case_id: Mapped[str] = mapped_column(ForeignKey("advisor_case_library.case_id", ondelete="CASCADE"), primary_key=True)
    domain_id: Mapped[str] = mapped_column(ForeignKey("advisor_domains.domain_id"), primary_key=True)
    runtime_advisor_id: Mapped[str] = mapped_column(Text, nullable=False)
    relevance_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP_COMPAT, server_default=func.now(), nullable=False)


class AdvisorDatasetImport(Base):
    __tablename__ = "advisor_dataset_imports"

    import_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    file_name: Mapped[str] = mapped_column(Text, nullable=False)
    domain_id: Mapped[str] = mapped_column(Text, nullable=False)
    runtime_advisor_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    row_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    imported_by: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB_COMPAT, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP_COMPAT, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP_COMPAT, server_default=func.now(), nullable=False)


class AdvisorDatasetStaging(Base):
    __tablename__ = "advisor_dataset_staging"

    staging_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    import_id: Mapped[str | None] = mapped_column(ForeignKey("advisor_dataset_imports.import_id", ondelete="CASCADE"), nullable=True)
    domain_id: Mapped[str] = mapped_column(Text, nullable=False)
    runtime_advisor_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSONB_COMPAT, nullable=False)
    normalized_question: Mapped[str | None] = mapped_column(Text, nullable=True)
    normalized_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    validation_status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP_COMPAT, server_default=func.now(), nullable=False)


class AdvisorConsultationEvent(Base):
    __tablename__ = "advisor_consultation_events"

    event_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    request_id: Mapped[str] = mapped_column(Text, nullable=False)
    session_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    advisor_ids: Mapped[list[Any]] = mapped_column(TEXT_ARRAY_COMPAT, default=list, nullable=False)
    advisor_domains: Mapped[list[Any]] = mapped_column(TEXT_ARRAY_COMPAT, default=list, nullable=False)
    query_text_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    interaction_need: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_level: Mapped[str | None] = mapped_column(Text, nullable=True)
    route_reason_codes: Mapped[list[Any]] = mapped_column(TEXT_ARRAY_COMPAT, default=list, nullable=False)
    retrieved_case_ids: Mapped[list[Any]] = mapped_column(TEXT_ARRAY_COMPAT, default=list, nullable=False)
    advisor_output_redacted: Mapped[dict[str, Any]] = mapped_column(JSONB_COMPAT, default=dict, nullable=False)
    used_by_friend: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    final_response_message_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt_included_case_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    approved_case_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    blocked_case_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    raw_response_in_prompt: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    model_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    retriever_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP_COMPAT, server_default=func.now(), nullable=False)


class SyncOutbox(Base):
    __tablename__ = "sync_outbox"

    outbox_id: Mapped[int] = mapped_column(
        BIGINT().with_variant(Integer, "sqlite"),
        Identity(),
        primary_key=True,
    )
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.user_id"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    processing_started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
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
    """
    Super Letter Model - Handles both personal therapeutic letters and social anonymous letters.
    Supports threading (replies), reactions, forwarding, and reporting in a single table.
    """

    __tablename__ = "therapy_letters"

    letter_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"), nullable=False)
    
    # Social/Interaction fields
    receiver_id: Mapped[str | None] = mapped_column(ForeignKey("users.user_id"), nullable=True)
    reply_to_id: Mapped[str | None] = mapped_column(ForeignKey("therapy_letters.letter_id"), nullable=True)
    
    # Content & Metadata
    letter_type: Mapped[str] = mapped_column(String(30), default="therapeutic", nullable=False) # 'therapeutic', 'public', 'reply'
    recipient_type: Mapped[str | None] = mapped_column(String(50), nullable=True) # For therapeutic: 'inner_child', 'future_self', etc.
    content: Mapped[str] = mapped_column(Text, nullable=False)
    anonymous_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    # Engagement fields
    forward_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reaction_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    
    # Safety & Status
    # status: lifecycle — 'pending_review' | 'active' | 'reported' | 'deleted'
    status: Mapped[str] = mapped_column(String(30), default="active", nullable=False)
    # review_status: guardrail result — 'not_reviewed' | 'passed' | 'failed' | 'escalated' | 'manual_review_required'
    review_status: Mapped[str] = mapped_column(String(40), default="not_reviewed", nullable=False)
    review_reason_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    report_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    content_masked: Mapped[str | None] = mapped_column(Text, nullable=True)
    safety_event_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Metrics
    word_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reward_event_id: Mapped[str | None] = mapped_column(ForeignKey("heart_reward_events.event_id"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class LetterReviewEvent(Base):
    """Immutable audit log for each guardrail run on a therapy letter."""

    __tablename__ = "letter_review_events"

    event_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    letter_id: Mapped[str] = mapped_column(ForeignKey("therapy_letters.letter_id"), nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"), nullable=False)
    validator_version: Mapped[str] = mapped_column(String(30), nullable=False)
    verdict: Mapped[str] = mapped_column(String(50), nullable=False)
    reason_codes: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    confidence: Mapped[float | None] = mapped_column(nullable=True)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


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
    reward_earned: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    persona_unlocked: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    knowledge_completed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class UserNotification(Base):
    """Notification history (retained for 30 days or user-configured retention)"""

    __tablename__ = "user_notifications"

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

# ---------------------------------------------------------------------------
# Admin Automation (Plan V2)
# ---------------------------------------------------------------------------

class AutomationTrigger(Base):
    __tablename__ = "automation_triggers"

    trigger_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    trigger_type: Mapped[str] = mapped_column(
        String(20),
        CheckConstraint("trigger_type IN ('fixed','custom')", name="ck_automation_trigger_type"),
        default="custom",
        nullable=False
    )
    action_key: Mapped[str] = mapped_column(
        String(50),
        CheckConstraint(
            "action_key IN ('batch_notification','ai_moderation','resource_crawler','custom_webhook','daily_reminder')",
            name="ck_automation_action_key"
        ),
        nullable=False
    )
    config: Mapped[dict[str, Any]] = mapped_column(JSONB_COMPAT, default=dict, nullable=False)
    
    # New schedule structure
    schedule_type: Mapped[str] = mapped_column(
        String(20),
        CheckConstraint("schedule_type IN ('daily', 'interval')", name="ck_automation_schedule_type"),
        default="daily",
        server_default="daily",
        nullable=False
    )
    schedule_value: Mapped[str] = mapped_column(String(100), nullable=False) # "07:00" or "60" (minutes)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

class AutomationLog(Base):
    __tablename__ = "automation_logs"
    __table_args__ = {"schema": "app"}

    log_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    target_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True) # worker_key or trigger_id
    action_key: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="success") # success, failure
    message: Mapped[str | None] = mapped_column(Text)
    details: Mapped[dict[str, Any]] = mapped_column(JSONB_COMPAT, default=dict)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP_COMPAT, server_default=func.now(), nullable=False)

class SystemInsight(Base):
    __tablename__ = "system_insights"

    insight_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    insight_type: Mapped[str] = mapped_column(String(50), nullable=False) # 'mood_trend', 'engagement', 'cost'
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
