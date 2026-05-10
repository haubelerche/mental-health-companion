# Serene Multiagent Flow Audit & SOS Redesign (Revised)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 3 vấn đề cần xử lý: (1) AnalystNode không đọc Neo4j user patterns khi phân tích; (2) Memory Ký ức tab trống — audit extraction trigger đang hoạt động không; (3) SOS voice flow lỗi + redesign thành 3 voice segments + 2 LLM counseling texts, bỏ CrisisStepper và user-facing notification.

**Architecture:** SafetyGate deterministic — không đổi. LLM crisis generation sau SOS gate (per PRD). Neo4j wrapped bằng `asyncio.to_thread()` để không block event loop. 3 voice scripts đi qua `_build_voice_intervention()` được mở rộng với `voice_scripts: list[str]` — cooldown chỉ gọi một lần. `CrisisInterventionPlan` giữ contract hiện tại, thêm `follow_up_texts` và `additional_voice_scripts` backward-compat.

**PR structure:**
- **PR-A**: Analyst graph context provider (Task 1)
- **PR-B**: Memory audit + regression tests (Task 2)
- **PR-C**: SOS plan schema + backend + frontend (Task 3a → 3c)

**Tech Stack:** Python 3.11 / FastAPI async / Neo4j sync driver (wrapped) / OpenAI AsyncClient / React 19 / TypeScript

---

## Critical Files Map

| File | Thay đổi |
|------|---------|
| `backend/app/services/neo4j_client.py` | Thêm `get_user_patterns_async()` — wrap sync driver bằng `asyncio.to_thread()` |
| `backend/app/services/langgraph_chat.py` | Inject `GraphContextResult` vào analyst_node prompt; propagate `graph_context_used` field |
| `backend/app/services/crisis_intervention_planner.py` | Thêm `follow_up_texts: list[str]` + `additional_voice_scripts: list[str]`; thêm `build_llm_crisis_messages()` async |
| `backend/app/api/v1/routers/chat.py` | Xóa `enqueue_notification` block; cập nhật SOS path dùng LLM messages; mở rộng `_build_voice_intervention()` xử lý list scripts với single cooldown |
| `frontend/src/components/chat/Chat.tsx` | Xóa `<CrisisStepper>` render (per user request); thêm `follow_up_texts` inline render; fix polling fallback unblock input; thêm sequential voice playback |
| `backend/tests/test_db_integration.py` | Tests `get_user_patterns_async()` |
| `backend/tests/test_memory_cards.py` | Regression tests cho `_maybe_extract_cards` flow |

---

## PR-A: Task 1 — Analyst Graph Context Provider

**Problem:** `analyst_node()` (`langgraph_chat.py:867–986`) gọi OpenAI không có user behavioral patterns từ Neo4j. User có lịch sử triggers/emotions/coping trong graph nhưng Analyst không biết → phân tích thiếu context cá nhân.

**Constraint:**
- Neo4j driver là SYNC blocking → phải wrap `asyncio.to_thread()`
- Neo4j là derived graph, không phải source of truth → đây là optional context, fail-safe
- Nếu Neo4j không available → analyst chạy bình thường, `graph_context_used=False`

---

- [ ] **Step 1: Thêm `get_user_patterns_async()` vào neo4j_client.py**

