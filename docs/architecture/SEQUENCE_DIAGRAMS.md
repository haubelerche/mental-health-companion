# Sequence Diagrams - Serene.AI Runtime

## Context

Tài liệu này là bộ sequence diagram canonical cho các luồng agent chính của Serene.AI, được cập nhật theo `docs/PRD.md` phiên bản 7.2. Mục tiêu không phải là liệt kê mọi tương tác phụ trong sản phẩm, mà là mô tả chính xác các đường đi quyết định giữa **Friend Agent**, **Analyst Agent** và **Safety Agent** trong những workflow có rủi ro sản phẩm, an toàn và vận hành cao nhất.

Các sơ đồ dùng Mermaid để có thể render trực tiếp trong Markdown preview, GitHub, hoặc công cụ tài liệu nội bộ.

## Problem Statement Technical Deep-Dive

PRD xác định Serene.AI là một assistant duy nhất với ba vai trò runtime chính. Persona, reward, memory, dashboard, resource retrieval, TTS và notification là service/router/worker, không phải agent độc lập có danh tính riêng. Do đó, sequence diagram phải tránh hai sai lệch kiến trúc phổ biến: biến mọi service thành agent, hoặc cho phép Analyst/Safety viết trực tiếp ra UI ngoài contract được kiểm soát.

| Vai trò runtime | Mã triển khai tham chiếu | User-facing | Trách nhiệm kỹ thuật |
|---|---|---:|---|
| Friend Agent | `FriendNode` | Có | Tạo phản hồi hội thoại cuối cùng trong normal flow, áp dụng persona như style mode, dùng context đã được lọc an toàn. |
| Analyst Agent | `AnalystNode` | Không | Tạo `AnalystBundle` có cấu trúc từ dữ liệu được phép, evidence, confidence, caveat và action candidate. |
| Safety Agent | `SafetyFinalizer` | Có, qua payload kiểm soát | Xử lý high-risk/SOS, de-escalation, hotline/referral, crisis/audit log và crisis UI payload. |

Các invariant bắt buộc trong mọi sơ đồ:

1. `SafetyGate` chạy trước mọi LLM call hoặc advisor call.
2. High-risk/SOS bypass toàn bộ normal flow, bao gồm Analyst Agent và Friend Agent.
3. Analyst Agent không nói trực tiếp với user; mọi nội dung chat user-facing phải đi qua Friend Agent hoặc dashboard-safe sanitizer.
4. Advisor không tạo final response; advisor chỉ cung cấp evidence, candidate hoặc critique cho Analyst.
5. PostgreSQL/Supabase là source of truth; Redis, pgvector, RAG, outbox và worker chỉ là lớp hỗ trợ.
6. Frontend chỉ render state/payload từ backend; frontend không tự quyết định safety tier, crisis state, reward grant hoặc diagnosis-like interpretation.
7. Output sanitizer chặn diagnosis label, internal metadata leak, prompt-injection echo, unsafe medical advice và persona bypass.

## Strategic Recommendations

| # | Sơ đồ | Quyết định kiến trúc được khóa |
|---:|---|---:|
| 1 | Normal Chat - Friend Direct | Latency thấp, SafetyGate trước Friend, Analyst không bị gọi khi không cần. |
| 2 | Analyst-Assisted Chat | Analyst internal-only, Friend diễn đạt lại user-safe, advisor có provenance. |
| 3 | Crisis/SOS - Safety Agent | Safety bypass normal flow, crisis/audit log sync, UI nhận payload kiểm soát. |
| 4 | Dashboard Rollup Insight | Analyst tạo insight từ dữ liệu được phép, sanitizer bảo vệ dashboard khỏi raw risk/trauma/rationale. |
| 5 | Guided Screening With Safety Intercept | PHQ/GAD/DASS/MDQ/PCL là screening signal, không diagnosis; risk answer chuyển Safety. |
| 6 | End-to-End Agent Runtime | Toàn bộ vòng lặp routing, persistence, async worker, trace và degradation. |

---

## 1. Normal Chat - Friend Direct

Luồng này xử lý một turn chat thông thường khi không có dấu hiệu high-risk và không cần phân tích pattern sâu. Mục tiêu hệ thống là tối ưu latency, giữ giọng Serene nhất quán, đồng thời vẫn thực thi safety gate và output validation đầy đủ.

