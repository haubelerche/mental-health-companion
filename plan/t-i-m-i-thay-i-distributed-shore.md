# Database Verification & Schema Consistency Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Kiểm định kết nối Supabase thật sự hoạt động, dữ liệu được stream đúng, và ORM code thống nhất với schema `core_sql.sql` mới đã deploy.

**Architecture:** Backend dùng SQLAlchemy ORM + psycopg kết nối thẳng vào Supabase PostgreSQL qua `DATABASE_URL`. Schema Supabase dùng namespace `app.*` (ví dụ `app.users`). ORM hiện tại dùng table name không có schema prefix — phải đảm bảo `search_path` của DB hoặc config ORM đặt đúng `app` schema.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy 2.x (async/sync), psycopg, Alembic, Supabase PostgreSQL, pytest, SQLite (test)

---

## Findings từ Exploration

### Mismatches nghiêm trọng cần fix trước khi chạy production:

| Vấn đề | File | Severity |
|--------|------|----------|
| `messages.tone_cam_xuc` (ORM) ≠ `assistant_tone` (SQL) | models.py | 🔴 Critical |
| `crisis_logs.muc_do` (ORM) ≠ `severity_level` (SQL) | models.py | 🔴 Critical |
| 5 bảng analyst pipeline có trong SQL nhưng **không có ORM model** | models.py | 🔴 Critical |
| `mood_checkins` ORM thiếu cột `source` (SQL có CHECK constraint) | models.py | 🟡 High |
| `conversation_memories` ORM thiếu `pii_checked, expires_at, source` | models.py | 🟡 High |
| `user_profiles` ORM thiếu `schema_version, last_active_session_id, summary_count` | models.py | 🟡 High |
| `clinical_profiles` ORM thiếu `score_source, model_version` | models.py | 🟡 High |
| Dashboard `_fetch_hypothesis_insights()` dùng raw SQL cho bảng không có ORM model | dashboard/service.py | 🟡 High |
| Tất cả tests dùng SQLite — không test PostgreSQL thật | tests/ | 🟡 High |
| ORM có 21 bảng (Plan 03–08) không có trong core_sql.sql | models.py | 🟢 Medium |

### Files chính cần sửa:
- `backend/app/services/db/models.py` — ORM models (36 models hiện tại)
- `backend/app/services/db/session.py` — engine/session setup, schema config
- `backend/app/dashboard/service.py` — raw SQL cần chuyển sang ORM
- `backend/alembic/versions/` — migration mới (0012)
- `backend/tests/conftest.py` — thêm PostgreSQL fixture
- `backend/tests/test_db_integration.py` — file test mới cho real DB

---

## File Structure

```
backend/
├── app/
│   ├── services/db/
│   │   ├── models.py          # MODIFY: fix column names + add 5 missing models
│   │   └── session.py         # VERIFY: schema search_path setup
│   └── dashboard/
│       └── service.py         # MODIFY: replace raw SQL with ORM query
├── alembic/
│   └── versions/
│       └── 0012_sync_core_schema.py  # CREATE: migration sync
├── tests/
│   ├── conftest.py            # MODIFY: add real-db fixture
│   └── test_db_integration.py # CREATE: PostgreSQL connectivity tests
└── scripts/
    └── verify_db_schema.py    # CREATE: standalone schema verification script
```

---

## Task 1: Viết script kiểm tra kết nối Supabase

**Files:**
- Create: `backend/scripts/verify_db_schema.py`

- [ ] **Step 1: Tạo script verify_db_schema.py**

