"""backend/app/safety — centralised safety layer.

Three concerns live here, each independent:
  policy.py           — shared constants
  verdicts.py         — typed output contracts
  content_guardrail.py — shared pattern library (diagnosis, SOS, harmful)
  letter_guardrail.py — letter pipeline (word-count → spam → content)
  output_validator.py — Friend / dashboard / TTS output validator
  escalation.py       — escalation helpers (safety_escalate → SafetyGate)
"""