```mermaid
sequenceDiagram
    autonumber
    actor User as User
    participant UI as Frontend Chat UI
    participant API as ChatGateway API
    participant Store as PostgreSQL/Supabase
    participant Redis as Redis Cache
    participant Safety as SafetyGate
    participant Router as DistressRouter
    participant Persona as PersonaRouter
    participant Friend as Friend Agent (FriendNode)
    participant Validator as SafetyOutputValidator
    participant Outbox as Outbox Queue
    participant Trace as Langfuse

    User->>UI: Gửi message tiếng Việt
    UI->>API: POST /chat/messages
    API->>Store: Persist user message, request id, session id
    API->>Store: Load recent messages, consent, profile, safe memory refs
    API->>Redis: Load ephemeral session/cache if available
    API->>Safety: Classify risk before LLM/advisor
    Safety-->>API: risk=normal, reason_codes
    API->>Router: Decide route from intent, distress, context sufficiency
    Router-->>API: route=friend_direct
    API->>Persona: Resolve selected persona and safety fallback
    Persona-->>API: style_mode=dung_luong, dat_le, or hau_luong; strength
    API->>Friend: Generate user-facing response with safe context and persona style
    Friend-->>API: draft_response
    API->>Validator: Validate no diagnosis, unsafe advice, internal leak, persona drift
    Validator-->>API: approved_response
    API->>Store: Persist assistant message and safe metadata
    API->>Outbox: Enqueue memory/dashboard/TTS jobs as non-blocking side effects
    API->>Trace: Record route, safety decision, model, latency, token/cost, validator verdict
    API-->>UI: Stream/render approved_response
    UI-->>User: Hiển thị phản hồi của Serene
```

![Sơ đồ 1 — Normal Chat — Friend Direct](flow-chart-images/1.%20Normal%20Chat%20%E2%80%94%20Friend%20Direct.png)

**Kiểm soát sản phẩm:** Friend Agent là agent duy nhất tạo final response trong normal chat direct. Persona chỉ là style mode và bị SafetyGate/PersonaRouter override khi distress tăng.

---

## 2. Analyst-Assisted Chat - Analyst Internal, Friend User-Facing

Luồng này áp dụng khi user hỏi về pattern, dashboard context còn thiếu diễn giải, hoặc router nhận thấy câu trả lời trực tiếp sẽ tạo insight nông. Analyst Agent tạo bundle nội bộ; Friend Agent diễn đạt lại thành phản hồi an toàn, tự nhiên, không chẩn đoán.

```mermaid
sequenceDiagram
    autonumber
    actor User as User
    participant UI as Frontend Chat UI
    participant API as ChatGateway API
    participant Store as PostgreSQL/Supabase
    participant Safety as SafetyGate
    participant Router as DistressRouter
    participant AnalystCtx as AnalystContextLoader
    participant Advisor as Advisor Pool
    participant Analyst as Analyst Agent (AnalystNode)
    participant Sanitizer as AnalystSanitizer
    participant Persona as PersonaRouter
    participant Friend as Friend Agent (FriendNode)
    participant Validator as SafetyOutputValidator
    participant Trace as Langfuse

    User->>UI: Hỏi về pattern hoặc "mình đang bị sao?"
    UI->>API: POST /chat/messages
    API->>Store: Persist user message and load minimal turn context
    API->>Safety: Classify risk before Analyst/Friend
    Safety-->>API: risk=normal_or_elevated_non_crisis
    API->>Router: Evaluate need for insight support
    Router-->>API: route=analyst_assisted
    API->>AnalystCtx: Build permitted evidence pack
    AnalystCtx->>Store: Load chat summary, safe memory, mood, meal, sleep, coping, PHQ/GAD, DASS-21, MDQ, PCL-5
    AnalystCtx-->>API: sanitized_analysis_context
    API->>Advisor: Request only necessary advisors with no raw PII/crisis detail
    Advisor-->>API: evidence, candidate_actions, provenance, caveats
    API->>Analyst: Produce structured AnalystBundle
    Analyst-->>API: signals, hypotheses, confidence, evidence_refs, recommended_actions, caveats
    API->>Sanitizer: Convert AnalystBundle to Friend-safe context
    Sanitizer-->>API: friend_safe_themes, allowed_actions, non_diagnostic_caveats
    API->>Persona: Resolve safe style mode
    Persona-->>API: persona_style
    API->>Friend: Generate final response from friend-safe analyst context
    Friend-->>API: draft_response
    API->>Validator: Validate no diagnosis, no internal rationale, no raw risk detail
    Validator-->>API: approved_response
    API->>Store: Persist assistant message and analyst metadata references
    API->>Trace: Record advisors, evidence sources, route, cost, latency, sanitizer verdict
    API-->>UI: Return approved_response
    UI-->>User: Hiển thị phản hồi user-safe
```