```python
"""
Chạy: DATABASE_URL=<supabase_url> python backend/scripts/verify_db_schema.py
Kiểm tra: kết nối, schema app tồn tại, các bảng core có đúng không.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import sqlalchemy as sa
from app.core.config import get_settings

REQUIRED_TABLES = [
    "users", "refresh_tokens", "conversations", "messages",
    "mood_checkins", "resources", "bookmarks", "play_events",
    "conversation_memories", "session_summaries_archive",
    "user_profiles", "user_profile_snapshots",
    "clinical_profiles", "risk_inference_log", "session_risk_snapshots",
    "crisis_logs", "analyst_signals", "insight_hypotheses",
    "sync_outbox", "admin_audit_log",
]

def main():
    settings = get_settings()
    db_url = settings.normalized_database_url()
    if "sqlite" in db_url:
        print("❌ DATABASE_URL chưa set — đang dùng SQLite local, không phải Supabase")
        sys.exit(1)

    engine = sa.create_engine(db_url, connect_args={"connect_timeout": 10})
    try:
        with engine.connect() as conn:
            conn.execute(sa.text("SET search_path TO app, public, extensions"))
            print(f"✅ Kết nối thành công: {db_url[:50]}...")

            result = conn.execute(sa.text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'app' ORDER BY table_name"
            ))
            existing = {row[0] for row in result}
            print(f"\n📋 Bảng tồn tại trong schema app ({len(existing)}):")
            for t in sorted(existing):
                marker = "✅" if t in REQUIRED_TABLES else "🆕"
                print(f"  {marker} {t}")

            missing = set(REQUIRED_TABLES) - existing
            if missing:
                print(f"\n❌ Bảng THIẾU trong Supabase ({len(missing)}):")
                for t in sorted(missing):
                    print(f"  ✗ {t}")
                sys.exit(1)
            else:
                print("\n✅ Tất cả required tables tồn tại!")

            # Kiểm tra columns của messages
            cols = conn.execute(sa.text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema='app' AND table_name='messages' ORDER BY column_name"
            ))
            msg_cols = {r[0] for r in cols}
            print(f"\n📋 messages columns: {sorted(msg_cols)}")
            if "assistant_tone" not in msg_cols:
                print("  ❌ assistant_tone THIẾU trong messages!")
            if "tone_cam_xuc" in msg_cols:
                print("  ⚠️  tone_cam_xuc vẫn tồn tại — cần đổi tên")

    except Exception as e:
        print(f"❌ Kết nối thất bại: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Chạy script với DATABASE_URL thật**

```bash
cd backend
DATABASE_URL="<supabase_postgresql_url>" python scripts/verify_db_schema.py
```

Expected output:
```
✅ Kết nối thành công: postgresql://...
📋 Bảng tồn tại trong schema app (20):
  ✅ admin_audit_log
  ✅ analyst_signals
  ...
✅ Tất cả required tables tồn tại!
📋 messages columns: ['assistant_tone', 'content', 'created_at', ...]
```

- [ ] **Step 3: Commit**

```bash
git add backend/scripts/verify_db_schema.py
git commit -m "feat(db): add Supabase schema verification script"
```

---

## Task 2: Fix ORM column name mismatches (Critical)

**Files:**
- Modify: `backend/app/services/db/models.py`

- [ ] **Step 1: Đọc models.py để xác nhận vị trí chính xác**

Tìm các cột cần sửa:
```bash
grep -n "tone_cam_xuc\|muc_do\|severity_level\|assistant_tone" backend/app/services/db/models.py
```

- [ ] **Step 2: Fix messages model — đổi tone_cam_xuc → assistant_tone**

Trong class `Message` (tablename: "messages"), tìm:
```python
tone_cam_xuc: Mapped[Optional[str]] = mapped_column(String(20))
```

Sửa thành:
```python
assistant_tone: Mapped[Optional[str]] = mapped_column(
    String(20),
    CheckConstraint(
        "assistant_tone IN ('supportive','validating','cheerful','calming','mentor','neutral')",
        name="ck_messages_assistant_tone",
    ),
)
```

- [ ] **Step 3: Fix crisis_logs model — đổi muc_do → severity_level**

Trong class `CrisisLog` (tablename: "crisis_logs"), tìm:
```python
muc_do: Mapped[str] = mapped_column(String(20))
```

Sửa thành:
```python
severity_level: Mapped[str] = mapped_column(
    String(20),
    CheckConstraint(
        "severity_level IN ('low','moderate','high','imminent','unknown')",
        name="ck_crisis_logs_severity_level",
    ),
)
```

- [ ] **Step 4: Tìm và fix tất cả references đến tone_cam_xuc và muc_do trong codebase**

```bash
grep -rn "tone_cam_xuc\|muc_do" backend/app/ --include="*.py"
```

Với mỗi file tìm thấy, đổi:
- `tone_cam_xuc` → `assistant_tone`
- `muc_do` → `severity_level`

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/db/models.py
git add backend/app/  # any router/service files updated
git commit -m "fix(db): rename ORM columns to match SQL schema (tone_cam_xuc→assistant_tone, muc_do→severity_level)"
```

