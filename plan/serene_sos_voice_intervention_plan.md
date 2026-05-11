# Codex Implementation Plan — Refactor SOS Voice Intervention Flow for Serene

## 0. Mục tiêu tổng quát

Refactor luồng SOS/critical distress của Serene để giải quyết tận gốc các vấn đề hiện tại:

1. Voice message không được đọc lại nguyên văn text message.
2. Không tạo nhiều file TTS giống nhau khi người dùng rơi vào SOS nhiều lần.
3. Khi distress/risk cao, hệ thống phải tạo voice intervention theo ngữ cảnh hội thoại hiện tại, có tuân thủ persona, nhưng vẫn đi qua safety validation.
4. UI khủng hoảng không được dồn toàn bộ nội dung vào một card chữ dài; cần chuyển sang stepper/action-based intervention.
5. Distress scoring phải có debug trace rõ ràng: reason codes, keyword hits, current score, rolling score, trend boost, final SOS decision.

Nguyên tắc an toàn:

- Deterministic SOS gate vẫn giữ quyền quyết định kích hoạt SOS.
- LLM chỉ được dùng để viết `CrisisInterventionPlan` sau khi SOS gate đã kích hoạt.
- LLM không được tự quyết định hotline, không được chẩn đoán, không được đưa nội dung gây nguy hiểm, không được mô tả chi tiết hành vi tự hại, và không được bịa tài nguyên hỗ trợ.

---

## 1. Files cần sửa

### Backend

- `app/services/sos_handler.py`
- `app/services/proactive_voice.py`
- `app/services/langgraph_chat.py`, nếu cần reuse persona config hoặc expose helper
- `app/api/routes/chat.py`, hoặc file router tương ứng đang chứa `/chat/message` và `/chat/message/stream`
- `app/db/models.py`, nếu cần thêm fields hoặc model cache riêng
- `app/core/config.py`, nếu cần thêm setting

### Frontend

- `src/components/chat/Chat.tsx`
- Có thể tạo component mới:
  - `src/components/crisis/CrisisStepper.tsx`
  - `src/components/crisis/CrisisActionCard.tsx`
  - `src/components/crisis/BreathingTimer.tsx`

### Tests

- `tests/services/test_sos_handler.py`
- `tests/services/test_crisis_intervention_planner.py`
- `tests/services/test_proactive_voice.py`
- `tests/api/test_chat_sos_flow.py`
- Frontend tests nếu project đang có setup test.

---

## 2. Backend Phase 1 — Tách `visible_text` và `voice_script`

### 2.1. Tạo service mới

Create file:

```text
app/services/crisis_intervention_planner.py
```

Implement các Pydantic models:

```python
from typing import Literal
from pydantic import BaseModel, Field

class CrisisActionCard(BaseModel):
    id: str
    type: Literal[
        "voice_grounding",
        "breathing_timer",
        "trusted_contact",
        "hotline",
        "clinic_map",
        "video_grounding",
        "continue_chat",
    ]
    title: str = Field(max_length=80)
    description: str = Field(max_length=180)
    action: str
    route: str | None = None
    priority: int = Field(ge=0, le=100)

class CrisisInterventionPlan(BaseModel):
    visible_text: str = Field(min_length=1, max_length=500)
    voice_script: str = Field(min_length=80, max_length=1200)
    action_cards: list[CrisisActionCard] = Field(default_factory=list, max_length=3)
    follow_up_question: str = Field(min_length=1, max_length=180)
    safety_reason_codes: list[str] = Field(default_factory=list, max_length=8)
    should_enqueue_voice: bool = True
    source: Literal["llm", "fallback_template"] = "fallback_template"
```

### 2.2. Implement fallback deterministic plan

Implement:

```python
def build_fallback_crisis_plan(
    *,
    user_message: str,
    recent_messages: list[dict],
    persona_id: str,
    distress_score: float,
    risk_level: int,
    safety_tier: str,
    reason_codes: list[str] | None = None,
) -> CrisisInterventionPlan:
    ...
```

Yêu cầu:

- `visible_text` ngắn, khoảng 1-3 câu.
- `voice_script` không được giống `visible_text`.
- `voice_script` là hướng dẫn bằng giọng nói, có nhịp, tập trung vào một hành động cụ thể.
- `action_cards` chỉ lấy từ danh sách action đã duyệt.
- Không đưa hotline hardcode do LLM tạo. Hotline phải đi từ curated source hiện có, ví dụ `hotline_cards_sos()`.

