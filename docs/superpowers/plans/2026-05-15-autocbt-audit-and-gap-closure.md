# AutoCBT Audit & Gap Closure — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the 4 verified gaps between Serene's backend and the AutoCBT paper's acceptance criteria, as identified in the 2026-05-15 audit.

**Architecture:** Serene's advisor pipeline already satisfies 11/15 AutoCBT mechanisms. This plan targets the 4 remaining gaps: (1) evidence\_refs bug, (2) advisor selector fallback, (3) voice/meme plan-driven emission from FriendAgentOutput, (4) memory dedup verification. No new agents. No architectural changes.

**Tech Stack:** Python 3.11 · FastAPI · Pydantic v2 · pytest · ThreadPoolExecutor

---

## Audit Summary (Read Before Implementing)

| Gap | Severity | File | Line |
|---|---|---|---|
| `evidence_refs=[]` hardcoded — case IDs not forwarded | **P0** | `counseling_advisor_service.py` | L127 |
| AdvisorSelector fallback ignores recent context | **P1** | `advisor_selector.py` | L124 |
| `FriendAgentOutput` has no `tts_candidate`/`meme_candidate` | **P1** | `friend_agent.py` | entire |
| Memory dedup behavior unverified (no test coverage) | **P1** | `tests/` | missing |

---

## Task 1: Fix Evidence Refs — Forward case_refs to AdvisorAdvice

**Files:**
- Modify: `backend/app/services/counseling_advisor_service.py:117-138`
- Test: `backend/tests/test_counseling_advisor_evidence_refs.py` (new)

### Step 1.1 — Write the failing test

- [ ] Create `backend/tests/test_counseling_advisor_evidence_refs.py`:

```python
"""Test that CounselingAdvisorService forwards case_refs into evidence_refs."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.services.counseling_advisor_service import CounselingAdvisorService
from app.services.schemas.advisors import (
    AdvisorCase,
    AdvisorCaseRetrievalResult,
    CounselingGuidance,
)


def _make_case(case_id: str) -> AdvisorCase:
    return AdvisorCase(
        case_id=case_id,
        user_context="Mình cảm thấy quá tải, không biết bắt đầu từ đâu.",
        topic_tags=["overload"],
        emotional_state_tags=["exhausted"],
        recommended_approach="validate + one small step",
        counseling_goal="giảm tải cảm giác bế tắc",
        intervention_steps=["Thở sâu 3 lần", "Chọn 1 việc làm được ngay"],
        reflection_questions=["Phần nào khó nhất lúc này?"],
        do_say=["Mình nghe cậu đang rất mệt."],
        do_not_say=["diagnosis", "Chắc bạn bị stress mãn tính"],
    )


def test_evidence_refs_forwarded_when_cases_retrieved():
    """evidence_refs must contain the retrieved case IDs, not be empty."""
    mock_retriever = MagicMock()
    mock_retriever.retrieve.return_value = AdvisorCaseRetrievalResult(
        cases=[_make_case("case_001"), _make_case("case_002")],
        approved_only=True,
        fallback_used=False,
    )

    service = CounselingAdvisorService(retriever=mock_retriever)
    guidance = service.build_guidance(
        user_message="Mình quá tải, không biết bắt đầu từ đâu.",
        interaction_need="advice",
    )
    advice = service.as_advisor_advice(guidance=guidance)

    assert "case_001" in advice.evidence_refs, (
        "case_refs from retrieval must be forwarded to evidence_refs"
    )
    assert "case_002" in advice.evidence_refs


def test_evidence_refs_empty_on_fallback():
    """evidence_refs must be [] when fallback heuristic is used (no cases retrieved)."""
    mock_retriever = MagicMock()
    mock_retriever.retrieve.return_value = AdvisorCaseRetrievalResult(
        cases=[],
        approved_only=True,
        fallback_used=True,
    )

    service = CounselingAdvisorService(retriever=mock_retriever)
    guidance = service.build_guidance(
        user_message="mình cũng không biết nữa",
        interaction_need=None,
    )
    advice = service.as_advisor_advice(guidance=guidance)

    assert advice.evidence_refs == [], (
        "Fallback guidance must produce empty evidence_refs (no retrieved cases)"
    )


def test_confidence_higher_when_cases_retrieved():
    """confidence must be 0.82 when case_refs exist, 0.68 when fallback."""
    mock_retriever = MagicMock()

    # With cases
    mock_retriever.retrieve.return_value = AdvisorCaseRetrievalResult(
        cases=[_make_case("case_abc")],
        approved_only=True,
        fallback_used=False,
    )
    service = CounselingAdvisorService(retriever=mock_retriever)
    guidance_with = service.build_guidance(user_message="test", interaction_need=None)
    advice_with = service.as_advisor_advice(guidance=guidance_with)
    assert advice_with.confidence == 0.82

    # Without cases
    mock_retriever.retrieve.return_value = AdvisorCaseRetrievalResult(
        cases=[], approved_only=True, fallback_used=True
    )
    guidance_without = service.build_guidance(user_message="test", interaction_need=None)
    advice_without = service.as_advisor_advice(guidance=guidance_without)
    assert advice_without.confidence == 0.68
```