---

## Task 3: Fix missing columns trong existing ORM models

**Files:**
- Modify: `backend/app/services/db/models.py`

- [ ] **Step 1: Thêm missing columns vào MoodCheckin**

Trong class `MoodCheckin`, thêm sau `triggers`:
```python
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
```

- [ ] **Step 2: Thêm missing columns vào ConversationMemory**

Trong class `ConversationMemory`, thêm sau `confidence`:
```python
pii_checked: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
expires_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
source: Mapped[str] = mapped_column(
    String(20),
    CheckConstraint(
        "source IN ('chat_turn','session_summary','checkin','manual','system')",
        name="ck_conv_memories_source",
    ),
    default="chat_turn",
    server_default="chat_turn",
    nullable=False,
)
```

- [ ] **Step 3: Thêm missing columns vào UserProfile**

Trong class `UserProfile`, thêm:
```python
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
```

- [ ] **Step 4: Thêm missing columns vào ClinicalProfile**

Trong class `ClinicalProfile`, thêm:
```python
score_source: Mapped[Optional[str]] = mapped_column(
    String(30),
    CheckConstraint(
        "score_source IN ('self_report','questionnaire','analyst_inference','clinician_review','system')",
        name="ck_clinical_profiles_score_source",
    ),
    nullable=True,
)
model_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
```

- [ ] **Step 5: Verify models.py syntax không bị lỗi**

```bash
cd backend && python -c "from app.services.db.models import *; print('OK')"
```

Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/db/models.py
git commit -m "fix(db): add missing columns to ORM models (source, pii_checked, schema_version, score_source, etc.)"
```

---

## Task 4: Thêm 5 ORM models cho bảng Analyst Pipeline

**Files:**
- Modify: `backend/app/services/db/models.py`

- [ ] **Step 1: Thêm SessionSummaryArchive model**

Thêm vào cuối phần Memory models trong models.py:
```python
class SessionSummaryArchive(Base):
    __tablename__ = "session_summaries_archive"

    archive_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    session_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("conversations.session_id", ondelete="SET NULL"), nullable=True
    )
    summary: Mapped[dict] = mapped_column(JSONB, nullable=False)
    session_started_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    dominant_emotion: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    sos_triggered: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    archived_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=func.now(), server_default=func.now(), nullable=False
    )
```

- [ ] **Step 2: Thêm RiskInferenceLog model**

```python
class RiskInferenceLog(Base):
    __tablename__ = "risk_inference_log"

    log_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    session_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("conversations.session_id", ondelete="SET NULL"), nullable=True
    )
    inferred_signal: Mapped[str] = mapped_column(String, nullable=False)
    model_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    score: Mapped[Optional[float]] = mapped_column(
        Float,
        CheckConstraint("score IS NULL OR (score >= 0 AND score <= 1)", name="ck_risk_log_score"),
        nullable=True,
    )
    detail: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=func.now(), server_default=func.now(), nullable=False
    )
```

- [ ] **Step 3: Thêm SessionRiskSnapshot model**

```python
class SessionRiskSnapshot(Base):
    __tablename__ = "session_risk_snapshots"

    snapshot_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        String, ForeignKey("conversations.session_id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
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
    escalation_flag: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    components: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}", nullable=False)
    source: Mapped[str] = mapped_column(
        String(20),
        CheckConstraint(
            "source IN ('supervisor','sos_override','batch_recalc','system','safety_agent')",
            name="ck_session_risk_source",
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=func.now(), server_default=func.now(), nullable=False
    )
```

- [ ] **Step 4: Thêm AnalystSignal model**

```python
class AnalystSignal(Base):
    __tablename__ = "analyst_signals"

    signal_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    session_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("conversations.session_id", ondelete="SET NULL"), nullable=True
    )
    message_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("messages.message_id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=func.now(), server_default=func.now(), nullable=False
    )
    emotional_theme: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    suggested_focus: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    clinical_note_internal: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    risk_indicators: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]", nullable=False)
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
    graph_context_used: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
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
    display_allowed: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