### 2.3. Implement LLM Crisis Planner

Implement:

```python
def build_crisis_intervention_plan(
    *,
    user_message: str,
    recent_messages: list[dict],
    persona_id: str,
    persona_config: dict,
    distress_score: float,
    risk_level: int,
    safety_tier: str,
    reason_codes: list[str],
    session_sos_count: int,
) -> CrisisInterventionPlan:
    ...
```

Logic:

1. Nếu thiếu API key hoặc LLM fail, dùng fallback.
2. Nếu LLM trả invalid JSON, dùng fallback.
3. Nếu safety validator fail, dùng fallback.
4. Nếu LLM output hợp lệ, trả plan với `source="llm"`.

Prompt requirement:

```text
You are generating a crisis-support intervention plan for a Vietnamese mental-health support app.

Input:
- user_message
- recent_messages
- persona_config
- distress_score
- risk_level
- safety_tier
- reason_codes
- session_sos_count
- available_action_tools

Return strict JSON only.

Rules:
- Do not diagnose.
- Do not mention probabilities of mental disorders.
- Do not describe harmful methods.
- Do not invent hotline numbers.
- visible_text and voice_script must not be identical.
- visible_text must be short and immediately reassuring.
- voice_script must guide one concrete action step.
- Keep the selected persona's tone, but safety rules override persona.
- Prefer action over explanation.
```

---

## 3. Backend Phase 2 — Safety validator cho `CrisisInterventionPlan`

Trong `crisis_intervention_planner.py`, implement:

```python
def validate_crisis_plan(plan: CrisisInterventionPlan) -> CrisisInterventionPlan:
    ...
```

Validation rules:

1. `visible_text` không quá 500 characters.
2. `voice_script` nằm trong khoảng 80-1200 characters.
3. Similarity giữa `visible_text` và `voice_script` phải thấp hơn threshold, ví dụ `< 0.65`.
4. `action_cards` tối đa 3.
5. `action` chỉ nằm trong allowlist:
   - `play_voice_grounding`
   - `start_breathing_timer`
   - `open_hotline_sheet`
   - `open_clinic_map`
   - `open_grounding_video`
   - `continue_chat`
6. `route`, nếu có, phải bắt đầu bằng `/serene/`.
7. Không cho phép forbidden content patterns trong output.
8. Không cho phép LLM bịa số điện thoại trong `visible_text` hoặc `voice_script`.

Acceptance criteria:

- LLM output lỗi không làm crash request.
- LLM output nguy hiểm hoặc sai schema bị thay bằng fallback.
- Có log rõ:

```text
crisis_plan_source=llm|fallback_template
validator_status=passed|failed
```

---

## 4. Backend Phase 3 — Sửa `chat.py` SOS branch

Hiện tại SOS branch đang có dạng:

```python
assistant_content = assistant_text_for_sos(raw_text, sos_count)
data = build_sos_chat_response_data(..., assistant_text=assistant_content)
data["intervention"] = _build_voice_intervention(
    assistant_reply_for_tts=assistant_content,
    ...
)
```

Refactor thành:

```python
persona_id = _active_persona_id(db, current_user.user_id)
persona_config = get_persona_config_safely(persona_id)

score_debug = decide_sos_debug(raw_text, recent_user_messages=previous_user_messages)
sos = score_debug.sos_triggered
distress0 = score_debug.distress_score

if sos:
    snap = snapshot_for_sos(distress0)
    sos_count = ...

    plan = build_crisis_intervention_plan(
        user_message=raw_text,
        recent_messages=ctx.recent_messages,
        persona_id=persona_id,
        persona_config=persona_config,
        distress_score=distress0,
        risk_level=snap.risk_level,
        safety_tier=snap.safety_tier,
        reason_codes=score_debug.reason_codes,
        session_sos_count=sos_count,
    )

    assistant_content = plan.visible_text

    # Save assistant message with content=assistant_content

    data = build_sos_chat_response_data(
        session.session_id,
        snap,
        assistant_text=plan.visible_text,
    )

    data["crisis_plan"] = plan.model_dump()
    data["scoring_debug"] = score_debug.model_dump()

    data["intervention"] = _build_voice_intervention_from_script(
        db=db,
        user_id=current_user.user_id,
        session_id=session.session_id,
        voice_script=plan.voice_script,
        snapshot=snap,
        trigger_reason="sos_gate_forced",
        rolling_window_turns=score_debug.rolling_window_turns,
        delta_score=score_debug.delta_score,
        cooldown_is_active=cooldown_is_active,
        cooldown_seconds=cooldown_seconds,
    )

    return ok(data)
```

