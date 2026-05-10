"""Backend-owned voice message policy for Serene chat and SOS turns."""

from __future__ import annotations

from dataclasses import dataclass

from app.services.voice_message_planner import build_voice_message_plan
from app.voice.types import VoiceIntent, VoicePolicyDecision


@dataclass(frozen=True)
class VoicePolicyContext:
    user_id: str
    session_id: str
    distress_score: float
    safety_tier: str = "normal"
    sos_triggered: bool = False
    cooldown_active: bool = False
    cooldown_seconds_remaining: int = 0
    user_voice_enabled: bool = True
    provider_enabled: bool = True
    current_turn_has_emotional_weight: bool = True
    purely_technical_turn: bool = False
    visible_text: str = ""
    reason_codes: tuple[str, ...] = ()


class VoiceMessagePolicyEngine:
    """Deterministic policy layer; frontend never computes risk or quota."""

    ELEVATED_MIN = 0.55
    ELEVATED_MAX = 0.70
    CASUAL_MAX = 0.54
    MIN_INTERVAL_SECONDS = 120

    @classmethod
    def decide(cls, context: VoicePolicyContext) -> VoicePolicyDecision:
        distress = float(context.distress_score or 0.0)
        safety_tier = str(context.safety_tier or "normal")
        reason_codes = list(context.reason_codes or ())

        if context.sos_triggered or safety_tier == "critical":
            return cls._sos_decision(context, reason_codes)

        if cls.ELEVATED_MIN <= distress <= cls.ELEVATED_MAX or safety_tier in {"elevated", "voice_recommended"}:
            return cls._elevated_decision(context, reason_codes)

        return cls._normal_decision(context, reason_codes)

    @classmethod
    def _terminal_skip(
        cls,
        *,
        risk_mode: str,
        reason: str,
        reason_codes: list[str],
        bypassed: bool = False,
        min_cards: int = 0,
        max_cards: int = 1,
    ) -> VoicePolicyDecision:
        return VoicePolicyDecision(
            should_attach_voice=False,
            risk_mode=risk_mode,  # type: ignore[arg-type]
            ordinary_cooldown_bypassed=bypassed,
            min_voice_cards=min_cards,
            max_voice_cards=max_cards,
            voice_messages=[],
            reason_codes=[*reason_codes, reason],
        )

    @classmethod
    def _sos_decision(cls, context: VoicePolicyContext, reason_codes: list[str]) -> VoicePolicyDecision:
        if not context.user_voice_enabled:
            return cls._terminal_skip(
                risk_mode="sos",
                reason="user_voice_disabled",
                reason_codes=reason_codes,
                bypassed=True,
                min_cards=2,
                max_cards=3,
            )
        if not context.provider_enabled:
            return cls._terminal_skip(
                risk_mode="sos",
                reason="provider_disabled",
                reason_codes=reason_codes,
                bypassed=True,
                min_cards=2,
                max_cards=3,
            )

        intents: list[VoiceIntent] = [
            "sos_grounding",
            "sos_stay_with_user",
            "sos_next_safe_step",
        ]
        messages = [
            build_voice_message_plan(
                plan_id=f"sos_voice_{idx + 1}",
                intent=intent,
                priority="high",
                dedupe_policy="reuse_or_variant",
                visible_text=context.visible_text,
                max_duration_seconds=45,
                variant_index=idx,
                reason_codes=[*reason_codes, "sos_voice_required"],
            )
            for idx, intent in enumerate(intents)
        ]
        return VoicePolicyDecision(
            should_attach_voice=True,
            risk_mode="sos",
            ordinary_cooldown_bypassed=True,
            min_voice_cards=2,
            max_voice_cards=3,
            voice_messages=messages,
            reason_codes=[*reason_codes, "sos_bypasses_ordinary_cooldown"],
        )

    @classmethod
    def _elevated_decision(cls, context: VoicePolicyContext, reason_codes: list[str]) -> VoicePolicyDecision:
        if not context.user_voice_enabled:
            return cls._terminal_skip(risk_mode="elevated", reason="user_voice_disabled", reason_codes=reason_codes)
        if context.purely_technical_turn:
            return cls._terminal_skip(risk_mode="elevated", reason="technical_turn", reason_codes=reason_codes)
        if not context.current_turn_has_emotional_weight:
            return cls._terminal_skip(risk_mode="elevated", reason="no_emotional_weight", reason_codes=reason_codes)
        if context.cooldown_active:
            return cls._terminal_skip(risk_mode="elevated", reason="ordinary_cooldown_active", reason_codes=reason_codes)

        message = build_voice_message_plan(
            plan_id="elevated_voice_1",
            intent="elevated_encouragement",
            priority="normal",
            dedupe_policy="reuse_if_ready",
            visible_text=context.visible_text,
            max_duration_seconds=30,
            reason_codes=[*reason_codes, "elevated_distress_not_casual"],
        )
        return VoicePolicyDecision(
            should_attach_voice=True,
            risk_mode="elevated",
            max_voice_cards=1,
            voice_messages=[message],
            reason_codes=[*reason_codes, "elevated_voice_allowed"],
        )

    @classmethod
    def _normal_decision(cls, context: VoicePolicyContext, reason_codes: list[str]) -> VoicePolicyDecision:
        if not context.user_voice_enabled:
            return cls._terminal_skip(risk_mode="normal", reason="user_voice_disabled", reason_codes=reason_codes)
        if context.cooldown_active:
            return cls._terminal_skip(risk_mode="normal", reason="ordinary_cooldown_active", reason_codes=reason_codes)
        if context.purely_technical_turn or not context.current_turn_has_emotional_weight:
            return cls._terminal_skip(risk_mode="normal", reason="low_voice_value_turn", reason_codes=reason_codes)
        if float(context.distress_score or 0.0) > cls.CASUAL_MAX:
            return cls._terminal_skip(risk_mode="normal", reason="outside_casual_range", reason_codes=reason_codes)

        message = build_voice_message_plan(
            plan_id="casual_voice_1",
            intent="casual_praise",
            priority="low",
            dedupe_policy="reuse_if_ready",
            visible_text=context.visible_text,
            max_duration_seconds=25,
            reason_codes=[*reason_codes, "casual_sparse_voice"],
        )
        return VoicePolicyDecision(
            should_attach_voice=True,
            risk_mode="normal",
            max_voice_cards=1,
            voice_messages=[message],
            reason_codes=[*reason_codes, "casual_voice_allowed"],
        )