```

- [ ] **Step 5: Thêm InsightHypothesis model**

```python
class InsightHypothesis(Base):
    __tablename__ = "insight_hypotheses"

    insight_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=func.now(), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=func.now(), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    hypothesis_type: Mapped[str] = mapped_column(
        String(40),
        CheckConstraint(
            "hypothesis_type IN ('stress_pattern','sleep_disruption','social_withdrawal',"
            "'low_mood_trend','anxiety_like_worry_loop','coping_success','engagement_pattern','other')",
            name="ck_insight_hyp_type",
        ),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    user_safe_summary: Mapped[str] = mapped_column(Text, nullable=False)
    internal_rationale: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}", nullable=False)
    evidence_window_start: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    evidence_window_end: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
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
            "severity_band IS NULL OR severity_band IN ('low','moderate','elevated')",
            name="ck_insight_hyp_severity",
        ),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        CheckConstraint(
            "status IN ('active','dismissed','expired','superseded')",
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
```

- [ ] **Step 6: Export các model mới trong module**

Đảm bảo `backend/app/services/db/__init__.py` (hoặc models.py cuối file) export:
```python
# Nếu có __all__, thêm vào:
__all__ = [
    # ... existing ...
    "SessionSummaryArchive",
    "RiskInferenceLog",
    "SessionRiskSnapshot",
    "AnalystSignal",
    "InsightHypothesis",
]
```

- [ ] **Step 7: Verify import OK**

```bash
cd backend && python -c "from app.services.db.models import InsightHypothesis, AnalystSignal, SessionRiskSnapshot, RiskInferenceLog, SessionSummaryArchive; print('OK')"
```

Expected: `OK`

- [ ] **Step 8: Commit**

```bash
git add backend/app/services/db/models.py
git commit -m "feat(db): add ORM models for analyst pipeline tables (InsightHypothesis, AnalystSignal, SessionRiskSnapshot, RiskInferenceLog, SessionSummaryArchive)"
```

---

## Task 5: Fix dashboard service — thay raw SQL bằng ORM

**Files:**
- Modify: `backend/app/dashboard/service.py`

- [ ] **Step 1: Tìm hàm _fetch_hypothesis_insights trong service.py**

```bash
grep -n "_fetch_hypothesis_insights\|text(\|FROM insight_hypotheses" backend/app/dashboard/service.py
```

- [ ] **Step 2: Thay raw SQL bằng ORM query**

Tìm hàm `_fetch_hypothesis_insights` (khoảng line 144-157), sửa thành:

```python
async def _fetch_hypothesis_insights(
    db: Session, user_id: str
) -> list[dict]:
    """Fetch active, display-allowed insights for dashboard."""
    from app.services.db.models import InsightHypothesis

    stmt = (
        select(
            InsightHypothesis.insight_id,
            InsightHypothesis.title,
            InsightHypothesis.user_safe_summary,
            InsightHypothesis.evidence_count,
            InsightHypothesis.confidence,
            InsightHypothesis.severity_band,
            InsightHypothesis.evidence_window_start,
            InsightHypothesis.evidence_window_end,
            InsightHypothesis.updated_at,
            InsightHypothesis.hypothesis_type,
        )
        .where(
            InsightHypothesis.user_id == user_id,
            InsightHypothesis.status == "active",
            InsightHypothesis.display_allowed.is_(True),
        )
        .order_by(InsightHypothesis.updated_at.desc())
        .limit(10)
    )
    rows = db.execute(stmt).mappings().all()
    return [dict(r) for r in rows]
```

- [ ] **Step 3: Xóa import `text` nếu không còn dùng ở chỗ nào khác**

```bash
grep -n "^from sqlalchemy import\|^import sqlalchemy" backend/app/dashboard/service.py
```

Nếu `text` không còn dùng, remove khỏi import line.

- [ ] **Step 4: Verify service.py syntax**

```bash
cd backend && python -c "from app.dashboard.service import build_reflect_summary; print('OK')"
```

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add backend/app/dashboard/service.py
git commit -m "fix(dashboard): replace raw SQL with ORM query using InsightHypothesis model"
```

---

## Task 6: Verify schema search_path cho ORM

**Files:**
- Read & potentially modify: `backend/app/services/db/session.py`

- [ ] **Step 1: Kiểm tra session.py có set search_path không**

```bash
grep -n "search_path\|connect_args\|options\|execution_options" backend/app/services/db/session.py
```

- [ ] **Step 2: Nếu chưa có search_path, thêm vào engine options**

Trong hàm `get_engine()`, tìm đoạn tạo engine PostgreSQL và thêm:

```python
# Với PostgreSQL/Supabase — đảm bảo ORM tìm bảng trong app schema
connect_args = {}
if "postgresql" in url or "postgres" in url:
    connect_args["options"] = "-csearch_path=app,public,extensions"

engine = create_engine(
    url,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_timeout=settings.db_pool_timeout_seconds,
    pool_recycle=settings.db_pool_recycle_seconds,
    pool_pre_ping=settings.db_pool_pre_ping,
    connect_args=connect_args,
)
```

- [ ] **Step 3: Verify engine tạo không lỗi**

```bash
cd backend && python -c "from app.services.db.session import get_engine; print('engine OK')"
```

Expected: `engine OK`

- [ ] **Step 4: Commit nếu có thay đổi**

```bash
git add backend/app/services/db/session.py
git commit -m "fix(db): set search_path=app,public,extensions for Supabase PostgreSQL connections"
```

---

## Task 7: Tạo Alembic migration 0012 để sync schema

**Files:**
- Create: `backend/alembic/versions/0012_sync_core_schema.py`

- [ ] **Step 1: Tạo migration file**

```bash
cd backend && alembic revision --rev-id 0012 --message "sync_core_schema"
```

- [ ] **Step 2: Viết nội dung migration**

Mở file vừa tạo `backend/alembic/versions/0012_sync_core_schema.py` và điền:

```python
"""sync_core_schema

Revision ID: 0012
Revises: 0011
Create Date: 2026-05-07
"""
from alembic import op
import sqlalchemy as sa

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Fix messages: rename tone_cam_xuc → assistant_tone
    with op.batch_alter_table("messages") as batch_op:
        batch_op.alter_column("tone_cam_xuc", new_column_name="assistant_tone")

    # Fix crisis_logs: rename muc_do → severity_level
    with op.batch_alter_table("crisis_logs") as batch_op:
        batch_op.alter_column("muc_do", new_column_name="severity_level")

    # Add missing columns to mood_checkins
    op.add_column("mood_checkins", sa.Column(
        "source", sa.String(20), nullable=False, server_default="self_report"
    ))

    # Add missing columns to conversation_memories
    op.add_column("conversation_memories", sa.Column(
        "pii_checked", sa.Boolean, nullable=False, server_default="false"
    ))
    op.add_column("conversation_memories", sa.Column(
        "expires_at", sa.TIMESTAMP(timezone=True), nullable=True
    ))
    op.add_column("conversation_memories", sa.Column(
        "source", sa.String(20), nullable=False, server_default="chat_turn"
    ))

    # Add missing columns to user_profiles
    op.add_column("user_profiles", sa.Column(
        "schema_version", sa.String(10), nullable=False, server_default="v1"
    ))
    op.add_column("user_profiles", sa.Column(
        "last_active_session_id", sa.String, nullable=True
    ))
    op.add_column("user_profiles", sa.Column(
        "summary_count", sa.Integer, nullable=False, server_default="0"
    ))

    # Add missing columns to clinical_profiles
    op.add_column("clinical_profiles", sa.Column(
        "score_source", sa.String(30), nullable=True
    ))
    op.add_column("clinical_profiles", sa.Column(
        "model_version", sa.String(50), nullable=True
    ))


def downgrade() -> None:
    # Reverse column additions
    op.drop_column("clinical_profiles", "model_version")
    op.drop_column("clinical_profiles", "score_source")
    op.drop_column("user_profiles", "summary_count")
    op.drop_column("user_profiles", "last_active_session_id")
    op.drop_column("user_profiles", "schema_version")
    op.drop_column("conversation_memories", "source")
    op.drop_column("conversation_memories", "expires_at")
    op.drop_column("conversation_memories", "pii_checked")
    op.drop_column("mood_checkins", "source")

    with op.batch_alter_table("crisis_logs") as batch_op:
        batch_op.alter_column("severity_level", new_column_name="muc_do")

    with op.batch_alter_table("messages") as batch_op:
        batch_op.alter_column("assistant_tone", new_column_name="tone_cam_xuc")
```

> **Lưu ý:** Migration này chạy với Alembic (Python ORM layer). Nếu Supabase đã được reset bằng `core_sql.sql` (đã có `assistant_tone` và `severity_level`), thì migration sẽ fail vì cột đã đúng tên. Trong trường hợp đó, upgrade() cần check conditional. Xem Step 3.

- [ ] **Step 3: Kiểm tra trạng thái DB trước khi chạy migration**

```bash
DATABASE_URL="<supabase_url>" python backend/scripts/verify_db_schema.py
```

Nếu Supabase đã có `assistant_tone` (core_sql.sql đã chạy), sửa migration upgrade() để bỏ rename:

```python
def upgrade() -> None:
    # Supabase đã có correct column names từ core_sql.sql
    # Chỉ add missing columns
    # (Bỏ alter_column nếu columns đã đúng tên)
    ...
```

- [ ] **Step 4: Run migration (staging/dev first)**

```bash
cd backend
DATABASE_URL="<dev_supabase_url>" alembic upgrade head
```

Expected:
```
INFO  [alembic.runtime.migration] Running upgrade 0011 -> 0012, sync_core_schema
```

- [ ] **Step 5: Commit**

```bash
git add backend/alembic/versions/0012_sync_core_schema.py
git commit -m "feat(db): migration 0012 - sync ORM column names and add missing fields"
```

---

## Task 8: Tạo integration tests với real PostgreSQL

**Files:**
- Modify: `backend/tests/conftest.py`
- Create: `backend/tests/test_db_integration.py`

- [ ] **Step 1: Thêm real-db fixture vào conftest.py**

Thêm vào cuối `backend/tests/conftest.py`:

```python
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

@pytest.fixture(scope="session")
def real_db_url():
    """Skip nếu DATABASE_URL không set hoặc là SQLite."""
    import os
    url = os.environ.get("DATABASE_URL", "")
    if not url or "sqlite" in url:
        pytest.skip("DATABASE_URL không set — bỏ qua real-db integration tests")
    return url


@pytest.fixture(scope="session")
def real_engine(real_db_url):
    engine = create_engine(
        real_db_url,
        connect_args={"options": "-csearch_path=app,public,extensions", "connect_timeout": 15},
    )
    yield engine
    engine.dispose()


@pytest.fixture
def real_db(real_engine):
    Session = sessionmaker(bind=real_engine)
    session = Session()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
```

- [ ] **Step 2: Tạo test_db_integration.py**

```python
"""
Integration tests với real Supabase DB.
Chạy: DATABASE_URL=<supabase_url> pytest backend/tests/test_db_integration.py -v

Skip tự động nếu DATABASE_URL không set.
"""
import pytest
from sqlalchemy import text, select

from app.services.db.models import (
    User, Conversation, Message, MoodCheckin,
    InsightHypothesis, AnalystSignal,
    SessionRiskSnapshot, RiskInferenceLog,
)


class TestSchemaConnectivity:
    def test_connection_alive(self, real_db):
        result = real_db.execute(text("SELECT 1"))
        assert result.scalar() == 1

    def test_search_path_is_app(self, real_db):
        result = real_db.execute(text("SHOW search_path"))
        path = result.scalar()
        assert "app" in path, f"search_path không có 'app': {path}"

    def test_core_tables_exist(self, real_db):
        required = [
            "users", "conversations", "messages", "mood_checkins",
            "conversation_memories", "session_summaries_archive",
            "analyst_signals", "insight_hypotheses",
            "crisis_logs", "session_risk_snapshots", "risk_inference_log",
            "sync_outbox", "admin_audit_log",
        ]
        result = real_db.execute(text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'app' ORDER BY table_name"
        ))
        existing = {row[0] for row in result}
        missing = set(required) - existing
        assert not missing, f"Bảng thiếu: {missing}"


class TestColumnConsistency:
    def test_messages_has_assistant_tone(self, real_db):
        result = real_db.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema='app' AND table_name='messages' AND column_name='assistant_tone'"
        ))
        assert result.fetchone() is not None, "messages.assistant_tone KHÔNG tồn tại"

    def test_messages_no_old_vietnamese_column(self, real_db):
        result = real_db.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema='app' AND table_name='messages' AND column_name='tone_cam_xuc'"
        ))
        assert result.fetchone() is None, "messages.tone_cam_xuc vẫn còn — chưa đổi tên"

    def test_crisis_logs_has_severity_level(self, real_db):
        result = real_db.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema='app' AND table_name='crisis_logs' AND column_name='severity_level'"
        ))
        assert result.fetchone() is not None, "crisis_logs.severity_level KHÔNG tồn tại"

    def test_mood_checkins_has_source(self, real_db):
        result = real_db.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema='app' AND table_name='mood_checkins' AND column_name='source'"
        ))
        assert result.fetchone() is not None, "mood_checkins.source KHÔNG tồn tại"

    def test_insight_hypotheses_columns(self, real_db):
        required_cols = {
            "insight_id", "user_id", "hypothesis_type", "title",
            "user_safe_summary", "status", "display_allowed", "confidence",
            "severity_band", "evidence_count", "created_at", "updated_at",
        }
        result = real_db.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema='app' AND table_name='insight_hypotheses'"
        ))
        existing = {row[0] for row in result}
        missing = required_cols - existing
        assert not missing, f"insight_hypotheses thiếu cột: {missing}"


class TestOrmReadWrite:
    def test_orm_can_query_users(self, real_db):
        """ORM select trên app.users không raise exception."""
        stmt = select(User).limit(1)
        real_db.execute(stmt)  # không raise = OK

    def test_orm_can_query_insight_hypotheses(self, real_db):
        """ORM select trên InsightHypothesis hoạt động."""
        stmt = (
            select(InsightHypothesis)
            .where(InsightHypothesis.status == "active")
            .limit(5)
        )
        rows = real_db.execute(stmt).scalars().all()
        # Không cần có data — chỉ cần query không raise
        assert isinstance(rows, list)

    def test_orm_can_query_analyst_signals(self, real_db):
        stmt = select(AnalystSignal).limit(1)
        real_db.execute(stmt)  # không raise = OK

    def test_orm_can_query_session_risk_snapshots(self, real_db):
        stmt = select(SessionRiskSnapshot).limit(1)
        real_db.execute(stmt)  # không raise = OK


class TestStreamingDataFlow:
    def test_checkin_write_and_read(self, real_db):
        """Test tạo mood_checkin → đọc lại — xác nhận data được lưu."""
        import uuid
        from datetime import date

        # Cần có user trong DB trước — lấy user đầu tiên
        user = real_db.execute(select(User).limit(1)).scalar_one_or_none()
        if user is None:
            pytest.skip("Không có user trong DB — cần seed data trước")

        test_date = date(2026, 1, 1)  # date trong quá khứ để không conflict
        # Xóa nếu đã tồn tại
        existing = real_db.execute(
            select(MoodCheckin).where(
                MoodCheckin.user_id == user.user_id,
                MoodCheckin.logged_date == test_date,
                MoodCheckin.time_bucket == "test_bucket",
            )
        ).scalar_one_or_none()
        if existing:
            real_db.delete(existing)
            real_db.flush()

        checkin = MoodCheckin(
            user_id=user.user_id,
            mood="okay",
            emotions=[],
            triggers=[],
            logged_date=test_date,
            time_bucket="test_bucket",
            source="self_report",
        )
        real_db.add(checkin)
        real_db.flush()

        fetched = real_db.execute(
            select(MoodCheckin).where(MoodCheckin.checkin_id == checkin.checkin_id)
        ).scalar_one()
        assert fetched.mood == "okay"
        assert fetched.source == "self_report"

        # Rollback để không dirty DB
        real_db.rollback()
```

- [ ] **Step 3: Chạy integration tests**

```bash
cd backend
DATABASE_URL="<supabase_url>" pytest tests/test_db_integration.py -v --tb=short
```

Expected:
```
tests/test_db_integration.py::TestSchemaConnectivity::test_connection_alive PASSED
tests/test_db_integration.py::TestSchemaConnectivity::test_search_path_is_app PASSED
tests/test_db_integration.py::TestSchemaConnectivity::test_core_tables_exist PASSED
tests/test_db_integration.py::TestColumnConsistency::test_messages_has_assistant_tone PASSED
...
```

- [ ] **Step 4: Commit**

```bash
git add backend/tests/conftest.py backend/tests/test_db_integration.py
git commit -m "test(db): add real PostgreSQL integration tests for Supabase schema verification"
```

---

## Task 9: Chạy full verification

- [ ] **Step 1: Run backend unit tests (SQLite) để không bị regression**

```bash
cd backend && pytest tests/ -q --ignore=tests/test_db_integration.py --ignore=tests/test_db.py
```

Expected: Tất cả tests pass (hoặc cùng số fail như trước — không tăng).

- [ ] **Step 2: Run integration tests với Supabase**

```bash
DATABASE_URL="<supabase_url>" pytest backend/tests/test_db_integration.py -v
```

Expected: Tất cả pass.

- [ ] **Step 3: Chạy verify script lần cuối**

```bash
DATABASE_URL="<supabase_url>" python backend/scripts/verify_db_schema.py
```

Expected:
```
✅ Kết nối thành công
✅ Tất cả required tables tồn tại!
✅ messages.assistant_tone tồn tại
```

- [ ] **Step 4: Update CHANGELOG.md**

Thêm entry:
```markdown
## [Unreleased] - 2026-05-07

### Fixed
- ORM column names synced with Supabase SQL schema (tone_cam_xuc→assistant_tone, muc_do→severity_level)
- Added missing ORM models: InsightHypothesis, AnalystSignal, SessionRiskSnapshot, RiskInferenceLog, SessionSummaryArchive
- Added missing columns to MoodCheckin, ConversationMemory, UserProfile, ClinicalProfile ORM models
- Fixed dashboard service to use ORM instead of raw SQL for insight_hypotheses
- Set search_path=app,public,extensions for Supabase PostgreSQL connections
- Added Supabase schema verification script (scripts/verify_db_schema.py)

### Added
- Alembic migration 0012: sync core schema column names and add missing fields
- Integration tests for real PostgreSQL/Supabase connectivity (test_db_integration.py)
```

- [ ] **Step 5: Final commit**

```bash
git add CHANGELOG.md
git commit -m "docs: update CHANGELOG for db schema sync and integration tests"
```

---

## Self-Review

### Spec coverage check:

| Yêu cầu | Covered? | Task |
|---------|----------|------|
| Kiểm tra kết nối Supabase thật | ✅ | Task 1, 8 |
| Dữ liệu có stream thật không | ✅ | Task 8 (TestStreamingDataFlow) |
| Logic DB thống nhất với code | ✅ | Task 2-6 |
| Column name mismatches | ✅ | Task 2, 7 |
| Missing ORM models | ✅ | Task 4 |
| Missing columns in ORM | ✅ | Task 3 |
| Dashboard raw SQL → ORM | ✅ | Task 5 |
| search_path cho app schema | ✅ | Task 6 |
| Migration để apply thay đổi | ✅ | Task 7 |

### Placeholder scan: Không có TBD, TODO, hoặc "similar to Task N".

### Type consistency: InsightHypothesis model (Task 4) → dashboard service (Task 5) → integration test (Task 8) dùng cùng class name và attribute names.

---

## Execution Handoff

Plan complete. Two execution options:

**1. Subagent-Driven (recommended)** — Fresh subagent mỗi task, review giữa tasks

**2. Inline Execution** — Chạy trong session này với executing-plans skill

**Lưu ý quan trọng trước khi chạy:**
- Cần có `DATABASE_URL` cho Supabase trong `.env` hoặc shell
- Task 7 (migration) cần chạy cẩn thận — verify DB state trước
- Task 2 cần check xem Supabase đã có `assistant_tone` chưa (nếu `core_sql.sql` đã chạy rồi thì rename là không cần thiết)