Important:

- Đổi `_build_voice_intervention` để nhận explicit `voice_script`, không nhận `assistant_reply_for_tts`.
- Không dùng `assistant_text_for_sos` làm source chính nữa. Có thể giữ lại function này cho backward compatibility hoặc fallback test cũ.
- Áp dụng tương tự cho streaming endpoint `/chat/message/stream` nếu file có nhánh SOS riêng.

Acceptance criteria:

- Text assistant hiển thị ngay.
- Voice card dùng `plan.voice_script`, không đọc lại `plan.visible_text`.
- Payload có:
  - `crisis_plan.visible_text`
  - `crisis_plan.voice_script`
  - `crisis_plan.action_cards`
- Persona được truyền vào Crisis Planner.

---

## 5. Backend Phase 4 — TTS deduplication và cache

Trong `proactive_voice.py`, thêm helper:

```python
import hashlib
import re

def normalize_tts_script(text: str) -> str:
    text = text or ""
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text

def build_voice_cache_key(
    *,
    voice_script: str,
    provider: str,
    voice_id: str | None,
    locale: str = "vi-VN",
    speech_rate: str | None = None,
) -> str:
    raw = "|".join([
        normalize_tts_script(voice_script),
        provider or "",
        voice_id or "",
        locale or "",
        speech_rate or "",
    ])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
```

Update `enqueue_voice_job` hoặc tạo function mới:

```python
def get_or_enqueue_voice_job(
    db: Session,
    *,
    user_id: str,
    session_id: str,
    voice_script: str,
    trigger_reason: str,
    trigger_snapshot: dict[str, Any],
) -> dict[str, Any]:
    ...
```

Algorithm:

1. Build `script_hash`.
2. Search recent `SyncOutbox` rows with:
   - `event_type == VOICE_JOB_EVENT_TYPE`
   - same `user_id`
   - same `session_id`
   - same `script_hash`
   - status in `done`, `pending`, `processing`
   - recent within configurable TTL, e.g. 24h.
3. If found:
   - Return existing `tts_job_id`.
   - Do not create new job.
   - Add field `cache_hit: true`.
4. If not found:
   - Create new outbox row.
   - Store `script_hash` inside payload.
   - Return `cache_hit: false`.

Payload should include:

```json
{
  "voice_script": "...",
  "voice_script_hash": "...",
  "provider": "...",
  "voice_id": "...",
  "trigger_reason": "...",
  "trigger_snapshot": {}
}
```

Update all callers:

- Non-SOS proactive voice.
- SOS voice intervention.

Acceptance criteria:

- Same script in same session no longer creates multiple TTS files.
- Queued/processing job is reused instead of enqueuing another job.
- Done job is reused and returns ready audio when available.
- Logs include:

```text
voice_cache_hit=true|false
```

---

## 6. Backend Phase 5 — Distress scoring debug

Trong `sos_handler.py`, thêm model:

```python
from pydantic import BaseModel

class DistressScoreDebug(BaseModel):
    sos_triggered: bool
    distress_score: float
    harm_risk_score: float | None = None
    current_turn_score: float
    rolling_score: float
    trend_boost: float
    delta_score: float
    rolling_window_turns: int
    reason_codes: list[str]
    keyword_hits: list[str]
    safety_tier_hint: str | None = None
```

Implement:

```python
def decide_sos_debug(
    message: str,
    recent_user_messages: list[str] | None = None,
) -> DistressScoreDebug:
    ...
```

Refactor existing `decide_sos(...)` to call `decide_sos_debug(...)` for backward compatibility:

```python
def decide_sos(message: str, recent_user_messages: list[str] | None = None) -> tuple[bool, float]:
    dbg = decide_sos_debug(message, recent_user_messages)
    return dbg.sos_triggered, dbg.distress_score
```

Debug requirements:

- Không chỉ trả một số score.
- Phải có reason codes, ví dụ:
  - `explicit_high_risk_keyword`
  - `violence_risk_keyword`
  - `rolling_distress_escalation`
  - `severe_history_count`
  - `critical_threshold_crossed`
  - `elevated_but_not_sos`
