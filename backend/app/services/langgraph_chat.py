"""
LangGraph: Analyst → Friend for non-SOS turns. SOS is handled outside (rule-based finalizer).
BACKEND_PLAN §3.3, MVP_CANVAS.
"""

from __future__ import annotations

import logging
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.core.config import get_settings
from app.services.safety_scoring import build_snapshot

logger = logging.getLogger(__name__)


class ChatGraphState(TypedDict, total=False):
    user_message: str
    recent_messages: list[dict[str, Any]]
    mood_today: dict[str, Any] | None
    distress_score: float
    routing_history: list[str]
    analyst_calls_this_turn: int
    crisis_route_finalized: bool
    analyst_instruction: str
    reply: str
    tone_cam_xuc: str
    goi_y_nhanh: list[str]
    the_dinh_kem: list[dict[str, Any]]


def analyst_node(state: ChatGraphState) -> dict[str, Any]:
    settings = get_settings()
    calls = int(state.get("analyst_calls_this_turn") or 0) + 1
    hist = list(state.get("routing_history") or [])
    hist.append("analyst")

    mood_note = ""
    m = state.get("mood_today")
    if m:
        mood_note = f"Mood hôm nay: {m.get('mood', '')} {m.get('emoji', '')}."

    ctx_lines = []
    for turn in (state.get("recent_messages") or [])[-8:]:
        ctx_lines.append(f"{turn.get('role', '')}: {turn.get('content', '')}")
    transcript = "\n".join(ctx_lines)

    instruction = (
        "Bạn là Analyst ẩn danh. Trả lời JSON một dòng với khóa: "
        '`clinical_note` (ngắn, tiếng Việt), `suggested_probe` (một câu gợi mở cho Friend hỏi thêm nếu cần). '
        "Không chẩn đoán. Không nhắc PII."
    )
    user_payload = f"{mood_note}\nLịch sử gần đây:\n{transcript}\nTin mới: {state.get('user_message', '')}"

    text_out = ""
    if settings.openai_api_key:
        try:
            from openai import OpenAI

            client = OpenAI(api_key=settings.openai_api_key, timeout=settings.llm_timeout_seconds)
            resp = client.chat.completions.create(
                model=settings.openai_model_analyst,
                temperature=0.0,
                messages=[
                    {"role": "system", "content": instruction},
                    {"role": "user", "content": user_payload},
                ],
            )
            text_out = (resp.choices[0].message.content or "").strip()
        except Exception as exc:
            logger.warning("analyst llm failed: %s", exc)
            text_out = '{"clinical_note": "", "suggested_probe": ""}'
    else:
        text_out = '{"clinical_note": "Người dùng đang chia sẻ căng thẳng.", "suggested_probe": "Bạn muốn kể thêm về điều đó không?"}'

    return {
        "analyst_calls_this_turn": calls,
        "routing_history": hist,
        "analyst_instruction": text_out[:2000],
    }


def friend_node(state: ChatGraphState) -> dict[str, Any]:
    settings = get_settings()
    hist = list(state.get("routing_history") or [])
    hist.append("friend")

    system = (
        "Bạn tên là Mây — bạn đồng hành Gen Z, ấm áp, không phán xét, tránh toxic positivity. "
        "Trả lời JSON với các khóa: reply (tiếng Việt, ngắn gọn), tone_cam_xuc (một trong: ho_tro, xac_nhan, vui_tuoi, lam_diu), "
        "goi_y_nhanh (mảng 3 chuỗi gợi ý), the_dinh_kem (mảng object {type, id, title}). "
        "Lồng gợi ý từ analyst nếu phù hợp: "
        + (state.get("analyst_instruction") or "")
    )
    user_text = state.get("user_message", "")

    payload: dict[str, Any] = {
        "reply": "Mình nghe cậu. Cảm ơn cậu đã chia sẻ — mình ở đây cùng cậu nhé.",
        "tone_cam_xuc": "xac_nhan",
        "goi_y_nhanh": ["Kể thêm đi cậu", "Mình nên làm gì bây giờ?", "Chỉ cần lắng nghe thôi"],
        "the_dinh_kem": [{"type": "breathing_exercise", "id": "breath_478", "title": "Thở 4-7-8 — Giảm căng thẳng"}],
    }

    if settings.openai_api_key:
        try:
            import json
            import re

            from openai import OpenAI

            client = OpenAI(api_key=settings.openai_api_key, timeout=settings.llm_timeout_seconds)
            resp = client.chat.completions.create(
                model=settings.openai_model_friend,
                temperature=0.7,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_text},
                ],
            )
            raw = (resp.choices[0].message.content or "").strip()
            m = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
            if m:
                raw = m.group(1).strip()
            parsed = json.loads(raw)
            payload.update(parsed)
        except Exception as exc:
            logger.warning("friend llm failed: %s", exc)

    return {
        "routing_history": hist,
        "reply": str(payload.get("reply") or ""),
        "tone_cam_xuc": str(payload.get("tone_cam_xuc") or "xac_nhan"),
        "goi_y_nhanh": list(payload.get("goi_y_nhanh") or []),
        "the_dinh_kem": list(payload.get("the_dinh_kem") or []),
    }


def build_chat_graph():
    g = StateGraph(ChatGraphState)
    g.add_node("analyst", analyst_node)
    g.add_node("friend", friend_node)
    g.add_edge(START, "analyst")
    g.add_edge("analyst", "friend")
    g.add_edge("friend", END)
    return g.compile()


_COMPILED = None


def get_chat_graph():
    global _COMPILED
    if _COMPILED is None:
        _COMPILED = build_chat_graph()
    return _COMPILED


def run_non_sos_turn(
    *,
    user_message: str,
    recent_messages: list[dict[str, Any]],
    mood_today: dict[str, Any] | None,
    distress_score: float,
) -> dict[str, Any]:
    """Run Analyst→Friend. Caller builds API `data` envelope with safety ladder."""
    settings = get_settings()
    snap = build_snapshot(
        distress_score,
        sos_triggered=False,
        voice_hint=settings.distress_voice_hint,
        critical=settings.distress_critical,
    )
    graph = get_chat_graph()
    out = graph.invoke(
        {
            "user_message": user_message,
            "recent_messages": recent_messages,
            "mood_today": mood_today,
            "distress_score": distress_score,
            "crisis_route_finalized": False,
            "analyst_calls_this_turn": 0,
            "routing_history": [],
        }
    )
    return {
        "session_fields": snap,
        "reply": out.get("reply", ""),
        "tone_cam_xuc": out.get("tone_cam_xuc", "xac_nhan"),
        "goi_y_nhanh": out.get("goi_y_nhanh", []),
        "the_dinh_kem": out.get("the_dinh_kem", []),
        "routing_history": out.get("routing_history", []),
    }


def build_normal_envelope(
    session_id: str,
    *,
    snap,
    reply: str,
    tone_cam_xuc: str,
    goi_y_nhanh: list[str],
    the_dinh_kem: list[dict[str, Any]],
    voice_hint: str | None = None,
) -> dict[str, Any]:
    return {
        "session_id": session_id,
        "conversation_mode": snap.conversation_mode,
        "distress_score": snap.distress_score,
        "safety_tier": snap.safety_tier,
        "voice_session_offered": snap.safety_tier == "voice_recommended",
        "suggest_voice": snap.safety_tier == "voice_recommended",
        "voice_hint": voice_hint,
        "emergency_actions": None,
        "reply": reply,
        "tone_cam_xuc": tone_cam_xuc,
        "goi_y_nhanh": goi_y_nhanh,
        "the_dinh_kem": the_dinh_kem,
        "sos_triggered": False,
    }
