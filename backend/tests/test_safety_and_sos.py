from app.services.safety_scoring import build_snapshot, compute_escalation_signal, distress_to_risk_level
from app.services.sos_handler import decide_sos


def test_distress_to_risk_level_boundaries():
    assert distress_to_risk_level(0.0) == 0
    assert distress_to_risk_level(0.34) == 1
    assert distress_to_risk_level(0.50) == 3
    assert distress_to_risk_level(1.0) == 5


def test_build_snapshot_forces_critical_when_sos():
    snap = build_snapshot(0.2, sos_triggered=True, voice_hint=0.8, critical=0.9)
    assert snap.safety_tier == "critical"
    assert snap.conversation_mode == "de_escalation"
    assert snap.risk_level >= 4


def test_decide_sos_true_for_explicit_keyword():
    sos, distress = decide_sos("Toi muon tu tu")
    assert sos is True
    assert distress >= 0.94


def test_decide_sos_false_for_regular_message():
    sos, distress = decide_sos("Hom nay minh thay hoi met vi hoc nhieu")
    assert sos is False
    assert 0.0 <= distress <= 1.0


def test_escalation_signal_threshold_crossed():
    signal = compute_escalation_signal(
        current_distress=0.92,
        previous_distress=[0.45, 0.52, 0.6],
        threshold=0.9,
        delta_threshold=0.3,
        window_turns=6,
    )
    assert signal.escalate is True
    assert signal.trigger_reason == "threshold_crossed"


def test_escalation_signal_rapid_delta():
    signal = compute_escalation_signal(
        current_distress=0.78,
        previous_distress=[0.4, 0.44, 0.46],
        threshold=0.9,
        delta_threshold=0.3,
        window_turns=6,
    )
    assert signal.escalate is True
    assert signal.trigger_reason == "rapid_escalation"