- `keyword_hits` phải lưu keyword normalized hoặc category; không cần lưu nguyên văn nhạy cảm nếu có nguy cơ logging quá mức.
- Nên tách dần:
  - `distress_score`: mức căng thẳng cảm xúc.
  - `harm_risk_score`: mức rủi ro an toàn.

Acceptance criteria:

- Response debug mode frontend có thể hiển thị scoring debug.
- Unit tests cover:
  - false positive
  - slang
  - normal sadness
  - explicit high-risk
  - multi-turn escalation
  - de-escalation

---

## 7. Frontend Phase 1 — Type update

Trong `Chat.tsx`, update type:

```ts
type CrisisActionCard = {
  id: string
  type:
    | 'voice_grounding'
    | 'breathing_timer'
    | 'trusted_contact'
    | 'hotline'
    | 'clinic_map'
    | 'video_grounding'
    | 'continue_chat'
  title: string
  description: string
  action: string
  route?: string | null
  priority: number
}

type CrisisPlan = {
  visible_text: string
  voice_script?: string
  action_cards: CrisisActionCard[]
  follow_up_question?: string
  safety_reason_codes?: string[]
  should_enqueue_voice?: boolean
  source?: 'llm' | 'fallback_template'
}

type ScoringDebug = {
  sos_triggered: boolean
  distress_score: number
  harm_risk_score?: number | null
  current_turn_score: number
  rolling_score: number
  trend_boost: number
  delta_score: number
  rolling_window_turns: number
  reason_codes: string[]
  keyword_hits: string[]
  safety_tier_hint?: string | null
}
```

Add to `ChatApiData`:

```ts
crisis_plan?: CrisisPlan
scoring_debug?: ScoringDebug
```

---

## 8. Frontend Phase 2 — Replace `CrisisPanel` bằng `CrisisStepper`

Current `CrisisPanel` đang render:

- assistant strategy badges
- micro_actions
- hotline cards
- tất cả trong một card

Replace bằng action-oriented component:

```tsx
function CrisisStepper({
  data,
  onPlayVoice,
  onAction,
}: {
  data: ChatApiData
  onPlayVoice?: () => void
  onAction: (card: CrisisActionCard) => void
}) {
  ...
}
```

UI structure:

### Step 1: Voice grounding

- Show voice card first if available.
- If voice still queued: show loading state, for example “Đang chuẩn bị hướng dẫn thoại...”
- If voice failed: show fallback text action.

### Step 2: Action cards

- Render tối đa 3 cards from `crisis_plan.action_cards`.
- Cards must be button-like, clear CTA.

### Step 3: Follow-up

- One short question from `crisis_plan.follow_up_question`.
- Optional quick replies.

Important:

- Không render `micro_actions` cũ nếu `crisis_plan.action_cards` tồn tại.
- Hotline should be a card/action, not a long list occupying the whole panel.
- Voice must be prominent, because the crisis intervention should be action-based, not text-heavy.

Acceptance criteria:

- SOS panel không còn là một block chữ dài.
- User nhìn thấy first actionable step within one screen.
- Voice loading state rõ ràng.
- Action cards are clickable.

---

## 9. Frontend Phase 3 — Action handlers

Implement action handler:

```ts
function handleCrisisAction(card: CrisisActionCard) {
  switch (card.action) {
    case 'play_voice_grounding':
      // play current message voice if ready
      break
    case 'start_breathing_timer':
      // open breathing timer modal/component
      break
    case 'open_hotline_sheet':
      // open hotline sheet
      break
    case 'open_clinic_map':
      // navigate route or open clinic map
      break
    case 'open_grounding_video':
      // navigate to resource route
      break
    case 'continue_chat':
      // focus input or send quick reply
      break
    default:
      // ignore safely, optionally log in dev mode
      break
  }
}
```

Acceptance criteria:

- Each action has deterministic frontend behavior.
- Unknown action is ignored safely with toast/log.
- No route outside `/serene/`.

---

## 10. Product behavior rules

Implement these behavior rules:

1. `visible_text` appears immediately.
2. `voice_script` is separate and should not repeat `visible_text`.
3. If cooldown is active:
   - Do not enqueue new TTS unless risk increased materially.
   - Return cooldown metadata.
4. If same voice script already exists:
   - Reuse existing TTS job/audio.
5. If LLM fails:
   - Fallback template still produces a valid, safe `CrisisInterventionPlan`.
