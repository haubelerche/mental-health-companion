from app.services.langgraph_chat import distress_router


def _make_state(distress: float, msg: str = "minh cam thay met moi lam") -> dict:
    return {
        "distress_score": distress,
        "user_message": msg,
        "routing_history": [],
        "crisis_route_finalized": False,
        "correlation_id": "test",
        "active_persona_id": "dung_luong",
    }


def test_distress_below_82_routes_to_friend():
    """distress 0.72-0.81 should route to friend (not analyst) after threshold raise."""
    state = _make_state(distress=0.78)
    result = distress_router(state)
    assert result["route_decision"] == "friend", (
        f"Expected friend at distress=0.78, got {result['route_decision']}"
    )


def test_distress_above_82_routes_to_analyst():
    state = _make_state(distress=0.85)
    result = distress_router(state)
    assert result["route_decision"] == "analyst"


def test_distress_at_threshold_routes_to_analyst():
    state = _make_state(distress=0.82)
    result = distress_router(state)
    assert result["route_decision"] == "analyst"


def test_distress_just_below_threshold_routes_to_friend():
    state = _make_state(distress=0.819)
    result = distress_router(state)
    assert result["route_decision"] == "friend"
