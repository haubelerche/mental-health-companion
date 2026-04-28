"""Hierarchical multi-agent blueprint for VinMec clinical expansion.

Current production path remains in langgraph_chat.py.
This module provides a structured graph scaffold to progressively migrate to:
- ScreeningTeam
- PsychoEducationTeam
- OperationsTeam
"""

from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph


class HierarchicalState(TypedDict, total=False):
    user_message: str
    route: str
    screening_payload: dict[str, Any]
    psychoeducation_payload: dict[str, Any]
    operations_payload: dict[str, Any]
    final_reply: str


def supervisor_route(state: HierarchicalState) -> dict[str, Any]:
    text = str(state.get("user_message") or "").lower()
    if any(k in text for k in ("đặt lịch", "appointment", "khoa", "bệnh viện")):
        return {"route": "operations"}
    if any(k in text for k in ("cbt", "kỹ thuật", "bài tập", "coping")):
        return {"route": "psychoeducation"}
    return {"route": "screening"}


def screening_team(state: HierarchicalState) -> dict[str, Any]:
    return {
        "screening_payload": {
            "risk_band": "low",
            "suggested_assessment": "phq9_quick",
        },
        "final_reply": "Mình ghi nhận cảm xúc hiện tại của bạn và đề xuất kiểm tra nhanh PHQ-9 để đánh giá rõ hơn.",
    }


def psychoeducation_team(state: HierarchicalState) -> dict[str, Any]:
    return {
        "psychoeducation_payload": {"module": "cbt_grounding"},
        "final_reply": "Mình gợi ý bài CBT grounding ngắn để bạn ổn định cảm xúc trong 5 phút tới.",
    }


def operations_team(state: HierarchicalState) -> dict[str, Any]:
    return {
        "operations_payload": {"channel": "vinmec_referral"},
        "final_reply": "Mình có thể hỗ trợ bạn kết nối tuyến dịch vụ VinMec phù hợp ngay lúc này.",
    }


def route_after_supervisor(state: HierarchicalState) -> str:
    route = str(state.get("route") or "screening")
    if route not in {"screening", "psychoeducation", "operations"}:
        return "screening"
    return route


def build_hierarchical_graph():
    graph = StateGraph(HierarchicalState)
    graph.add_node("supervisor", supervisor_route)
    graph.add_node("screening", screening_team)
    graph.add_node("psychoeducation", psychoeducation_team)
    graph.add_node("operations", operations_team)
    graph.add_edge(START, "supervisor")
    graph.add_conditional_edges(
        "supervisor",
        route_after_supervisor,
        {
            "screening": "screening",
            "psychoeducation": "psychoeducation",
            "operations": "operations",
        },
    )
    graph.add_edge("screening", END)
    graph.add_edge("psychoeducation", END)
    graph.add_edge("operations", END)
    return graph.compile()
