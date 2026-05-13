"""Contract shape stability tests.

Verify that response shapes for persona registry, reward store, wallet,
TTS job, memory APIs, and Phase 1 runtime contracts remain stable.
"""

from __future__ import annotations

import asyncio
from urllib.parse import parse_qs, urlparse

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, event
from sqlalchemy.exc import TimeoutError as SQLAlchemyTimeoutError
from sqlalchemy.orm import Session

from app.rewards.catalog import CATALOG
from app.services.db.models import (  # noqa: F401
    HeartWallet,
    RewardStoreItem,
    User,
    UserInventoryItem,
)
from app.services.db.session import Base
from app.services.schemas.contracts import (
    AdvisorAdvice,
    AnalystBundle,
    ContextPack,
    FriendAgentOutput,
    SafetyPolicyDecision,
    WorkerJob,
)


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def set_pragma(conn, _):
        conn.execute("PRAGMA foreign_keys=ON")

    tables_for_sqlite = [t for t in Base.metadata.sorted_tables if not t.schema]
    Base.metadata.create_all(engine, tables=tables_for_sqlite)
    with Session(engine) as session:
        yield session
    Base.metadata.drop_all(engine, tables=tables_for_sqlite)


def _seed_user(db: Session, user_id: str = "usr_contract") -> None:
    db.add(User(
        user_id=user_id,
        display_name="Contract",
        email=f"{user_id}@test.com",
        password_hash="x",
        is_active=True,
    ))
    db.commit()


def test_registry_has_exactly_three_personas():
    from app.personas.registry import PERSONA_REGISTRY
    assert set(PERSONA_REGISTRY) == {"dung_luong", "dat_le", "hau_luong"}


def test_registry_persona_shape():
    from app.personas.registry import PERSONA_REGISTRY
    required_attrs = {"persona_id", "display_name", "tts_style_id", "max_distress"}
    for persona in PERSONA_REGISTRY.values():
        for attr in required_attrs:
            assert hasattr(persona, attr), f"{persona.persona_id} missing attribute {attr!r}"


def test_alias_mapping_keeps_backward_compatibility():
    from app.personas.aliases import resolve_alias
    from app.personas.registry import PERSONA_REGISTRY

    dung = PERSONA_REGISTRY["dung_luong"]
    assert dung.display_name == "Dũng"
    assert dung.user_facing_name == "Dũng"
    assert resolve_alias("dung_luong") == "dung_luong"
    assert resolve_alias("dung") == "dung_luong"
    assert resolve_alias("Dũng") == "dung_luong"
    assert resolve_alias("Dung Luong") == "dung_luong"
    assert resolve_alias("Dũng Lương") == "dung_luong"
    assert resolve_alias("ban_than") == "dung_luong"
    assert resolve_alias("default") == "dung_luong"
    assert resolve_alias("friend") == "dung_luong"
    assert resolve_alias("best_friend") == "dung_luong"
    assert resolve_alias("serene_default") == "dung_luong"
    assert resolve_alias("dat_le") == "dat_le"
    assert resolve_alias("dat") == "dat_le"
    assert resolve_alias("Đạt") == "dat_le"
    assert resolve_alias("Dat Le") == "dat_le"
    assert resolve_alias("nguoi_thay") == "dat_le"
    assert resolve_alias("cun") != "dung_luong"
    assert resolve_alias("cún") != "dung_luong"
    assert resolve_alias("meo") != "dung_luong"
    assert resolve_alias("mèo") != "dung_luong"
    assert resolve_alias("crush") != "dung_luong"
    assert resolve_alias("persona_crush") != "dung_luong"
    assert resolve_alias("nguoi_yeu") != "dung_luong"


def test_persona_chat_greetings_utf8_aligned_with_registry():
    """Regression: greetings must use correct Vietnamese + pronouns from PersonaConfig."""
    from app.personas.greetings import PERSONA_CHAT_GREETINGS, persona_chat_greeting_text
    from app.personas.registry import PERSONA_REGISTRY

    assert set(PERSONA_CHAT_GREETINGS) == set(PERSONA_REGISTRY)
    nt = PERSONA_CHAT_GREETINGS["dat_le"].lower()
    assert "di?u" not in PERSONA_CHAT_GREETINGS["dat_le"]
    assert "thầy" not in PERSONA_CHAT_GREETINGS["dat_le"].lower()
    assert " em " not in PERSONA_CHAT_GREETINGS["dat_le"]
    cfg = PERSONA_REGISTRY["dat_le"]
    assert cfg.pronoun_self.lower() in nt
    assert cfg.pronoun_user.lower() in nt

    bt = PERSONA_CHAT_GREETINGS["dung_luong"].lower()
    assert PERSONA_REGISTRY["dung_luong"].pronoun_self.lower() in bt
    assert PERSONA_REGISTRY["dung_luong"].pronoun_user.lower() in bt

    assert persona_chat_greeting_text("unknown_id") == PERSONA_CHAT_GREETINGS["dung_luong"]