![Sơ đồ 2 — Analyst-Assisted Chat](flow-chart-images/2.%20Analyst-Assisted%20Chat%20%E2%80%94%20Analyst%20internal,%20Friend%20user-facing.png)

**Kiểm soát sản phẩm:** Analyst Agent không được phép trả lời trực tiếp trong chat. Nếu `AnalystBundle` chứa diagnosis term, raw risk indicator hoặc rationale nội bộ, `AnalystSanitizer` phải loại bỏ trước khi Friend Agent nhận context.

---

## 3. Crisis/SOS - Safety Agent Bypasses Normal Flow

Luồng này xử lý self-harm, imminent danger, severe distress hoặc SOS explicit. Đây là đường đi ưu tiên reliability hơn personalization; mọi style vui, meme, Analyst và normal Friend response đều bị bypass.

```mermaid
sequenceDiagram
    autonumber
    actor User as User
    participant UI as Frontend Chat UI
    participant API as ChatGateway API
    participant Store as PostgreSQL/Supabase
    participant SafetyGate as SafetyGate
    participant SafetyAgent as Safety Agent (SafetyFinalizer)
    participant Referral as Referral/Hotline Service
    participant CrisisValidator as Crisis Validator
    participant Audit as Crisis and Audit Log Writer
    participant TTS as Voice/TTS Outbox
    participant Trace as Langfuse

    User->>UI: Gửi SOS/high-risk message
    UI->>API: POST /chat/messages
    API->>Store: Persist user message with protected safety metadata
    API->>SafetyGate: Classify risk synchronously before any LLM/advisor
    SafetyGate-->>API: risk=high_or_crisis, reason_codes
    Note over API: Bypass DistressRouter, Analyst Agent, Friend Agent, meme and normal persona style.
    API->>Referral: Load approved hotline/referral resources by locale and policy
    Referral-->>API: hotline/referral/action options
    API->>SafetyAgent: Build crisis payload contract
    SafetyAgent-->>API: visible_text, action_cards, optional_voice_script, follow_up_step, safety_metadata
    API->>CrisisValidator: Validate tone, no guilt/shame, no method detail, no fabricated hotline
    CrisisValidator-->>API: approved_crisis_payload or deterministic_fallback
    API->>Audit: Write crisis log and admin audit event
    Audit->>Store: Persist backend-only crisis/audit records
    opt voice grounding allowed
        API->>TTS: Enqueue voice_script with dedup key
    end
    API->>Trace: Record anonymized reason codes, route=crisis, fallback state, latency
    API-->>UI: Return crisis payload
    UI-->>User: Render crisis UI, action cards, hotline/referral, grounding step
```

![Sơ đồ 3 — Crisis SOS](flow-chart-images/3.%20Crisis%20-%20SOS%20%E2%80%94%20Safety%20Agent%20bypasses%20normal%20flow.png)

**Kiểm soát sản phẩm:** Safety Agent là agent user-facing duy nhất trong high-risk/SOS, nhưng chỉ thông qua payload kiểm soát. Crisis log/audit log là sync write bắt buộc; TTS là async và không được block phản hồi text.

---

## 4. Dashboard Rollup Insight - Analyst to Dashboard-Safe Layer

Luồng này chạy theo worker hoặc refresh dashboard. Analyst Agent tạo insight có evidence và confidence, nhưng dashboard chỉ được đọc dữ liệu đã sanitize; raw trauma detail, clinical note, risk inference và analyst rationale không được expose.