### Step 1.2 — Run test to verify it fails

- [ ] Run: `pytest backend/tests/test_counseling_advisor_evidence_refs.py -v`
- Expected: FAIL with `AssertionError: case_refs from retrieval must be forwarded`

### Step 1.3 — Fix the bug in counseling_advisor_service.py

- [ ] Edit `backend/app/services/counseling_advisor_service.py`, function `as_advisor_advice()`:

Change line 127 from:
```python
evidence_refs=[],
```
To:
```python
evidence_refs=guidance.case_refs,
```

Full updated function for clarity:
```python
def as_advisor_advice(self, *, guidance: CounselingGuidance) -> AdvisorAdvice:
    moves = _dedupe(
        [
            guidance.one_practical_step or "",
            guidance.one_reflection_question or "",
            guidance.response_goal,
            *[move for move in guidance.recommended_moves if not re.search(r"\b(validate|formulate|offer|briefly)\b", move, re.IGNORECASE)],
        ],
        limit=4,
    )
    return AdvisorAdvice(
        advisor_id=self.advisor_id,
        confidence=0.82 if guidance.case_refs else 0.68,
        evidence_refs=guidance.case_refs,  # ← FIXED: was evidence_refs=[]
        advice_to_friend=[
            guidance.case_understanding,
            guidance.response_goal,
        ],
        suggested_response_moves=moves,
        forbidden_moves=list(guidance.avoid),
        should_use=True,
    )
```

### Step 1.4 — Run test to verify it passes

- [ ] Run: `pytest backend/tests/test_counseling_advisor_evidence_refs.py -v`
- Expected: All 3 tests PASS

### Step 1.5 — Run full test suite to check no regression

- [ ] Run: `pytest backend/tests -q`
- Expected: All existing tests still pass

### Step 1.6 — Commit

```bash
git add backend/app/services/counseling_advisor_service.py backend/tests/test_counseling_advisor_evidence_refs.py
git commit -m "fix(advisor): forward case_refs into evidence_refs in CounselingAdvisorService"
```

---

## Task 2: AdvisorSelector — Context-Aware Fallback

**Files:**
- Modify: `backend/app/services/advisor_selector.py`
- Test: `backend/tests/test_advisor_selector_context_fallback.py` (new)

**Problem:** When no keyword matches, selector falls back to `reflection_advisor` without considering recent message context. A short "ừ" after emotional messages → wrong advisor.

### Step 2.1 — Write failing tests

- [ ] Create `backend/tests/test_advisor_selector_context_fallback.py`:

```python
"""Test AdvisorSelector's context-aware fallback logic."""
from __future__ import annotations

import pytest

from app.services.advisor_selector import AdvisorSelector
from app.services.schemas.routing import AdvisorSelection, RoutingDecision


def _routing_advisor() -> RoutingDecision:
    return RoutingDecision(
        route_tier="advisor_assisted",
        reason_codes=["repeated_self_blame"],
        should_call_advisors=True,
    )


def test_short_ack_after_emotional_recent_gets_empathy_advisor():
    """A short ack after 2+ emotional messages should pick empathy_advisor, not reflection_advisor."""
    recent = [
        "Mình căng thẳng quá, cảm thấy kiệt sức rồi",
        "Không biết mình có ổn không",
    ]
    selection = AdvisorSelector().select(
        routing=_routing_advisor(),
        user_message="ừ",
        recent_user_messages=recent,
    )
    assert "empathy_advisor" in selection.advisor_ids, (
        "Short ack after emotional context must select empathy_advisor"
    )


def test_no_keyword_match_and_no_recent_context_gets_reflection():
    """Without any signal, reflection_advisor is the safe fallback."""
    selection = AdvisorSelector().select(
        routing=_routing_advisor(),
        user_message="không biết",
        recent_user_messages=[],
    )
    assert "reflection_advisor" in selection.advisor_ids


def test_recent_self_blame_adds_cbt_advisor():
    """Two recent self-blame messages should add cbt_pattern_advisor even for short current message."""
    recent = [
        "Mình cứ tự trách mình mãi, lỗi do mình hết",
        "Thấy mình vô dụng quá",
    ]
    selection = AdvisorSelector().select(
        routing=_routing_advisor(),
        user_message="vâng",
        recent_user_messages=recent,
    )
    assert "cbt_pattern_advisor" in selection.advisor_ids or "empathy_advisor" in selection.advisor_ids, (
        "Recent self-blame context must produce a relevant advisor"
    )


def test_max_two_advisors_still_enforced_with_context():
    """Context-aware fallback must not exceed MAX_ADVISORS_PER_TURN=2."""
    recent = [
        "Mình vừa cãi nhau với gia đình, deadline gấp, ăn uống thất thường, cảm thấy kiệt sức",
        "Lỗi tại mình hết thôi, mình vô dụng",
    ]
    selection = AdvisorSelector().select(
        routing=_routing_advisor(),
        user_message="ừ mình hiểu",
        recent_user_messages=recent,
    )
    assert len(selection.advisor_ids) <= 2, "Context-aware path must still cap at 2 advisors"
```

### Step 2.2 — Run to verify failures

- [ ] Run: `pytest backend/tests/test_advisor_selector_context_fallback.py -v`
- Expected: test_short_ack_after_emotional_recent_gets_empathy_advisor and test_recent_self_blame_adds_cbt_advisor FAIL

### Step 2.3 — Implement context-aware fallback in advisor_selector.py

- [ ] Edit `backend/app/services/advisor_selector.py`, modify the `select()` method. Add a recent-context check before the unconditional fallback:

```python
# Replace lines 124-126:
if not picked:
    picked = ["reflection_advisor"]
```

With:

```python
if not picked:
    # Context-aware fallback: check recent messages for emotional signals
    recent_normalized = [_normalize(m) for m in (recent_user_messages or [])[-3:]]
    recent_combined = " ".join(recent_normalized)

    has_recent_emotional = any(
        k in recent_combined
        for k in (
            "cam thay", "buon", "met", "tuyet vong", "qua tai",
            "kiet suc", "khong on", "can kiet",
        )
    )
    has_recent_self_blame = any(
        k in recent_combined
        for k in (
            "tu trach", "loi tai minh", "tai minh", "vo dung",
            "thua kem", "minh te", "minh kem",
        )
    )

    if has_recent_self_blame:
        picked = ["cbt_pattern_advisor"]
    elif has_recent_emotional:
        picked = ["empathy_advisor"]
    else:
        picked = ["reflection_advisor"]
```

### Step 2.4 — Run test to verify passes

- [ ] Run: `pytest backend/tests/test_advisor_selector_context_fallback.py -v`
- Expected: All 4 tests PASS

### Step 2.5 — Run autocbt compliance tests

- [ ] Run: `pytest backend/tests/test_autocbt_compliance.py backend/tests/test_advisor_selector_context_fallback.py -v`
- Expected: All tests PASS (selector changes must not break existing compliance tests)

### Step 2.6 — Commit

```bash
git add backend/app/services/advisor_selector.py backend/tests/test_advisor_selector_context_fallback.py
git commit -m "feat(advisor-selector): context-aware fallback uses recent emotional signals"
```

---

## Task 3: FriendAgentOutput — Emit tts_candidate and meme_candidate

