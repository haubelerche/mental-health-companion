import json
from pathlib import Path

from app.services.langgraph_chat import supervisor_node
from app.services.safety_scoring import compute_escalation_signal
from app.services.sos_handler import decide_sos


def _load_cases():
    path = Path(__file__).resolve().parent / "golden" / "ai_routing_safety_cases.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_ai_golden_cases():
    cases = _load_cases()
    for case in cases:
        kind = case["kind"]
        if kind == "sos":
            sos, _distress = decide_sos(case["message"])
            assert sos is bool(case["expected_sos"]), case["id"]
        elif kind == "supervisor":
            state = dict(case["state"])
            state["routing_history"] = []
            out = supervisor_node(state)
            assert out["supervisor_route"] == case["expected_route"], case["id"]
        elif kind == "escalation":
            signal = compute_escalation_signal(
                current_distress=float(case["current_distress"]),
                previous_distress=list(case["previous_distress"]),
                threshold=float(case["threshold"]),
                delta_threshold=float(case["delta_threshold"]),
                window_turns=int(case["window_turns"]),
            )
            assert signal.escalate is bool(case["expected_escalate"]), case["id"]