```mermaid
sequenceDiagram
    autonumber
    actor User as User
    participant UI as Dashboard UI
    participant API as Dashboard API
    participant Worker as DashboardInsightWorker
    participant Store as PostgreSQL/Supabase
    participant Vector as pgvector/RAG Store
    participant Safety as Safety/Privacy Sanitizer
    participant Advisor as Advisor Pool
    participant Analyst as Analyst Agent (AnalystNode)
    participant Trace as Langfuse

    Worker->>Store: Load permitted source events since last rollup
    Store-->>Worker: mood, meal, sleep, coping, memory cards, conversation summaries, screening scores
    Worker->>Vector: Retrieve relevant resource/context embeddings without raw PII
    Vector-->>Worker: grounded context with provenance
    Worker->>Safety: Remove raw risk, PII, raw trauma detail, clinical notes
    Safety-->>Worker: dashboard_analysis_context
    Worker->>Advisor: Request targeted advisors only when context requires them
    Advisor-->>Worker: evidence, resource candidates, caveats, provenance
    Worker->>Analyst: Generate structured insight bundle
    Analyst-->>Worker: signals, hypotheses, confidence, evidence_refs, suggested_actions, data_gaps
    Worker->>Safety: Sanitize for dashboard-safe exposure
    Safety-->>Worker: insight_cards, charts_metadata, suggested_actions, freshness, empty_state_if_needed
    Worker->>Store: Upsert dashboard_safe_insights and materialized chart data
    Worker->>Trace: Record advisor usage, sufficiency, evidence coverage, latency, cost

    User->>UI: Mở Dashboard
    UI->>API: GET /dashboard
    API->>Store: Read dashboard_safe_insights only
    Store-->>API: sanitized insights, charts, data freshness
    API-->>UI: Return dashboard payload
    UI-->>User: Render insight cards, trend, next step, data quality notice
```

![Sơ đồ 4 — Dashboard Rollup Insight](flow-chart-images/4.%20Dashboard%20Rollup%20Insight%20%E2%80%94%20Analyst%20%E2%86%92%20dashboard-safe%20layer.png)

**Kiểm soát sản phẩm:** Dashboard không được bịa insight khi thiếu dữ liệu. Khi evidence coverage thấp, worker phải materialize empty state hoặc data quality notice thay vì tạo kết luận giả.

---

## 5. Guided Screening With Safety Intercept

Luồng này bao phủ PHQ-9, GAD-7, DASS-21, MDQ và PCL-5. Các công cụ này chỉ là screening signal, không phải diagnosis; câu trả lời high-risk trong quá trình làm bài phải chuyển ngay sang Safety flow.

```mermaid
sequenceDiagram
    autonumber
    actor User as User
    participant UI as Screening UI
    participant API as Screening API
    participant Screening as ScreeningService
    participant SafetyGate as SafetyGate
    participant Store as PostgreSQL/Supabase
    participant SafetyAgent as Safety Agent (SafetyFinalizer)
    participant Dashboard as Dashboard Outbox
    participant Trace as Langfuse

    User->>UI: Chọn PHQ-9/GAD-7/DASS-21/MDQ/PCL-5
    UI->>API: POST /screening/sessions
    API->>Screening: Create session with consent/disclaimer
    Screening->>Store: Persist screening session and instrument type
    API-->>UI: Return first item and non-diagnostic disclaimer

    loop For each answer
        User->>UI: Trả lời item
        UI->>API: POST /screening/sessions/{id}/answers
        API->>Screening: Validate answer and update interim score
        Screening->>SafetyGate: Check safety implications before continuing
        alt high-risk answer detected
            SafetyGate-->>Screening: risk=high_or_crisis
            Screening->>Store: Persist answer, risk snapshot, protected metadata
            Screening->>SafetyAgent: Build crisis payload
            SafetyAgent-->>API: crisis_payload
            API-->>UI: Return safety_intercept payload
            UI-->>User: Render crisis/SOS support instead of normal screening result
        else no high-risk signal
            SafetyGate-->>Screening: risk=normal_or_elevated_non_crisis
            Screening->>Store: Persist answer and interim state
            API-->>UI: Return next item or completion state
        end
    end

    opt screening completed without safety intercept
        Screening->>Store: Persist score, severity/signal band, coverage, timestamp
        Screening->>Dashboard: Enqueue dashboard/profile update
        API->>Trace: Record instrument, completion, safety checks, non-diagnostic result policy
        API-->>UI: Return safe summary and suggested next step
        UI-->>User: Hiển thị kết quả như tín hiệu sàng lọc, không gắn nhãn bệnh
    end
```

![Sơ đồ 5 — Guided Screening](flow-chart-images/5.%20Guided%20Screening%20%E2%80%94%20screening%20with%20safety%20intercept.png)

**Kiểm soát sản phẩm:** MDQ/PCL-5 không được hiển thị như nhãn bipolar/PTSD; PCL-5 không expose raw trauma detail lên dashboard; điểm cao phải khuyến nghị tìm chuyên gia theo ngôn ngữ không chẩn đoán.