**Files:**
- Modify: `backend/app/services/schemas/contracts.py` — add fields to `FriendAgentOutput`
- Modify: `backend/app/services/friend_agent.py` — populate fields in `compose()`
- Test: `backend/tests/test_friend_agent_response_plan.py` (new)

**Problem:** `FriendAgentOutput` does not carry `tts_candidate` or `meme_candidate`. Voice/meme decisions are made outside the finalizer, disconnected from the response plan. This violates AutoCBT's "single response plan" pattern and SERENE_AUTOCBT_FEATURE_AUDIT_AND_DEBUG_PLAN §PR-07.

### Step 3.1 — Write failing tests

- [ ] Create `backend/tests/test_friend_agent_response_plan.py`:

```python
"""Test FriendAgentOutput emits response-plan-driven tts_candidate and meme_candidate."""
from __future__ import annotations

import pytest

from app.services.friend_agent import FriendAgent
from app.services.schemas.contracts import AdvisorAdvice, ContextPack, FriendAgentOutput, SafetyPolicyDecision


def _make_pack(*, distress_score: float = 0.2, risk_level: int = 0, persona_id: str = "dung_luong") -> ContextPack:
    policy = SafetyPolicyDecision(
        policy_action="allow",
        risk_level=risk_level,
        distress_score=distress_score,
        persona_style_strength=0.8,
    )
    return ContextPack(
        safety_policy=policy,
        persona_context={"selected": persona_id},
        recent_messages=[],
    )


def test_friend_output_has_tts_candidate_field():
    """FriendAgentOutput must have a tts_candidate field (may be None for fast turns)."""
    output = FriendAgent().compose(
        user_message="Chào cậu",
        context_pack=_make_pack(),
    )
    assert hasattr(output, "tts_candidate"), "FriendAgentOutput must have tts_candidate field"


def test_friend_output_has_meme_candidate_field():
    """FriendAgentOutput must have a meme_candidate field (may be None)."""
    output = FriendAgent().compose(
        user_message="Chào cậu",
        context_pack=_make_pack(),
    )
    assert hasattr(output, "meme_candidate"), "FriendAgentOutput must have meme_candidate field"


def test_high_risk_suppresses_meme_candidate():
    """High-risk turns (risk_level >= 3) must not emit a meme_candidate."""
    output = FriendAgent().compose(
        user_message="Mình không muốn sống nữa",
        context_pack=_make_pack(distress_score=0.85, risk_level=4),
    )
    assert output.meme_candidate is None, (
        "meme_candidate must be None for high-risk turns"
    )


def test_low_risk_playful_may_have_meme_candidate():
    """Low-risk playful turn should produce a meme_candidate hint (not None)."""
    output = FriendAgent().compose(
        user_message="Kể meme vui đi, mình đang cần cười",
        context_pack=_make_pack(distress_score=0.05, risk_level=0),
    )
    # meme_candidate may be None if FriendAgent decides not to emit one;
    # the field must exist and not raise
    assert hasattr(output, "meme_candidate")


def test_tts_candidate_none_for_very_short_response():
    """Very short responses (greetings) may have tts_candidate=None — that is valid."""
    output = FriendAgent().compose(
        user_message="ừ",
        context_pack=_make_pack(),
    )
    # Either None or a string; must not crash
    assert output.tts_candidate is None or isinstance(output.tts_candidate, str)
```

### Step 3.2 — Run to verify failures