```python
# backend/app/services/neo4j_client.py — thêm sau get_neo4j_driver()

import asyncio
import logging

_neo4j_log = logging.getLogger(__name__)


def _query_user_patterns_sync(user_id: str, limit: int) -> dict:
    """Blocking Neo4j query — only call via asyncio.to_thread()."""
    driver = get_neo4j_driver()
    if driver is None:
        return {"triggers": [], "emotions": [], "coping": [], "available": False}
    try:
        with driver.session() as session:
            result = session.run(
                """
                MATCH (u:User {user_id: $uid})
                OPTIONAL MATCH (u)-[r1:EXPERIENCED]->(t:Trigger)
                OPTIONAL MATCH (u)-[r2:FELT]->(e:Emotion)
                OPTIONAL MATCH (u)-[r3:USED_COPING]->(c:CopingAction)
                RETURN
                  collect(DISTINCT {name: t.name, count: r1.count})[..$lim] AS triggers,
                  collect(DISTINCT {name: e.name, count: r2.count})[..$lim] AS emotions,
                  collect(DISTINCT {name: c.name, effectiveness: r3.effectiveness_avg})[..$lim] AS coping
                """,
                uid=user_id,
                lim=limit,
            )
            row = result.single()
            if row is None:
                return {"triggers": [], "emotions": [], "coping": [], "available": True}
            return {
                "triggers": [r for r in (row["triggers"] or []) if r.get("name")],
                "emotions": [r for r in (row["emotions"] or []) if r.get("name")],
                "coping": [r for r in (row["coping"] or []) if r.get("name")],
                "available": True,
            }
    except Exception as exc:
        _neo4j_log.warning("Neo4j pattern query failed user=%s: %s", user_id, exc)
        return {"triggers": [], "emotions": [], "coping": [], "available": False}


async def get_user_patterns_async(user_id: str, limit: int = 5) -> dict:
    """
    Non-blocking Neo4j user pattern query. Wraps sync driver via asyncio.to_thread().
    Returns empty dicts with available=False on any failure.
    """
    return await asyncio.to_thread(_query_user_patterns_sync, user_id, limit)
```

- [ ] **Step 2: Viết tests trước khi inject**

```python
# backend/tests/test_db_integration.py — thêm

import pytest

@pytest.mark.asyncio
async def test_get_user_patterns_async_no_driver(monkeypatch):
    """Returns empty + available=False when Neo4j driver is None."""
    import backend.app.services.neo4j_client as nc
    monkeypatch.setattr(nc, "get_neo4j_driver", lambda: None)
    result = await nc.get_user_patterns_async("user_test")
    assert result["available"] is False
    assert result["triggers"] == []
    assert result["emotions"] == []
    assert result["coping"] == []


@pytest.mark.asyncio
async def test_get_user_patterns_async_filters_none_names(monkeypatch):
    """Rows with name=None are filtered out."""
    import backend.app.services.neo4j_client as nc

    class FakeRow:
        def __getitem__(self, key):
            if key == "triggers":
                return [{"name": None, "count": 3}, {"name": "academic_pressure", "count": 5}]
            if key == "emotions":
                return []
            return [{"name": "walking", "effectiveness": 0.8}]

    class FakeResult:
        def single(self): return FakeRow()

    class FakeSession:
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def run(self, *a, **kw): return FakeResult()

    class FakeDriver:
        def session(self): return FakeSession()

    monkeypatch.setattr(nc, "get_neo4j_driver", lambda: FakeDriver())
    result = await nc.get_user_patterns_async("user_test")
    assert len(result["triggers"]) == 1
    assert result["triggers"][0]["name"] == "academic_pressure"
```

- [ ] **Step 3: Chạy test — xác nhận FAIL**

```bash
pytest backend/tests/test_db_integration.py -v -k "user_patterns"
```

Expected: FAIL với `AttributeError: has no attribute 'get_user_patterns_async'`

- [ ] **Step 4: Implement `get_user_patterns_async`** (code ở Step 1) và chạy lại

```bash
pytest backend/tests/test_db_integration.py -v -k "user_patterns"
```

Expected: 2 PASSED

- [ ] **Step 5: Inject vào analyst_node trong langgraph_chat.py**

Tìm `analyst_node()` (~line 867). Tìm đoạn build system prompt (trước `openai_client.chat.completions.create()`). Thêm:

```python
# Import ở đầu file (nếu chưa có):
from app.services.neo4j_client import get_user_patterns_async

# Trong analyst_node(), trước openai call:
_graph_raw = await get_user_patterns_async(user_id)
_graph_context_used = _graph_raw.get("available", False) and any(
    _graph_raw.get(k) for k in ("triggers", "emotions", "coping")
)
_graph_context_block = ""
if _graph_context_used:
    _t = ", ".join(
        f"{x['name']} (×{x['count']})"
        for x in _graph_raw["triggers"]
        if x.get("count")
    ) or "chưa ghi nhận"
    _e = ", ".join(x["name"] for x in _graph_raw["emotions"]) or "chưa ghi nhận"
    _c = ", ".join(
        f"{x['name']} (hiệu quả={x['effectiveness']:.2f})"
        for x in _graph_raw["coping"]
        if x.get("effectiveness") is not None
    ) or "chưa ghi nhận"
    _graph_context_block = (
        f"\n\n[Lịch sử hành vi từ Neo4j — derived context]\n"
        f"Tác nhân hay gặp: {_t}\n"
        f"Cảm xúc hay gặp: {_e}\n"
        f"Chiến lược đối phó đã thử: {_c}"
    )
```