---

## 6. End-to-End Agent Runtime

Sơ đồ này tổng hợp quyết định routing chính cho một chat turn, bao gồm normal direct, analyst-assisted và crisis. Đây là bản tham chiếu nên dùng khi review code orchestration hoặc viết integration test.

```mermaid
sequenceDiagram
    autonumber
    actor User as User
    participant UI as Frontend
    participant API as Backend API
    participant Store as PostgreSQL/Supabase
    participant Safety as SafetyGate
    participant Router as DistressRouter
    participant Analyst as Analyst Agent (AnalystNode)
    participant Advisor as Advisor Pool
    participant Friend as Friend Agent (FriendNode)
    participant SafetyAgent as Safety Agent (SafetyFinalizer)
    participant Validator as Output/Crisis Validators
    participant Outbox as Outbox Workers
    participant Trace as Langfuse

    User->>UI: Send chat/check-in/screening-triggered message
    UI->>API: Submit request
    API->>Store: Sync write inbound event and load permitted context
    API->>Safety: Mandatory pre-route risk classification

    alt SafetyGate returns high-risk/SOS
        Safety-->>API: route=crisis, reason_codes
        API->>SafetyAgent: Generate controlled crisis payload
        SafetyAgent-->>API: crisis_payload
        API->>Validator: Validate crisis contract and fallback if unsafe
        Validator-->>API: approved_crisis_payload
        API->>Store: Persist assistant safety response, crisis log, audit log
        API->>Outbox: Optional TTS/follow-up jobs only after sync safety writes
        API->>Trace: Record route=crisis without raw PII
        API-->>UI: Return crisis UI payload
    else SafetyGate returns normal/elevated non-crisis
        Safety-->>API: route_candidate=normal
        API->>Router: Decide friend_direct vs analyst_assisted
        alt route=analyst_assisted
            Router-->>API: analyst_assisted
            API->>Advisor: Fetch advisor evidence with sanitized input
            Advisor-->>API: evidence and provenance
            API->>Analyst: Produce internal AnalystBundle
            Analyst-->>API: structured insight bundle
            API->>Validator: Sanitize AnalystBundle for Friend context
            Validator-->>API: friend_safe_context
            API->>Friend: Generate final user-facing response
            Friend-->>API: draft_response
        else route=friend_direct
            Router-->>API: friend_direct
            API->>Friend: Generate final user-facing response
            Friend-->>API: draft_response
        end
        API->>Validator: Validate final response
        Validator-->>API: approved_response or safe_fallback
        API->>Store: Persist assistant message and safe metadata
        API->>Outbox: Enqueue memory, dashboard, reward, TTS, notification jobs
        API->>Trace: Record route, model, advisor usage, validation, latency, token/cost
        API-->>UI: Return approved response
    end

    UI-->>User: Render backend-provided state only
```

![Sơ đồ 6 — End-to-End Agent Runtime](flow-chart-images/6.%20End-to-End%20Agent%20Runtime%20%E2%80%94%20canonical%20routing.png)

**Kiểm soát sản phẩm:** Frontend không tự suy luận route, safety tier hoặc crisis state. Mọi quyết định sản phẩm nhạy cảm nằm ở backend và được trace bằng Langfuse với dữ liệu đã ẩn danh.

---

## Verification Checklist

| Gate | Điều kiện đạt |
|---|---|
| Safety-first | Mọi sơ đồ có `SafetyGate` trước LLM/advisor hoặc safety intercept trong screening. |
| Friend boundary | Friend Agent chỉ nhận context an toàn và là final writer trong normal chat. |
| Analyst boundary | Analyst Agent không có đường trả lời trực tiếp tới UI/User. |
| Safety boundary | High-risk/SOS bypass Router, Analyst và Friend; Safety Agent trả payload kiểm soát. |
| Data architecture | PostgreSQL/Supabase là source of truth; outbox/worker là async side effect. |
| Dashboard privacy | Dashboard chỉ đọc `dashboard_safe_insights`, không đọc raw risk, trauma detail hoặc analyst rationale. |
| Non-diagnosis | Screening và insight đều dùng ngôn ngữ screening signal, caveat và suggested action. |
| Observability | Các luồng agentic đều ghi Langfuse trace với route, reason code, model/cost/latency và validator verdict. |