def test_persona_router_decision_shape():
    from app.personas.router import route_persona

    decision = route_persona(
        current_persona_id="dung_luong",
        requested_persona_id=None,
        distress=0.0,
        sos_triggered=False,
        is_unlocked=True,
    )
    assert hasattr(decision, "target_persona_id")
    assert hasattr(decision, "action")
    assert hasattr(decision, "safety_override")


def test_dung_prompt_block_policy_guardrails():
    from app.personas.prompt_blocks import build_persona_block
    from app.personas.registry import get_persona

    block = build_persona_block(get_persona("dung_luong")).lower()
    assert "tớ" in block
    assert "cậu" in block
    assert "ask at most one question" in block
    assert "low-risk casual: humor" in block
    assert "safety rules override this block" in block
    assert "never diagnose" in block
    assert "never use cún/mèo/crush behavior" in block
    assert "mày/tao" in block


def test_dung_temperature_caps_by_distress():
    from app.services.langgraph_chat import _persona_temperature

    assert _persona_temperature("dung_luong", use_fast_model=False, distress_score=0.10) == 0.70
    assert _persona_temperature("dung_luong", use_fast_model=False, distress_score=0.50) == 0.50
    assert _persona_temperature("dung_luong", use_fast_model=False, distress_score=0.75) == 0.30


def test_dat_le_effective_temperature_low_risk_is_point_five():
    from app.services.langgraph_chat import _persona_temperature

    assert _persona_temperature("dat_le", use_fast_model=False, distress_score=0.10) == 0.50
    assert _persona_temperature("dat_le", use_fast_model=False, distress_score=0.10) == 0.50


def test_mem0_pgvector_collection_uses_search_path_not_schema_qualified_identifier():
    from app.services.mem0_service import _pgvector_config_from_database_url

    cfg = _pgvector_config_from_database_url("postgresql+psycopg://user:pass@localhost:5432/appdb")

    assert cfg["collection_name"] == "mem0_memories"
    assert "." not in cfg["collection_name"]
    query = parse_qs(urlparse(cfg["connection_string"]).query)
    assert query["options"] == ["-c search_path=app,extensions"]


def test_websocket_cookie_auth_fails_closed_when_db_pool_is_exhausted(monkeypatch):
    from app.api.v1.routers import ws

    class BrokenSession:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def scalar(self, *_args, **_kwargs):
            raise SQLAlchemyTimeoutError("pool exhausted")

    monkeypatch.setattr(ws, "decode_token", lambda _token: {"sub": "usr_timeout"})
    monkeypatch.setattr(ws, "get_session_factory", lambda: lambda: BrokenSession())

    user = asyncio.run(ws.get_current_user_ws_cookie(access_token="token"))

    assert user is None


def test_store_item_required_fields():
    required = {"item_id", "item_type", "title", "price_hearts", "tier"}
    for item in CATALOG:
        for key in required:
            assert key in item, f"Item {item.get('item_id')} missing field {key!r}"


def test_store_item_price_within_bounds():
    for item in CATALOG:
        assert 100 <= item["price_hearts"] <= 10_000


def test_store_item_tier_is_int():
    for item in CATALOG:
        assert isinstance(item["tier"], int), f"Item {item['item_id']} tier must be int"


def test_grant_hearts_response_shape(db):
    _seed_user(db)
    from app.hearts.service import grant_hearts

    result = grant_hearts(
        db,
        user_id="usr_contract",
        amount=10,
        event_type="test_contract",
        source_tab="test",
        idempotency_key="contract:shape:001",
    )
    assert "granted" in result
    assert "amount" in result
    assert "new_balance" in result
    assert "event_id" in result


def test_purchase_result_shape(db):
    from app.hearts.service import grant_hearts
    from app.rewards.purchase_service import purchase_item

    _seed_user(db)
    item = CATALOG[0]
    db.add(RewardStoreItem(
        item_id=item["item_id"],
        item_type=item["item_type"],
        title=item["title"],
        price_hearts=item["price_hearts"],
        tier=item["tier"],
        metadata_json=item.get("metadata", {}),
        requirements=item.get("requirements", {}),
    ))
    db.commit()

    grant_hearts(
        db,
        user_id="usr_contract",
        amount=item["price_hearts"] + 100,
        event_type="fund",
        source_tab="test",
        idempotency_key="fund:contract",
    )
    db.commit()

    result = purchase_item(db, user_id="usr_contract", item_id=item["item_id"])
    assert "inventory_id" in result
    assert "item_id" in result
    assert "idempotent" in result
    assert "new_balance" in result


def test_user_memory_out_schema_fields():
    from app.memory.routes import UserMemoryOut

    fields = UserMemoryOut.model_fields
    required = {"memory_id", "content", "source", "created_at", "metadata"}
    for field_name in required:
        assert field_name in fields, f"UserMemoryOut missing field {field_name!r}"


