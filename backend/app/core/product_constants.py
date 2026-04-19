"""
Product / Legal knobs (BACKEND_PLAN §15). Tune with Product before production.
"""

# Guest trial — max session wall time (seconds)
GUEST_TRIAL_MAX_DURATION_SEC = 900

# Distress ladder (BACKEND_PLAN §7.9) — align distress_score 0.0–1.0
DISTRESS_VOICE_HINT = 0.8
DISTRESS_CRITICAL = 0.9

# Policy document version surfaced to clients
CURRENT_POLICY_VERSION = "1.0"