Append `_graph_context_block` vào cuối system prompt string.

Thêm `graph_context_used=_graph_context_used` vào `AnalystBundle` nếu field đó tồn tại, hoặc log nó để observable:

```python
logger.debug("analyst_node graph_context_used=%s user=%s", _graph_context_used, user_id)
```

- [ ] **Step 6: Chạy full backend tests**

```bash
pytest backend/tests -q
```

Expected: All pass

- [ ] **Step 7: Commit (PR-A)**

```bash
git add backend/app/services/neo4j_client.py backend/app/services/langgraph_chat.py backend/tests/test_db_integration.py
git commit -m "feat(analyst): add async Neo4j graph context provider; inject derived user patterns into AnalystNode prompt"
```

---

## PR-B: Task 2 — Memory Audit Only (Không thêm trigger mới)

**Problem:** Tab Ký ức trống. Trước khi implement bất cứ thứ gì, cần xác nhận `_maybe_extract_cards` đang chạy đúng và cards được tạo thành công.

**Đã xác nhận:** `_maybe_extract_cards` chạy tại `chat.py:754–758` (non-stream) và `chat.py:1080–1084` (stream) sau mỗi non-SOS turn. Không thêm trigger mới.

---

- [ ] **Step 1: Kiểm tra extraction dedup trong service**

```bash
grep -n "create_cards_from_candidates\|dedup\|already.*exists\|upsert" backend/app/memory/service.py | head -30
```

Xác nhận có cơ chế tránh tạo duplicate cards không. Ghi lại kết quả.

- [ ] **Step 2: Kiểm tra guardrail có đang reject quá nhiều không**

```bash
grep -n "rejected_by_guardrail\|review_memory_candidate\|is_blocked\|reason" backend/app/memory/guardrail.py
```

Xác nhận các pattern nào đang bị reject. Nếu guardrail reject tất cả candidate → cards không bao giờ được tạo dù extraction chạy.

- [ ] **Step 3: Viết regression tests cho extraction flow**

```python
# backend/tests/test_memory_cards.py — thêm class

class TestExtractionTriggerFlow:
    """Verify _maybe_extract_cards flow produces cards for standard Vietnamese input."""

    def test_extractor_finds_coping_walking(self):
        """Coping history signal: đi bộ + giúp ích."""
        from backend.app.memory.extractor import extract_memory_candidates
        text = "mình hay đi bộ mỗi khi căng thẳng, giúp ích nhiều lắm"
        result = extract_memory_candidates(text, session_id="sess_test")
        types = [c["memory_type"] for c in result["candidate_cards"]]
        assert "coping_history" in types, f"Expected coping_history, got {types}"

    def test_extractor_finds_stressor_deadline(self):
        """Stressor signal: deadline + stress."""
        from backend.app.memory.extractor import extract_memory_candidates
        text = "mình đang stress vì deadline bài nộp tuần sau"
        result = extract_memory_candidates(text, session_id="sess_test")
        types = [c["memory_type"] for c in result["candidate_cards"]]
        assert "current_stressor" in types, f"Expected current_stressor, got {types}"

    def test_extractor_empty_text_returns_no_candidates(self):
        from backend.app.memory.extractor import extract_memory_candidates
        result = extract_memory_candidates("", session_id="sess_test")
        assert result["candidate_cards"] == []

    def test_guardrail_does_not_reject_normal_coping_card(self):
        """A normal coping card should pass guardrail (not SOS, no diagnosis, correct length)."""
        from backend.app.memory.guardrail import review_memory_candidate
        candidate = {
            "memory_type": "coping_history",
            "title": "Cách vượt qua căng thẳng",
            "content": "Đi bộ ngắn từng giúp bạn cảm thấy nhẹ hơn.",
            "confidence": 0.75,
        }
        result = review_memory_candidate(candidate)
        assert not result.is_blocked, f"Unexpected block: {result.reason_codes}"
```

- [ ] **Step 4: Chạy tests**

```bash
pytest backend/tests/test_memory_cards.py -v -k "ExtractionTrigger"
```