def test_tts_terminal_statuses_contain_required_values():
    from app.voice.types import TTS_REUSABLE_STATUSES, TTS_TERMINAL_STATUSES

    for status in ("ready", "failed", "skipped_duplicate", "cache_hit", "provider_disabled"):
        assert status in TTS_TERMINAL_STATUSES
    for status in ("ready", "cache_hit"):
        assert status in TTS_REUSABLE_STATUSES


def test_tts_queued_and_processing_are_not_terminal():
    from app.voice.types import TTS_TERMINAL_STATUSES

    assert "queued" not in TTS_TERMINAL_STATUSES
    assert "processing" not in TTS_TERMINAL_STATUSES


def test_safety_policy_decision_contract_shape():
    payload = SafetyPolicyDecision(
        policy_action="supportive_continuation",
        risk_level=2,
        distress_score=0.45,
        must_include=["short_validation"],
        must_avoid=["diagnosis_language"],
        persona_style_strength=0.6,
        ui_support_mode="optional_sheet",
        audit_required=False,
        reason_codes=["distress_disclosure"],
    )
    assert payload.policy_action == "supportive_continuation"
    assert payload.ui_support_mode == "optional_sheet"


def test_context_pack_contract_shape():
    pack = ContextPack(
        recent_messages=[{"role": "user", "content": "mÃ¬nh má»‡t"}],
        active_memory={"memory_id": "mem_1", "content": "deadline gáº§n Ä‘Ã¢y"},
        onboarding_summary={"primary_concern": "stress"},
        mood_context={"today": "stressful"},
        nutrition_context={"meal_slots_logged": ["breakfast"]},
        screening_summary={"phq9_score": 8},
        resource_candidates=[{"resource_id": "res_1"}],
        persona_context={"persona_id": "dung_luong"},
        safety_policy=SafetyPolicyDecision(
            policy_action="allow",
            risk_level=1,
            distress_score=0.2,
            persona_style_strength=1.0,
            ui_support_mode="none",
        ),
    )
    assert pack.safety_policy.policy_action == "allow"
    assert pack.active_memory is not None


def test_advisor_advice_rejects_final_text_field():
    with pytest.raises(ValidationError):
        AdvisorAdvice(
            advisor_id="cbt_pattern",
            confidence=0.8,
            evidence_refs=["msg:1"],
            advice_to_friend=["reflect pattern softly"],
            suggested_response_moves=["name the loop gently"],
            forbidden_moves=["diagnosis"],
            should_use=True,
            final_text="forbidden",
        )


def test_counseling_guidance_contract_rejects_final_text_field():
    from app.services.schemas.advisors import CounselingGuidance

    with pytest.raises(ValidationError):
        CounselingGuidance(
            case_understanding="understand",
            response_goal="help",
            final_text="forbidden",
        )


def test_friend_agent_output_contract_shape():
    payload = FriendAgentOutput(
        final_text="mÃ¬nh nghe Ä‘oáº¡n nÃ y Ä‘ang Ä‘Ã¨ lÃªn cáº­u khÃ¡ náº·ng.",
        response_intent="reflect",
        used_advisor_ids=["cbt_pattern"],
        used_resource_ids=["res_sleep_1"],
        suggested_next_action={"type": "continue"},
        memory_write_candidates=[{"kind": "preference", "value": "wants_short_replies"}],
        tts_candidate={"enabled": False},
        confidence=0.82,
    )
    assert payload.response_intent == "reflect"
    assert payload.used_advisor_ids == ["cbt_pattern"]


def test_analyst_bundle_contract_shape():
    payload = AnalystBundle(
        user_id="usr_1",
        time_window={"from": "2026-05-01T00:00:00Z", "to": "2026-05-10T00:00:00Z"},
        dominant_emotions=["stress", "sadness"],
        recurring_triggers=["deadline", "sleep_loss"],
        cognitive_patterns=[{"pattern": "self_blame"}],
        nutrition_patterns=[{"pattern": "skipped_breakfast"}],
        coping_preferences=["walk", "music"],
        evidence_refs=["sess_1", "sess_2"],
        confidence="medium",
        missing_info=["weekly_checkins"],
        safe_dashboard_candidates=[{"title": "tÃ­n hiá»‡u cÄƒng tháº³ng láº·p láº¡i"}],
    )
    assert payload.confidence == "medium"
    assert payload.time_window["from"] == "2026-05-01T00:00:00Z"


def test_worker_job_contract_shape():
    payload = WorkerJob(
        job_id="job_1",
        job_type="analyst_event",
        user_id="usr_1",
        session_id="sess_1",
        payload_ref="sync_outbox:123",
        idempotency_key="analyst:sess_1",
        status="queued",
        attempt_count=0,
    )
    assert payload.job_type == "analyst_event"
    assert payload.status == "queued"
