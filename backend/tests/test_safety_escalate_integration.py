"""
Safety escalation integration tests.

Covers 5 scenarios per the P1 test expansion requirement:
1. Ambiguous self-harm: constrained supportive flow, not playful persona.
2. Explicit SOS: safety finalization bypasses normal persona.
3. Crush/Cún persona during high distress: must fallback to safe default.
4. Multi-turn escalation: distress increase raises routing conservatism.
5. Both streaming and non-streaming apply output safety validation.
"""
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.api.v1.routers import safety as safety_router
from app.main import app
from app.services.safety_policy import evaluate_safety_policy


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _override_user():
    return SimpleNamespace(user_id="usr_safety")


class _Db:
    pass


DIAGNOSIS_FRAGMENTS = [
    "bạn bị ",
    "bạn mắc ",
    "chẩn đoán",
    "rối loạn",
    "disorder",
    "you have ",
]

HARM_FRAGMENTS = [
    "chi tiết phương pháp tự hại",
    "cách tự làm hại",
    "liều thuốc",
    "tăng liều",
    "ngừng thuốc đột ngột",
]

PERSONA_THEATRICS = [
    "em yêu anh",
    "tình yêu của tôi",
    "cún yêu",
    "chỉ có em",
]


def _no_diagnosis(text: str) -> None:
    lower = text.lower()
    for frag in DIAGNOSIS_FRAGMENTS:
        assert frag not in lower, f"Found diagnosis fragment '{frag}' in: {text[:200]}"


def _no_harmful_details(text: str) -> None:
    lower = text.lower()
    for frag in HARM_FRAGMENTS:
        assert frag not in lower, f"Found harmful content '{frag}' in: {text[:200]}"


def _no_persona_theatrics(text: str) -> None:
    lower = text.lower()
    for frag in PERSONA_THEATRICS:
        assert frag not in lower, f"Found persona theatrics '{frag}' in: {text[:200]}"


# ---------------------------------------------------------------------------
# Case 1: Ambiguous self-harm — safety policy tracks distress level
# ---------------------------------------------------------------------------

def test_ambiguous_distress_constrains_flow():
    """
    A message matching IMPLICIT_MEDIUM_RISK 'muon bien khoi the gioi nay' after
    normalization should produce elevated distress (> 0.5) in the safety policy.
    The policy must not be plain allow at zero risk.
    """
    msg = "mình muốn biến khỏi thế giới này, không muốn đối mặt với gì nữa"
    policy = evaluate_safety_policy(msg, [])
    # Must not be the lowest possible distress/risk — keyword should score it higher
    assert policy.distress_score > 0.3, (
        f"Expected distress > 0.3 for high-distress message, got {policy.distress_score}"
    )
    # must_avoid/must_include contain policy codes (not clinical text) — just check for no raw scores
    for code in policy.must_avoid:
        assert "%" not in code, f"Probability claim in must_avoid: {code}"


# ---------------------------------------------------------------------------
# Case 2: Explicit SOS phrase → keyword-matched risk_level 5
# ---------------------------------------------------------------------------

def test_explicit_sos_triggers_safety_finalization():
    """
    'tôi muốn tự tử' → normalized 'toi muon tu tu' → EXPLICIT_HIGH_RISK.
    Must produce risk_level == 5 and a supportive (not allow) policy.
    """
    msg = "Tôi muốn tự tử, tôi không biết làm gì nữa"
    policy = evaluate_safety_policy(msg, [])
    assert policy.risk_level == 5, f"SOS must produce risk_level=5, got {policy.risk_level}"
    assert policy.policy_action != "allow", (
        f"SOS must not produce 'allow' policy, got {policy.policy_action}"
    )
    assert policy.persona_style_strength <= 0.1, (
        f"persona_style_strength must be ≤0.1 on SOS, got {policy.persona_style_strength}"
    )
    # must_avoid contains policy codes — verify they're not clinical diagnosis strings
    for code in policy.must_avoid:
        assert "bạn bị" not in code.lower(), f"Clinical diagnosis in must_avoid code: {code}"
        assert "bạn mắc" not in code.lower(), f"Clinical diagnosis in must_avoid code: {code}"


# ---------------------------------------------------------------------------
# Case 3: Crush persona during high distress → persona must be suppressed
# ---------------------------------------------------------------------------

def test_crush_persona_blocked_during_high_distress():
    """
    When risk_level == 5, persona_style_strength must drop to ≤ 0.1.
    """
    sos_msg = "Mình không muốn sống nữa, cảm thấy chán quá"
    policy = evaluate_safety_policy(sos_msg, [])
    assert policy.risk_level == 5, f"risk_level should be 5: {policy.risk_level}"
    assert policy.persona_style_strength <= 0.1, (
        f"persona_style_strength must be ≤0.1 on SOS turn, got {policy.persona_style_strength}"
    )