Nếu `test_extractor_finds_coping_walking` FAIL → extractor không có Vietnamese pattern → cần thêm pattern vào `_COPING_SIGNALS` trong `backend/app/memory/extractor.py`.

Pattern cần thêm nếu thiếu:

```python
# Trong _COPING_SIGNALS:
(r"(đi bộ|bước đi|dạo bộ).{0,30}(giúp|nhẹ|better|ích|bình tĩnh)", "coping_history",
 "Đi bộ ngắn từng giúp bạn cảm thấy nhẹ hơn.", 0.75),

# Trong _STRESSOR_SIGNALS:
(r"(deadline|bài nộp|nộp bài|áp lực|stress).{0,60}", "current_stressor",
 "Bạn đang có áp lực về deadline hoặc bài nộp.", 0.6),
```

- [ ] **Step 5: Chạy full tests**

```bash
pytest backend/tests -q
```

Expected: All pass

- [ ] **Step 6: Commit (PR-B)**

```bash
git add backend/tests/test_memory_cards.py backend/app/memory/extractor.py
git commit -m "test(memory): add extraction flow regression tests; fix missing Vietnamese coping/stressor patterns"
```

---

## PR-C: Task 3 — SOS Redesign (Schema + Backend + Frontend)

**Mục tiêu:**
1. Xóa user-facing SOS notification (giữ audit logs)
2. Thay CrisisStepper bằng 2 LLM counseling text messages hiển thị inline (per user request)
3. Thêm 3 voice segments LLM-generated, đi qua TTS dedup đúng cách (single cooldown)
4. Fix polling fallback: sau timeout, unblock input

**Key constraint:**
- `_build_voice_intervention()` hiện tại gọi `mark_cooldown()` sau mỗi enqueue → gọi 3 lần sẽ block jobs 2+3
- Fix: mở rộng `_build_voice_intervention()` nhận `voice_scripts: list[str]`, gọi `mark_cooldown()` một lần duy nhất
- TTS dedup vẫn hoạt động đúng vì mỗi script khác nhau → signature khác nhau → 3 jobs riêng biệt

---

### 3a — Mở rộng CrisisInterventionPlan + LLM generator

**Files:** `backend/app/services/crisis_intervention_planner.py`

- [ ] **Step 1: Thêm `follow_up_texts` và `additional_voice_scripts` vào schema**

```python
# Thay class CrisisInterventionPlan (backward-compat: giữ voice_script cũ):

class CrisisInterventionPlan(BaseModel):
    visible_text: str = Field(min_length=1, max_length=500)
    voice_script: str = Field(min_length=10, max_length=1200)  # kept: voice_scripts[0]
    additional_voice_scripts: list[str] = Field(default_factory=list)  # NEW: scripts[1] và [2]
    follow_up_texts: list[str] = Field(default_factory=list)           # NEW: 2 LLM counseling texts
    action_cards: list[CrisisActionCard] = Field(default_factory=list, max_length=3)
    follow_up_question: str = Field(min_length=1, max_length=180)
    safety_reason_codes: list[str] = Field(default_factory=list, max_length=8)
    should_enqueue_voice: bool = True
    source: Literal["llm", "fallback_template"] = "fallback_template"

    @property
    def all_voice_scripts(self) -> list[str]:
        """All voice scripts: primary + additional."""
        return [self.voice_script] + list(self.additional_voice_scripts)
```

- [ ] **Step 2: Thêm 3 fallback voice script groups**

Xóa `_VOICE_SCRIPTS` cũ, thay bằng 3 groups:

```python
_VOICE_GROUNDING = [
    "Mình ở đây với bạn. Hãy đặt hai chân xuống sàn và hít thở chậm lại cùng mình. Bạn không một mình.",
    "Hít vào 4 giây, giữ 4 giây, thở ra 6 giây. Làm lại một lần nữa nhé. Mình ở đây.",
    "Bạn đang có mặt ở đây, và mình cũng vậy. Hãy cảm nhận bàn tay bạn, thở chậm một nhịp cùng mình.",
]
_VOICE_PRESENCE = [
    "Mình nghe bạn. Cảm ơn bạn đã chia sẻ điều này. Mình vẫn ở đây.",
    "Bạn đang rất can đảm khi nói lên điều này. Mình ở đây và lắng nghe từng điều bạn nói.",
    "Không cần nói nhiều ngay bây giờ. Mình ở đây — im lặng cùng bạn cũng được.",
]
_VOICE_NEXT_STEP = [
    "Có những người ngoài đời sẵn sàng nghe bạn ngay lúc này, cả ngày lẫn đêm.",
    "Bạn đã vượt qua được đến đây. Bước tiếp theo nhỏ thôi — chỉ cần tiếp tục ở lại.",
    "Mình sẽ không để bạn một mình trong điều này. Bạn muốn nói tiếp không?",
]

def _pick_three_voice_scripts(session_sos_count: int, is_alone: bool) -> list[str]:
    idx = session_sos_count % 3
    s3 = (
        "Bạn không một mình — mình đang ở đây cùng bạn. Luôn có người sẵn sàng lắng nghe bạn."
        if is_alone
        else _VOICE_NEXT_STEP[idx]
    )
    return [_VOICE_GROUNDING[idx], _VOICE_PRESENCE[idx], s3]
```

- [ ] **Step 3: Cập nhật `build_fallback_crisis_plan()` dùng 3 scripts**

```python
def build_fallback_crisis_plan(...) -> CrisisInterventionPlan:
    # ... (giữ nguyên logic visible_text và follow_up) ...

    _three = _pick_three_voice_scripts(session_sos_count, is_alone)

    return CrisisInterventionPlan(
        visible_text=visible_text,
        voice_script=_three[0],
        additional_voice_scripts=_three[1:],
        follow_up_texts=[],               # populated by LLM caller
        action_cards=_DEFAULT_ACTION_CARDS,
        follow_up_question=follow_up,
        safety_reason_codes=reason_codes or ["sos_gate_triggered"],
        should_enqueue_voice=should_enqueue_voice,
        source="fallback_template",
    )
```

- [ ] **Step 4: Thêm `build_llm_crisis_messages()` async**

```python
# crisis_intervention_planner.py — thêm vào cuối

import asyncio
import json as _json

_LLM_CRISIS_SYSTEM = (
    "Bạn là Serene, AI hỗ trợ sức khoẻ tâm thần người Việt — đang trong tình huống khủng hoảng.\n"
    "Tạo 5 tin nhắn hỗ trợ ngắn, tiếng Việt tự nhiên, tone_level=0 (safe formal per spec).\n\n"
    "RULES:\n"
    "- Dùng 'mình/bạn'\n"
    "- KHÔNG chẩn đoán, KHÔNG nói 'mọi chuyện sẽ ổn'\n"
    "- KHÔNG lặp nội dung giữa 5 tin nhắn\n"
    "- Ngắn, ấm, hiện tại, không phán xét, không slang\n\n"
    "JSON keys:\n"
    "text_1: văn bản 1 — ghi nhận + hiện diện (2-3 câu)\n"
    "text_2: văn bản 2 — khuyến khích kết nối hỗ trợ thực tế, khác text_1 (2-3 câu)\n"
    "voice_1: TTS grounding, hít thở (20-50 từ)\n"
    "voice_2: TTS hiện diện 'mình ở đây' (20-50 từ, khác voice_1)\n"
    "voice_3: TTS bước nhỏ tiếp theo (20-50 từ, khác voice_1 và voice_2)\n"
)


async def build_llm_crisis_messages(
    *,
    user_message: str,
    session_sos_count: int = 0,
    is_alone: bool = False,
    openai_api_key: str,
    model: str = "gpt-4o-mini",
    timeout_seconds: float = 5.0,
) -> tuple[list[str], list[str]]:
    """
    LLM-generated crisis messages.
    Returns (follow_up_texts[2], voice_scripts[3]).
    Falls back to rule-based templates on any failure.
    """
    user_ctx = f"Tin nhắn người dùng: {user_message[:300]}"
    if is_alone:
        user_ctx += "\n[Người dùng đang một mình]"
    if session_sos_count > 0:
        user_ctx += f"\n[Lần khủng hoảng thứ {session_sos_count + 1} trong session]"

    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=openai_api_key)
        resp = await asyncio.wait_for(
            client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": _LLM_CRISIS_SYSTEM},
                    {"role": "user", "content": user_ctx},
                ],
                response_format={"type": "json_object"},
                max_tokens=450,
                temperature=0.7,
            ),
            timeout=timeout_seconds,
        )
        data = _json.loads((resp.choices[0].message.content or "{}").strip())
        texts = [str(data.get("text_1", "")).strip(), str(data.get("text_2", "")).strip()]
        voices = [
            str(data.get("voice_1", "")).strip(),
            str(data.get("voice_2", "")).strip(),
            str(data.get("voice_3", "")).strip(),
        ]
        # Validate: non-empty, voices distinct, no forbidden patterns
        combined = " ".join(texts + voices)
        if (
            all(texts) and all(voices) and len(set(voices)) == 3
            and not any(p.search(combined) for p in _FORBIDDEN_CONTENT_PATTERNS)
        ):
            return texts, voices
    except Exception as exc:
        logger.warning("LLM crisis messages failed (fallback): %s", exc)

    fallback_texts = [
        "Mình nghe bạn, và mình đang ở đây với bạn ngay lúc này. Bạn không cần đối mặt với điều này một mình.",
        "Có những người ngoài đời cũng sẵn sàng lắng nghe bạn. Đường dây hỗ trợ luôn mở, bất cứ lúc nào.",
    ]
    return fallback_texts, _pick_three_voice_scripts(session_sos_count, is_alone)
```

