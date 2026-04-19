from app.services.langgraph_chat import get_chat_graph


def test_supervisor_skips_analyst_on_light_greeting():
    graph = get_chat_graph()
    out = graph.invoke(
        {
            "user_message": "chao may",
            "recent_messages": [],
            "mood_today": None,
            "distress_score": 0.1,
            "crisis_route_finalized": False,
            "analyst_calls_this_turn": 0,
            "routing_history": [],
        }
    )
    assert out["routing_history"][0] == "supervisor"
    assert "analyst" not in out["routing_history"]
    assert "friend" in out["routing_history"]
    assert out["reply"]


def test_supervisor_routes_analyst_when_distress_high():
    graph = get_chat_graph()
    out = graph.invoke(
        {
            "user_message": "Minh dang rat ap luc va khong on",
            "recent_messages": [],
            "mood_today": {"mood": "stressed", "emoji": ":("},
            "distress_score": 0.7,
            "crisis_route_finalized": False,
            "analyst_calls_this_turn": 0,
            "routing_history": [],
        }
    )
    assert out["routing_history"][0] == "supervisor"
    assert "analyst" in out["routing_history"]
    assert out["analyst_calls_this_turn"] == 1


def test_supervisor_respects_analyst_cap():
    graph = get_chat_graph()
    out = graph.invoke(
        {
            "user_message": "Minh thay khong on",
            "recent_messages": [],
            "mood_today": {"mood": "stressed"},
            "distress_score": 0.9,
            "crisis_route_finalized": False,
            "analyst_calls_this_turn": 2,
            "routing_history": [],
        }
    )
    assert "analyst" not in out["routing_history"]
    assert out["supervisor_reason"] == "analyst_cap_reached"