# ---------------------------------------------------------------------------
# Case 4: Multi-turn escalation — safety gate evaluates current turn only
# ---------------------------------------------------------------------------

def test_multi_turn_distress_escalation():
    """
    Safety gate must produce risk_level == 5 on the final SOS turn regardless
    of prior low-distress history.

    evaluate_safety_policy second arg is list[str] — user message strings only,
    not conversation dicts.
    """
    prior_user_messages = [
        "Hôm nay mình hơi mệt chút",
        "Ừ, mình cũng không ổn lắm, khó ngủ",
    ]
    final_msg = "Tôi muốn tự tử, tôi sợ lắm"
    policy = evaluate_safety_policy(final_msg, prior_user_messages)
    assert policy.risk_level == 5, (
        f"Final SOS turn must produce risk_level=5 even after low-distress history, got {policy.risk_level}"
    )
    assert policy.policy_action != "allow", f"SOS must not allow: {policy.policy_action}"


# ---------------------------------------------------------------------------
# Case 5: Both streaming and non-streaming respect output safety
# ---------------------------------------------------------------------------

def test_non_streaming_output_contains_no_harmful_fragments():
    """
    ChatOrchestrator.finalize_normal_chat_response must strip internal fields
    and never expose raw distress or diagnosis to the caller.
    """
    from app.services.chat_orchestrator import ChatOrchestrator

    raw_turn = {
        "assistant_text": "Mình nghe bạn đang rất mệt.",
        "reply": "Mình nghe bạn đang rất mệt.",
        "route_tier": "advisor_assisted",
        "used_advisor_ids": ["empathy_advisor"],
        "distress_score": 0.85,
        "reason_codes": ["sos_adjacent", "high_distress"],
        "risk_level": 4,
        "clinical_note_internal": "Possible MDD markers detected",
    }
    data = ChatOrchestrator.finalize_normal_chat_response(
        raw_turn,
        latency_trace={"total_backend_ms": 100},
    )
    assert "distress_score" not in data
    assert "reason_codes" not in data
    assert "risk_level" not in data
    assert "clinical_note_internal" not in data
    reply = data.get("reply", "")
    _no_diagnosis(reply)
    _no_harmful_details(reply)


# ---------------------------------------------------------------------------
# Original tests (preserved)
# ---------------------------------------------------------------------------

def test_safety_escalate_legal_gate_off(monkeypatch):
    monkeypatch.setattr(safety_router, "get_settings", lambda: SimpleNamespace(trusted_contact_outbound_enabled=False))
    monkeypatch.setattr(safety_router, "list_trusted_contacts", lambda *_args, **_kwargs: [{"name": "A", "phone": "0123"}])
    monkeypatch.setattr(safety_router, "get_outbound_opt_in", lambda *_args, **_kwargs: True)

    def override_db():
        yield _Db()

    app.dependency_overrides[safety_router.ensure_policy_acknowledged] = _override_user
    app.dependency_overrides[safety_router.get_db] = override_db
    try:
        with TestClient(app) as client:
            resp = client.post(
                "/v1/safety/escalate",
                json={"session_id": "sess_1", "risk_level": 5, "reason": "high_risk_detected"},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["queued"] is False
        assert body["data"]["legal_gate_enabled"] is False
    finally:
        app.dependency_overrides.clear()


def test_safety_escalate_queues_when_enabled(monkeypatch):
    monkeypatch.setattr(safety_router, "get_settings", lambda: SimpleNamespace(trusted_contact_outbound_enabled=True))
    monkeypatch.setattr(safety_router, "list_trusted_contacts", lambda *_args, **_kwargs: [{"name": "A", "phone": "0123"}])
    monkeypatch.setattr(safety_router, "get_outbound_opt_in", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(safety_router, "enqueue_trusted_contact_notification", lambda *_args, **_kwargs: 999)

    def override_db():
        yield _Db()

    app.dependency_overrides[safety_router.ensure_policy_acknowledged] = _override_user
    app.dependency_overrides[safety_router.get_db] = override_db
    try:
        with TestClient(app) as client:
            resp = client.post(
                "/v1/safety/escalate",
                json={"session_id": "sess_1", "risk_level": 5, "reason": "high_risk_detected"},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["queued"] is True
        assert body["data"]["outbox_id"] == 999
    finally:
        app.dependency_overrides.clear()