6. If TTS fails:
   - UI still shows action cards and visible text.
7. If SOS repeats in same session:
   - LLM/fallback should vary the intervention step instead of repeating the same copy.
   - Use `session_sos_count` and recent messages to avoid repeated wording.

---

## 11. Tests to implement

### 11.1. `test_crisis_intervention_planner.py`

Test cases:

- Returns valid fallback plan.
- LLM invalid JSON falls back.
- LLM unsafe output falls back.
- `visible_text` and `voice_script` are not identical.
- Persona id affects tone field or wording, but does not override safety constraints.
- Action cards are within allowlist.

### 11.2. `test_sos_handler.py`

Test cases:

- `decide_sos_debug` returns reason codes.
- Normal sadness is not automatically SOS.
- High-risk explicit wording triggers SOS.
- Multi-turn escalation increases score.
- De-escalation does not remain stuck forever at critical level.
- Debug payload includes current, rolling, trend, reason_codes.

### 11.3. `test_proactive_voice.py`

Test cases:

- Same script returns same queued job.
- Same script after done returns ready job.
- Different script creates new job.
- Cooldown prevents duplicate voice creation.
- Payload includes `voice_script_hash`.

### 11.4. `test_chat_sos_flow.py`

Test cases:

- SOS response contains `crisis_plan`.
- `assistant_text == crisis_plan.visible_text`.
- `intervention.voice_script == crisis_plan.voice_script`.
- `visible_text != voice_script`.
- `routing_history` includes `sos_handler`.
- `scoring_debug` exists in response.

### 11.5. Frontend tests/manual checks

Manual test:

1. Send a normal supportive message.
2. Send a high distress message.
3. Confirm:
   - Text appears immediately.
   - Voice card appears after queued/processing.
   - Voice is not identical to text.
   - Crisis UI shows stepper/action cards.
   - No more than one TTS job is generated for same script.
   - Debug panel shows distress reason codes.

---

## 12. Definition of Done

The task is complete only when all conditions below pass:

1. SOS text and voice are separated:
   - `visible_text` is short.
   - `voice_script` is action-oriented and context-aware.
   - They are not identical.

2. Persona is preserved:
   - Crisis Planner receives active persona.
   - Persona affects wording lightly.
   - Safety rules always override persona.

3. TTS dedup works:
   - Repeated same script does not generate new `tts_*.mp3`.
   - Existing queued/processing/done job is reused.

4. UI is action-based:
   - `CrisisPanel` is replaced or substantially refactored into `CrisisStepper`.
   - User sees voice/action cards instead of a large static SOS block.

5. Distress scoring is auditable:
   - `decide_sos_debug` exists.
   - API response includes scoring debug in debug/dev mode.
   - Logs include reason codes.

6. Backward compatibility:
   - Existing non-SOS chat flow still works.
   - Existing voice polling still works.
   - Existing `assistant_text_for_sos` can remain as fallback, but not as the main SOS generation path.

---

## 13. Suggested implementation order

1. Add `crisis_intervention_planner.py` with schema, fallback plan, validator.
2. Add `decide_sos_debug` while preserving `decide_sos`.
3. Refactor `chat.py` SOS branch to use `CrisisInterventionPlan`.
4. Rename/refactor `_build_voice_intervention` to accept explicit `voice_script`.
5. Add TTS script hash dedup in `proactive_voice.py`.
6. Update frontend types in `Chat.tsx`.
7. Replace `CrisisPanel` with `CrisisStepper`.
8. Add tests.
9. Run full backend and frontend checks.
10. Manually verify SOS flow and duplicate TTS behavior.

---

## 14. Expected final architecture

```text
User message
  -> decide_sos_debug
  -> if non-SOS:
       LangGraph Analyst/Friend flow
  -> if SOS:
       deterministic SOS gate
       -> persona resolver
       -> CrisisInterventionPlanner
       -> CrisisPlan validator
       -> save visible_text as assistant message
       -> enqueue/reuse TTS for voice_script
       -> return crisis_plan + intervention + scoring_debug
       -> frontend CrisisStepper renders voice/action flow
```

---

## 15. Key instruction for Codex

Do not solve this by adding more hardcoded SOS text variants.

The correct solution is an architectural refactor from:

```text
SOS static message
```

to:

```text
validated crisis intervention plan
```

The new plan object must contain:

```text
visible_text
voice_script
action_cards
scoring_debug
```

This is the core contract between backend and frontend.
