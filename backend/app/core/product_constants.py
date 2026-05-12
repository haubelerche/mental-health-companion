"""
Product / Legal knobs (BACKEND_PLAN §15). Tune with Product before production.
"""

# Guest trial - max session wall time (seconds)
GUEST_TRIAL_MAX_DURATION_SEC = 120

# Distress ladder (BACKEND_PLAN §7.9) - align distress_score 0.0-1.0
DISTRESS_CONSTRAIN_RESPONSE_MIN = 0.4
DISTRESS_SUPPORTIVE_CONTINUATION_MIN = 0.55
DISTRESS_VOICE_HINT = 0.8
DISTRESS_CRITICAL = 0.9

# Policy document version surfaced to clients
CURRENT_POLICY_VERSION = "1.0"

# Persona name shown in SOS / consent payloads (Product-facing string)
CHAT_AGENT_DISPLAY_NAME = "Friend"
# Persona rollout gates (BUILDING-PLAN-PERSONAS 20.2)
FEATURE_FLAGS = {
    "persona_router_enabled": True,
    "persona_unlock_progression_enabled": True,
    "heart_economy_enabled": True,
    "rewards_store_enabled": True,
    "persona_hau_luong_unlock_enabled": True,
    "persona_voice_styles_enabled": False,
    "user_memories_enabled": True,
    "knowledge_unlocks_enabled": True,
}