---

### 3b — Cập nhật chat.py

**Files:** `backend/app/api/v1/routers/chat.py`

- [ ] **Step 5: Xóa enqueue_notification trong `_record_sos_side_effects()`**

Tìm và xóa block (khoảng lines 199–211):

```python
# XÓA toàn bộ:
# try:
#     from app.services.notification_service import enqueue_notification
#     enqueue_notification(db, user_id=user_id, event_type="crisis.detected", payload={...})
# except Exception:
#     pass
```

Giữ nguyên: `CrisisLog`, `AdminAuditLog`, `record_risk_inference`, `record_session_risk_snapshot`, `get_or_create_clinical_profile`.

- [ ] **Step 6: Mở rộng `_build_voice_intervention()` nhận list scripts**

Thay signature hiện tại (`assistant_reply_for_tts: str`) thành list-aware với single cooldown:

```python
# Thêm param mới (backward-compat: voice_scripts mặc định None):
def _build_voice_intervention(
    *,
    db: Session,
    user_id: str,
    session_id: str,
    assistant_reply_for_tts: str,          # giữ cho compat — dùng khi voice_scripts=None
    snapshot,
    trigger_reason: str,
    rolling_window_turns: int,
    delta_score: float,
    voice_scripts: list[str] | None = None, # NEW: nếu có, enqueue tất cả trước khi mark_cooldown
) -> dict:
    scripts_to_enqueue = voice_scripts if voice_scripts else [assistant_reply_for_tts]

    snapshot_dict = {
        "distress_score": snapshot.distress_score,
        "risk_level": snapshot.risk_level,
        "safety_tier": snapshot.safety_tier,
        "rolling_window_turns": rolling_window_turns,
        "delta_score": delta_score,
    }

    voice_jobs: list[dict] = []
    for script in scripts_to_enqueue:
        _verdict = _validate_tts_output(script, surface="tts")
        if _verdict.is_blocked:
            logger.warning("TTS script blocked user=%s: %s", user_id, _verdict.reason_codes)
            continue
        job = enqueue_voice_job(
            db,
            user_id=user_id,
            session_id=session_id,
            voice_script=script,
            trigger_reason=trigger_reason,
            trigger_snapshot=snapshot_dict,
        )
        voice_jobs.append(job)

    # Cooldown gọi một lần duy nhất sau khi enqueue tất cả
    mark_cooldown(user_id=user_id, session_id=session_id)

    primary = voice_jobs[0] if voice_jobs else {}
    return {
        "type": "proactive_voice",
        "trigger_reason": trigger_reason,
        "trigger_snapshot": snapshot_dict,
        "cooldown": {"active": False, "seconds_remaining": 0},
        "voice": primary,
        "voice_jobs": voice_jobs,                         # NEW: list of all jobs
        "voice_job_ids": [j.get("tts_job_id") for j in voice_jobs if j.get("tts_job_id")],  # NEW
        "voice_script": scripts_to_enqueue[0],
        "crisis_footer": {
            "show_once": True,
            "text": "Nếu bạn đang có ý định tự hại, hãy bấm để kết nối hỗ trợ khẩn cấp.",
            "hotline_cta": {"label": "Gọi hỗ trợ khẩn cấp", "action": "open_hotline_sheet"},
        },
    }
```