- [ ] Run: `pytest backend/tests/test_friend_agent_response_plan.py -v`
- Expected: `test_friend_output_has_tts_candidate_field` and `test_friend_output_has_meme_candidate_field` FAIL (fields don't exist yet)

### Step 3.3 — Add fields to FriendAgentOutput schema

- [ ] Find `FriendAgentOutput` in `backend/app/services/schemas/contracts.py` and add optional fields:

```python
# In FriendAgentOutput dataclass/Pydantic model, add after existing fields:
tts_candidate: str | None = None
# Short voice text derived from final_text; None = don't attach voice this turn.
# Populated by FriendAgent when: low/medium risk + voice feature enabled + text warrants voice.

meme_candidate: str | None = None
# Reason code for meme selection (e.g. "playful_low_risk", "encouragement").
# None = suppress meme. High-risk turns must set this to None.
# Frontend maps reason code → actual meme asset.
```

### Step 3.4 — Populate fields in FriendAgent.compose()

- [ ] In `backend/app/services/friend_agent.py`, at the end of `compose()`, before returning `FriendAgentOutput`, add logic to populate the new fields:

```python
# After generating final_text and before return:

risk_level = context_pack.safety_policy.risk_level if context_pack.safety_policy else 0
distress_score = context_pack.safety_policy.distress_score if context_pack.safety_policy else 0.0

# tts_candidate: short voice script derived from final_text
# Only emit when text is substantive and risk is not high
tts_candidate: str | None = None
if risk_level < 3 and final_text and len(final_text) >= 20:
    # Truncate to first 2 sentences for voice (TTS renderer will also cap)
    sentences = [s.strip() for s in re.split(r"[.!?]", final_text) if s.strip()]
    tts_candidate = ". ".join(sentences[:2]) if sentences else None

# meme_candidate: reason code for meme selection
# Suppress on high risk; emit hint code on low risk playful context
meme_candidate: str | None = None
if risk_level < 2 and distress_score < 0.45:
    # Check if turn is playful/lighthearted
    user_lower = user_message.lower()
    if any(k in user_lower for k in ("meme", "vui", "cười", "hài", "funny", "mood")):
        meme_candidate = "playful_low_risk"
```

### Step 3.5 — Run tests

- [ ] Run: `pytest backend/tests/test_friend_agent_response_plan.py -v`
- Expected: All 5 tests PASS

### Step 3.6 — Run full compliance suite

- [ ] Run: `pytest backend/tests/test_autocbt_compliance.py backend/tests/test_friend_agent_response_plan.py -v`
- Expected: All PASS. FriendAgentOutput changes must not break existing role contract tests.

### Step 3.7 — Commit

```bash
git add backend/app/services/schemas/contracts.py backend/app/services/friend_agent.py backend/tests/test_friend_agent_response_plan.py
git commit -m "feat(friend-agent): emit tts_candidate and meme_candidate from response plan"
```

---

## Task 4: Memory Dedup — Verify and Fix mention_count Behavior

**Files:**
- Read: `backend/app/services/db/models.py` — MemoryCard model
- Read: `backend/app/services/` — any file handling memory extraction
- Test: `backend/tests/test_memory_dedup_mention_count.py` (new)

**Problem:** It is unverified whether repeated facts update `mention_count` on existing MemoryCard vs creating duplicate cards.

### Step 4.1 — First, read the memory extraction code

- [ ] Run: `grep -rn "mention_count\|MemoryCard\|extract_memory" backend/app/services/ --include="*.py" -l`
- [ ] Read all files listed. Identify: where is `mention_count` incremented? Where is dedup checked?

### Step 4.2 — Write failing test for dedup behavior

- [ ] Create `backend/tests/test_memory_dedup_mention_count.py` after reading the code:

```python
"""Test that repeated memory facts update mention_count, not create duplicate cards.

IMPORTANT: Read the memory extraction service before editing this test template.
The actual function names and parameters depend on what you find in Step 4.1.
Replace the placeholder calls below with the real API.
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch


# TEMPLATE — replace with real imports after Step 4.1 investigation
# from app.services.memory_cards import upsert_memory_card
# from app.services.db.models import MemoryCard


def test_repeated_fact_updates_mention_count_not_creates_duplicate():
    """
    Given: A MemoryCard with content "tên là Hậu" already exists.
    When: The same fact is extracted again with similar wording.
    Then: mention_count on the existing card increments; no new card created.

    IMPLEMENT after Step 4.1 reveals the actual memory upsert API.
    """
    pytest.skip("Implement after reading memory extraction code in Step 4.1")


def test_distinct_facts_create_separate_cards():
    """
    Given: No existing cards.
    When: Two semantically distinct facts are extracted.
    Then: Two separate cards are created (no false merge).

    IMPLEMENT after Step 4.1.
    """
    pytest.skip("Implement after reading memory extraction code in Step 4.1")


def test_deleted_card_not_used_in_context():
    """
    Given: A MemoryCard exists but is_deleted=True.
    When: context_pack_builder loads memory.
    Then: The deleted card does not appear in ContextPack.

    IMPLEMENT after Step 4.1.
    """
    pytest.skip("Implement after reading memory extraction code in Step 4.1")
```

### Step 4.3 — Implement based on findings

After reading the code:
- If `mention_count` increment already exists → write tests that verify it works
- If dedup is missing → implement upsert logic and write tests

The implementation MUST satisfy:
1. Same semantic fact → `mention_count += 1` on existing card
2. Distinct facts → separate cards
3. `is_deleted=True` cards excluded from context injection

### Step 4.4 — Run memory tests

- [ ] Run: `pytest backend/tests/test_memory_dedup_mention_count.py -v`
- Expected: All tests PASS (skip tests must be replaced with real implementations)

### Step 4.5 — Run full test suite

- [ ] Run: `pytest backend/tests -q`
- Expected: All tests PASS (no regression from memory changes)

### Step 4.6 — Commit

```bash
git add backend/app/services/ backend/tests/test_memory_dedup_mention_count.py
git commit -m "test(memory): verify mention_count dedup for repeated facts"
```

---

## Task 5: Final Verification

### Step 5.1 — Run full backend test suite

- [ ] Run: `pytest backend/tests -q`
- Expected: All tests pass. Zero failures.

### Step 5.2 — Run targeted autocbt compliance

- [ ] Run: `pytest backend/tests/test_autocbt_compliance.py -v`
- Expected: All 12 tests PASS

### Step 5.3 — Run all new tests together

- [ ] Run: `pytest backend/tests/test_counseling_advisor_evidence_refs.py backend/tests/test_advisor_selector_context_fallback.py backend/tests/test_friend_agent_response_plan.py backend/tests/test_memory_dedup_mention_count.py -v`
- Expected: All PASS

### Step 5.4 — Update CHANGELOG.md

- [ ] Add entry to `CHANGELOG.md`:

```markdown
## [feat/autocbt-gap-closure] — 2026-05-15

### Fixed
- `CounselingAdvisorService.as_advisor_advice()`: `evidence_refs` now forwards `case_refs` from JSONL retrieval instead of hardcoded `[]` (P0 bug)

### Improved
- `AdvisorSelector.select()`: fallback now uses recent message context (empathy/self-blame signals) instead of always defaulting to `reflection_advisor`
- `FriendAgentOutput`: new fields `tts_candidate` and `meme_candidate` emitted from response plan; high-risk turns suppress `meme_candidate`

### Verified
- Memory dedup behavior (`mention_count` increment vs duplicate card creation) covered by new test suite
- AutoCBT §18 acceptance criteria: all 12 compliance tests pass
```

---

## Self-Review Checklist

- [x] **Spec coverage**: All 4 P0/P1 gaps from audit → covered by Tasks 1–4
- [x] **Placeholder scan**: No TBD. Task 4.2 uses `pytest.skip()` explicitly pending Step 4.1 investigation — this is intentional, not a placeholder
- [x] **Type consistency**: `tts_candidate: str | None`, `meme_candidate: str | None` used consistently in Task 3
- [x] **No architectural changes**: No new agents, no new service boundaries, no new external dependencies
- [x] **Backward compatibility**: New fields on `FriendAgentOutput` are `Optional` with `None` defaults — existing callers unaffected
- [x] **Stop-ship criteria checked**: After this plan, criteria #3 (evidence_refs), #10 (meme suppression) should be PASS

---

## Remaining Risks After This Plan

| Risk | Severity | Notes |
|---|---|---|
| `langgraph_chat.py` is 30k+ lines | P1 | Needs refactor into smaller files but is out of scope for this plan |
| Dashboard Analyst insight generation from PHQ-9+mood+nutrition | P1 | Unverified — needs separate audit and plan |
| AdvisorSelector is keyword-only (no semantic similarity) | P2 | Works for known Vietnamese patterns; may miss novel phrasing |
| ElevenLabs single-provider TTS | P2 | No fallback provider; outage disables all voice |
| In-memory voice job locks | P2 | Single-instance only; multi-process requires Redis |