- [ ] **Step 7: Cập nhật SOS path (non-streaming) dùng LLM messages**

Trong non-streaming endpoint, thay đoạn ~lines 625–645:

```python
# Imports ở đầu file (thêm nếu chưa có):
# from app.services.crisis_intervention_planner import build_llm_crisis_messages

_is_alone = is_alone_signal(raw_text)
_settings = get_settings()

# Deterministic base plan
crisis_plan_base = build_fallback_plan(
    assistant_content,
    is_alone=_is_alone,
    session_sos_count=sos_count,
)

# Optional LLM enrichment (async, với timeout fallback)
try:
    _llm_texts, _llm_voices = await build_llm_crisis_messages(
        user_message=raw_text,
        session_sos_count=sos_count,
        is_alone=_is_alone,
        openai_api_key=_settings.openai_api_key,
    )
    crisis_plan = crisis_plan_base.model_copy(update={
        "follow_up_texts": _llm_texts,
        "voice_script": _llm_voices[0],
        "additional_voice_scripts": _llm_voices[1:],
        "source": "llm",
    })
except Exception as _exc:
    logger.warning("LLM crisis enrichment failed, using base plan: %s", _exc)
    crisis_plan = crisis_plan_base

data["crisis_plan"] = crisis_plan.model_dump()
data["voice_script"] = crisis_plan.voice_script

# Enqueue 3 TTS jobs qua extended _build_voice_intervention()
data["intervention"] = _build_voice_intervention(
    db=db,
    user_id=current_user.user_id,
    session_id=session.session_id,
    assistant_reply_for_tts=crisis_plan.voice_script,
    voice_scripts=crisis_plan.all_voice_scripts,  # truyền cả 3
    snapshot=snap,
    trigger_reason="sos_gate_forced",
    rolling_window_turns=1,
    delta_score=0.0,
)
```

Lặp lại tương tự cho streaming path (tìm SOS branch trong stream handler).

---

### 3c — Frontend: xóa CrisisStepper + thêm follow_up_texts + fix polling

**Files:** `frontend/src/components/chat/Chat.tsx`

- [ ] **Step 8: Cập nhật TypeScript types**

Tìm `type CrisisPlan = {...}` (~line 80), cập nhật:

```typescript
type CrisisPlan = {
    visible_text: string
    voice_script?: string
    additional_voice_scripts?: string[]   // NEW
    follow_up_texts?: string[]            // NEW: 2 counseling texts
    action_cards: CrisisActionCard[]
    follow_up_question?: string
    safety_reason_codes?: string[]
    source?: 'llm' | 'fallback_template'
}

// Trong ChatApiData, cập nhật intervention type:
type ProactiveVoiceIntervention = {
    type: string
    voice_job_ids?: string[]              // NEW
    voice_jobs?: Array<{ tts_job_id?: string | null; status?: string }> // NEW
    voice?: { status?: string; tts_job_id?: string | null; audio_url?: string | null }
    voice_script?: string
    crisis_footer?: { show_once: boolean; text: string; hotline_cta: { label: string; action: string } }
}
```

- [ ] **Step 9: Xóa `<CrisisStepper>` render (per user request)**

Tìm đoạn (~lines 1023–1029):

```tsx
// XÓA:
// {m.apiData?.sos_triggered && (
//     <CrisisStepper data={m.apiData} onAction={handleCrisisAction} onSend={...} />
// )}
```

Giữ lại hàm `function CrisisStepper()` trong file (có thể dùng lại sau), nhưng không render.

- [ ] **Step 10: Thêm `follow_up_texts` inline render**

Ở vị trí vừa xóa CrisisStepper, thêm:

```tsx
{m.apiData?.sos_triggered &&
    (m.apiData.crisis_plan?.follow_up_texts ?? []).map((msg, i) => (
        <div
            key={`followup-${i}`}
            className={`mt-2 rounded-2xl px-4 py-3 text-sm leading-relaxed border ${
                isDark
                    ? 'bg-theme-surface/80 text-theme-text-primary border-theme-border/30'
                    : 'bg-white/80 text-theme-text-primary border-stone-200/60'
            }`}
        >
            {msg}
        </div>
    ))
}
```

- [ ] **Step 11: Fix polling fallback — unblock input sau timeout**

Tìm `pollVoiceJob()` (~line 523). Sau vòng lặp retry, thêm ở cuối function (trước `return`):

```tsx
// Đảm bảo input không bị stuck sau khi polling hết attempts:
setSending(false)
setVoiceStatus('')
```

- [ ] **Step 12: Thêm sequential multi-voice playback**

Tìm đoạn `applyIntervention(data)` hoặc nơi SOS response được xử lý (gần `setSosActive(true)`). Thêm:

```tsx
const voiceJobIds: string[] =
    data.intervention?.voice_job_ids ??
    (data.intervention?.voice?.tts_job_id ? [data.intervention.voice.tts_job_id] : [])

if (voiceJobIds.length > 0) {
    void (async () => {
        for (const jobId of voiceJobIds) {
            await pollVoiceJob(jobId, undefined, 10)
            if (voiceJobIds.indexOf(jobId) < voiceJobIds.length - 1) {
                await new Promise(r => setTimeout(r, 800))
            }
        }
    })()
}
```

- [ ] **Step 13: Frontend build (typecheck)**

```bash
npm --prefix frontend run build
```

Expected: 0 TypeScript errors, build thành công

- [ ] **Step 14: Backend tests**

```bash
pytest backend/tests -q
```

Expected: All pass

- [ ] **Step 15: Manual smoke test**

```bash
npm --prefix frontend run dev
```

Test scenario — gửi "mình muốn chết":
- [ ] Không hiện CrisisStepper panel đỏ với action cards
- [ ] 2 counseling text messages xuất hiện dưới tin chính
- [ ] Voice indicator chạy tuần tự (3 lần)
- [ ] Nếu TTS fail/timeout (~15s), input không bị blocked — user vẫn gõ được
- [ ] `CrisisLog` row được tạo trong DB
- [ ] Không có `crisis.detected` event trong notification queue

- [ ] **Step 16: Commit (PR-C)**

```bash
git add backend/app/services/crisis_intervention_planner.py backend/app/api/v1/routers/chat.py frontend/src/components/chat/Chat.tsx
git commit -m "feat(sos): expand CrisisInterventionPlan with 3 LLM voice segments + 2 follow_up_texts; remove user notification; fix TTS polling unblock"
```

---

## Verification Checklist

| Check | Command | Kỳ vọng |
|-------|---------|---------|
| Backend tests toàn bộ | `pytest backend/tests -q` | All pass |
| Frontend build | `npm --prefix frontend run build` | 0 errors |
| Neo4j unavailable | Không set `NEO4J_URI` → chat bình thường | No error, analyst vẫn chạy |
| Neo4j available | Set `NEO4J_URI` → analyst log | `graph_context_used=True` xuất hiện |
| Memory tab | Chat 3+ turns → `GET /v1/chat/memory-cards` | Cards với `pending_user_review` |
| SOS manual | Send "mình muốn chết" | 2 text + 3 voice (tuần tự), không CrisisStepper |
| SOS audit | Check DB `crisis_log` | Row tồn tại, `severity_level="high"` |
| Notification removed | Check DB notification queue | Không có `crisis.detected` |
| TTS timeout | Kill TTS provider → trigger SOS | Input unblocked sau ~15s |
| LLM fallback | Unset `OPENAI_API_KEY` → trigger SOS | Fallback templates dùng, không crash |

---

## Safety Invariant Checklist

- [ ] `SafetyGate` vẫn chạy TRƯỚC mọi LLM call
- [ ] `CrisisLog` + `AdminAuditLog` vẫn ghi trong `_record_sos_side_effects()` (chỉ xóa notification event)
- [ ] `mask_pii()` vẫn gọi trước DB write trong SOS side effects
- [ ] LLM voices pass `_FORBIDDEN_CONTENT_PATTERNS` trước khi dùng
- [ ] Frontend không render `voice_script` như visible text
- [ ] `mark_cooldown()` chỉ gọi một lần sau khi enqueue tất cả TTS jobs
- [ ] Nếu LLM fail → fallback templates, không crash
