# PRD.md — Serene AI Mental-Health Companion

**Document type:** Product + Backend + Runtime Requirements Document  
**Version:** 6.2 — Technical Sync (2026-05-14)  
**Status:** MVP architecture specification  
**Supersedes:** `BACKEND_PLAN.md`, `BUILDING-PLAN-AGENT-SPECS.md`  
**Target stack:** React, FastAPI, LangGraph-style orchestration, PostgreSQL/pgvector, Redis, Neo4j, Celery/Outbox, OpenAI-compatible LLMs  
**Default user-facing language:** Vietnamese

---

<a id="reader-summary"></a>
## Reader Summary

**The current architecture is lightweight multi-agent: 3 main agents + supporting services/workers.** Do not implement five independent agents, and do not turn personas into separate agents.

| Group | Agent / role (product) | Orchestration id (code) | Directly talks to user? | Responsibility |
|---|---|---|---:|---|
| Agent 1 | Serene Conversation Agent | `FriendNode` | Yes | Responds in the normal flow, preserves one stable Serene identity, and applies personas as style modes. |
| Agent 2 | Internal Analyst Agent | `AnalystNode` | No | Analyzes patterns, signs, triggers, coping/resource context; outputs only structured `AnalystBundle`. |
| Agent 3 | Safety Agent | `SafetyFinalizer` | Yes, through controlled payload | Handles high-risk turns, returns de-escalation payload, micro-actions, referral/hotline, crisis/audit logs. |
| Not agents | Screening/resource/referral/persona/memory/dashboard/TTS/Neo4j sync | `Service`, `Router`, `Worker` | No | Backend support tools with no separate identity and no direct user-facing voice. |

**Core flow:** `SafetyGate` always runs first. If high-risk, the **Safety Agent** (`SafetyFinalizer`) controls the whole turn. If not high-risk, the request goes to the **Serene Conversation Agent** (`FriendNode`) directly or through the **Internal Analyst Agent** (`AnalystNode`) when pattern insight is needed.

**Naming (agents vs orchestration identifiers):** **Serene Conversation Agent**, **Internal Analyst Agent**, and **Safety Agent** are the product names for the three runtime roles that may invoke an LLM or return a user-visible outcome. In code, traces, and `RuntimeState`, the same roles appear as orchestration identifiers `FriendNode`, `AnalystNode`, and `SafetyFinalizer`. This document uses the agent name in prose where clarity matters, followed by the identifier in parentheses when both are relevant. The word **node** is not used to mean “agent”; Neo4j uses graph nodes (for example `:MemoryNode`) only in the graph-model sense.
Runtime naming reference: `docs/GLOSSARY_RUNTIME.md`.

**Sections that must not be skipped:** §3 invariants, §7 architecture, §8 runtime flow, §11 safety, §12 Neo4j boundaries, §15 privacy/security, §16 degradation, §21 acceptance criteria.

<a id="agent-reading-protocol"></a>
## Agent Reading Protocol

1. **Do not start coding after reading only the beginning.** Before any backend/chat/safety/data change, scan the Table of Contents and Anti-Context-Rot Section Map.
2. **For chat/routing tasks:** read §3, §4, §7, §8, §9, §10, §11, §21.
3. **For graph/data/memory tasks:** read §12, §13, §15, §16, §21.
4. **For API/frontend contract tasks:** read §6, §8, §10, §14, §21.
5. **For persona/reward/TTS tasks:** read §4, §6.8, §10, §11, §14, §16, §21.
6. **For high-risk/SOS/crisis tasks:** read §11 first, then the relevant implementation sections; high-risk turns must not enter normal flow.
7. **Before merge:** check §21 Non-Negotiable Acceptance Criteria.


## Table of Contents

- [Reader Summary](#reader-summary)
- [Agent Reading Protocol](#agent-reading-protocol)
- [Anti-Context-Rot Section Map](#anti-context-rot-map)
- [§0. Document Purpose](#sec-0)
- [§1. Executive Summary](#sec-1)
- [§2. Product Thesis](#sec-2)
- [§3. Non-Negotiable Product and Architecture Invariants](#sec-3)
- [§4. Strategic Product Decisions](#sec-4)
- [§5. Target Users](#sec-5)
- [§6. Core Product Requirements](#sec-6)
- [§7. Canonical System Architecture](#sec-7)
- [§8. Runtime Flow](#sec-8)
- [§9. Runtime State Contract](#sec-9)
- [§10. Component Contracts](#sec-10)
- [§11. Safety Requirements](#sec-11)
- [§12. Neo4j Knowledge Graph Role](#sec-12)
- [§13. Data Architecture](#sec-13)
- [§14. API Plan](#sec-14)
- [§15. Memory, Privacy, Security](#sec-15)
- [§16. Observability and Graceful Degradation](#sec-16)
- [§17. Success Metrics](#sec-17)
- [§18. MVP Scope](#sec-18)
- [§19. Implementation Phases](#sec-19)
- [§20. Open Product and Legal Decisions](#sec-20)
- [§21. Non-Negotiable Acceptance Criteria](#sec-21)

---

<a id="anti-context-rot-map"></a>
## Anti-Context-Rot Section Map

This map helps an agent understand the whole document before editing code, instead of reading only the beginning and missing safety/data/acceptance sections in the middle or end.

| Section | Purpose | Mandatory read condition |
|---|---|---|
| §0. Document Purpose | Defines this file as the only canonical PRD and sets conflict-resolution priority after older backend/spec files are removed. | Before editing code, verify that no older document overrides this PRD. |
| §1. Executive Summary | Summarizes Serene as a privacy-first companion, not a diagnostic or clinical replacement, with one stable identity. | Any UX/chat change must preserve one coherent Serene identity. |
| §2. Product Thesis | States the product thesis: users need safe expression, pattern understanding, and one small next step, not diagnosis. | If a feature does not support this loop, move it to backlog instead of MVP. |
| §3. Non-Negotiable Product and Architecture Invariants | Lists non-negotiable invariants for identity, persona, safety, data, async work, and validation. | Use this as the mandatory checklist before major PRs. |
| §4. Strategic Product Decisions | Locks strategic decisions: 3 main agents in practical terms, personas are not agents, and Neo4j is not a diagnosis engine. | When asked for “multi-agent,” follow the top agent table; do not create five independent bots. |
| §5. Target Users | Defines primary and secondary users and their real product needs. | Do not add heavy clinical intake if it increases first-chat friction. |
| §6. Core Product Requirements | Defines core product requirements: onboarding, chat, pattern insight, screening, coping, safety pathway, dashboard, persona/reward/memory/TTS. | For each feature, check the acceptance criteria in the relevant subsection. |
| §7. Canonical System Architecture | Defines the canonical runtime architecture and the rejected architecture. | Do not implement Conversation/Screener/Resource/Escalation/SafetyGuardrail as autonomous LLM agents. |
| §8. Runtime Flow | Describes the three runtime flows: normal chat, pattern insight, and high-risk handling. | Always verify that high-risk turns bypass normal flow. |
| §9. Runtime State Contract | Defines RuntimeState and mutation permissions for each component. | Do not pass free-form dictionaries or let async workers mutate in-request state after response return. |
| §10. Component Contracts | Defines short contracts for each component/service/worker and required fallback behavior. | When assigning coding work, scope it to the relevant component contract only. |
| §11. Safety Requirements | Defines SafetyGate output, risk levels, and the required Safety Agent (`SafetyFinalizer`) payload. | This section is mandatory when changing chat, safety, TTS, referral, or routing. |
| §12. Neo4j Knowledge Graph Role | Defines Neo4j as graph reasoning for patterns/resources, not raw sensitive storage. | Do not create user-has-disorder edges or write raw transcripts to the graph. |
| §13. Data Architecture | Separates data-layer responsibilities across PostgreSQL, Redis, pgvector, Neo4j, and Celery/Outbox. | Choose the correct source of truth before writing schema or persistence logic. |
| §14. API Plan | Lists API scope for guest, chat, screening, safety/referral, dashboard, persona/reward/memory/TTS. | Check response shapes here before changing frontend/backend contracts. |
| §15. Memory, Privacy, Security | Defines memory, privacy, security, access control, deletion, and opt-out rules. | Do not store long-term memory without consent and minimization. |
| §16. Observability and Graceful Degradation | Defines metrics, logging fields, and graceful degradation when Redis/Neo4j/LLM/PostgreSQL/TTS fails. | Do not let TTS or Neo4j failure break normal text chat. |
| §17. Success Metrics | Defines success metrics for activation, engagement, pattern quality, safety, and system health. | Evaluate features through metrics, not only subjective UX impressions. |
| §18. MVP Scope | Locks MVP scope and out-of-scope boundaries to prevent scope creep. | If a task is out-of-scope, do not implement it in MVP without a new decision. |
| §19. Implementation Phases | Breaks delivery into phases A-E from core safety/chat to hardening. | Prioritize Phase A before complex engagement layers. |
| §20. Open Product and Legal Decisions | Lists unresolved product/legal decisions. | Do not guess thresholds, retention, hotline sources, or outbound contact policy. |
| §21. Non-Negotiable Acceptance Criteria | Defines non-negotiable release acceptance criteria. | Use this as the final QA gate before merge or release. |

<a id="sec-0"></a>
## 0. Document Purpose

> **Section summary:** Defines this file as the only canonical PRD and sets conflict-resolution priority after older backend/spec files are removed.  
> **Agent checkpoint:** Before editing code, verify that no older document overrides this PRD.


This document is the single source of truth for Serene after `BACKEND_PLAN.md` and `BUILDING-PLAN-AGENT-SPECS.md` are removed. It consolidates product requirements, backend architecture, runtime contracts, safety boundaries, data rules, API scope, rollout phases, and acceptance criteria into one consistent PRD.

### 0.1 Core Implementation Rule

```text
Do not implement five independent agents.
Implement one stable user-facing identity through the Serene Conversation Agent (`FriendNode`),
one conditional Internal Analyst Agent (`AnalystNode`),
one deterministic Safety Agent (`SafetyFinalizer`),
and a service/tool/worker layer for screening, resources, referral, memory, dashboard, TTS, and Neo4j sync.
```

### 0.2 Conflict Resolution Priority

1. User safety and legal/compliance policy.
2. This canonical PRD.
3. Local code conventions.
4. Frontend/UI constraints.

No older document may override this PRD.

---

<a id="sec-1"></a>
## 1. Executive Summary

> **Section summary:** Summarizes Serene as a privacy-first companion, not a diagnostic or clinical replacement, with one stable identity.  
> **Agent checkpoint:** Any UX/chat change must preserve one coherent Serene identity.


Serene is a privacy-first AI mental-health companion for young users, especially people aged 18–24 who feel stressed, emotionally overloaded, uncertain about their mental state, or reluctant to seek real-world support because of stigma, cost, time, fear of judgment, or lack of trust.

Serene is **not an AI doctor**, **not a diagnostic therapist**, and **not a replacement for professional care**. Its correct role is a supportive digital front door: it helps users express difficult feelings, understand emotional and behavioral patterns, receive one small actionable next step, and transition to real-world support when risk exceeds self-support.

The user experience must feel like **one coherent companion**. The UI may expose persona cards, unlock progression, a heart economy, and memory cards; however, these are product and style layers. The backend may be sophisticated, but the user should experience one stable identity: **Serene**.

---

<a id="sec-2"></a>
## 2. Product Thesis

> **Section summary:** States the product thesis: users need safe expression, pattern understanding, and one small next step, not diagnosis.  
> **Agent checkpoint:** If a feature does not support this loop, move it to backlog instead of MVP.


Users who are struggling rarely begin with a clinical request. They usually begin with uncertainty:

```text
“I do not know what is wrong with me.”
“I want to say it, but I do not want anyone to judge me.”
“I am not sure whether this is serious.”
“I need to know what to do next.”
```

Therefore, Serene must not behave like a diagnosis machine. It must behave as a safe, explainable, action-oriented support layer.

Core product loop:

```text
Private expression
  -> Emotional validation
  -> Pattern understanding
  -> Small next step
  -> Reflection and continuity
  -> Care pathway when needed
```

Serene’s differentiation is not generic chatbot empathy. It is the combination of:

- low-friction privacy-first onboarding;
- one stable Serene identity with controlled persona/style modes;
- clinically informed but non-diagnostic pattern insight;
- a Neo4j Knowledge Graph for symptom, trigger, emotion, cognitive distortion, coping, and resource relationships;
- a deterministic safety path;
- async memory and dashboard intelligence;
- engagement systems that do not manipulate dependency.

---

<a id="sec-3"></a>
## 3. Non-Negotiable Product and Architecture Invariants

> **Section summary:** Lists non-negotiable invariants for identity, persona, safety, data, async work, and validation.  
> **Agent checkpoint:** Use this as the mandatory checklist before major PRs.


| Category | Required invariant |
|---|---|
| Identity | The user experiences one assistant identity: **Serene**. |
| Persona | Personas are style/profile modes inside the **Serene Conversation Agent** (`FriendNode`), not separate agents. |
| Normal user-facing LLM | The **Serene Conversation Agent** (`FriendNode`) is the only user-facing LLM **step** in the normal flow. |
| Internal analysis | The **Internal Analyst Agent** (`AnalystNode`) only produces a structured `AnalystBundle`; it never speaks directly to the user. |
| Safety ordering | `SafetyGate` always runs before normal graph or LLM orchestration. |
| High-risk path | High-risk turns bypass `DistressRouter`, the **Internal Analyst Agent** (`AnalystNode`), and the normal **Serene Conversation Agent** (`FriendNode`). |
| Deterministic safety | The **Safety Agent** (`SafetyFinalizer`) must be deterministic, auditable, and final for the high-risk turn. |
| Screening | Screening and pattern insight are monitoring support, not diagnosis. |
| Data source of truth | PostgreSQL is the source of truth; Neo4j is a derived knowledge/pattern layer. |
| Async-first work | Memory, embeddings, summaries, dashboards, and graph sync run after response unless synchronous writes are mandatory. |
| Neo4j safety | Neo4j must not store raw messages, PII, crisis logs, or direct disorder assignment. |
| Output validation | Every normal response must pass `SafetyOutputValidator` before return. |

---

<a id="sec-4"></a>
## 4. Strategic Product Decisions

> **Section summary:** Locks strategic decisions: 3 main agents in practical terms, personas are not agents, and Neo4j is not a diagnosis engine.  
> **Agent checkpoint:** When asked for “multi-agent,” follow the top agent table; do not create five independent bots.


### 4.1 One Stable Identity, Multiple Controlled Style Modes

```text
Serene = stable assistant identity.
Serene Conversation Agent (`FriendNode`) = only normal user-facing LLM orchestration step.
Persona = controlled style/profile layer inside the Serene Conversation Agent (`FriendNode`).
```

Allowed persona IDs:

| Persona | ID | Role | Safety posture |
|---|---|---|---|
| Good Friend | `ban_than` | Default emotional support | Always available in normal flow |
| Mentor | `nguoi_thay` | Clarity and decision support | Available from day one |
| Puppy | `cun` | Playful mood lift | Only when distress is low |
| Cat | `meo` | Quiet, low-pressure support | Deactivate when distress rises |
| Crush | `crush` | Warm soft-support with strict boundaries | Explicit opt-in; never during high-risk state |

Canonical metadata:

```json
{
  "agent_display_name": "Serene",
  "active_persona_id": "ban_than",
  "active_persona_label": "Bạn Tốt",
  "persona_style_applied": true,
  "persona_style_strength": 1.0
}
```

Safety may force `active_persona_id = "ban_than"`, `persona_style_applied = false`, or `persona_style_strength = 0.0`. Core support must remain available even when a persona is locked, unsafe, in cooldown, or deactivated.

### 4.2 Screening, Not Diagnosis

Serene may identify signs compatible with broad condition groups such as anxiety-related stress, depressive mood, sleep disturbance, prolonged stress, social withdrawal, or cognitive distortion patterns. Serene must not conclude that the user has a disorder.

Allowed framing:

```text
“Some signs you described are compatible with ...”
“This is not a diagnosis.”
“What is still missing to understand this better is ...”
“The appropriate next step is ...”
```

Forbidden framing:

```text
“You have ...”
“You are highly likely to have ...”
“The AI diagnoses you with ...”
“You have an X% disease risk ...”
```

### 4.3 Safety-First, Not Hard-Stop-First

When a high-risk signal appears, the system must not simply freeze the UI or display a cold list of phone numbers. The backend must return a controlled de-escalation payload that includes:

1. emotional stabilization;
2. immediate safe micro-action;
3. connection to real-world support when needed.

LLMs may help generate bounded copy when policy allows, but the safety decision must not depend on free-form LLM output.

### 4.4 Neo4j Is a Knowledge/Pattern Substrate, Not a Diagnosis Engine

Neo4j supports relationship reasoning: symptom co-occurrence, trigger-emotion-symptom paths, cognitive distortion mapping, coping/resource matching, dashboard insight, and disorder-aware screening support. Neo4j is not the source of truth and must not store raw sensitive user data.

---

<a id="sec-5"></a>
## 5. Target Users

> **Section summary:** Defines primary and secondary users and their real product needs.  
> **Agent checkpoint:** Do not add heavy clinical intake if it increases first-chat friction.


### 5.1 Primary User: Young Adult Who Cannot Tell Anyone

| Attribute | Description |
|---|---|
| Age | 18–24 |
| Context | Student, early-career worker, or user under transition pressure |
| Stressors | Study, work, family expectations, relationships, money, future uncertainty, loneliness |
| Behavior | Comfortable with AI/social platforms; expects low-friction digital support |
| Barrier | Fear of judgment, stigma, privacy concerns, uncertainty about severity |
| Need | Private expression, emotional understanding, small next steps, safety path when escalation occurs |

### 5.2 Secondary User: Self-Aware Mental-Health Explorer

| Attribute | Description |
|---|---|
| Context | Has used check-ins, journaling, therapy content, or self-care apps |
| Need | Long-term tracking, trigger insight, pattern explanation, resource recommendation |
| Opportunity | Convert chat into dashboard insight and a guided care pathway |

---

<a id="sec-6"></a>
## 6. Core Product Requirements

> **Section summary:** Defines core product requirements: onboarding, chat, pattern insight, screening, coping, safety pathway, dashboard, persona/reward/memory/TTS.  
> **Agent checkpoint:** For each feature, check the acceptance criteria in the relevant subsection.


### 6.1 Private Onboarding

**Goal:** Users should enter chat quickly without being forced through a long medical intake.

Requirements:

- Allow guest or anonymous sessions.
- Show a short and understandable privacy note.
- Let users choose their immediate need: talk, calm down, understand what is happening, or receive a small plan.
- Do not require clinical forms before the first chat.
- Provide controls to delete chat history or disable long-term memory.

Acceptance criteria:

- First chat can start in under 30 seconds.
- Onboarding does not use diagnosis-oriented language.
- Guest persistence is explicit and limited.

### 6.2 Serene Chat Surface

**Goal:** Users should feel heard without being judged, lectured, or labeled.

Requirements:

- If the user writes in Vietnamese, Serene responds in Vietnamese.
- Response order: acknowledge emotional signal -> reflect specific context -> offer one question or one small action.
- Avoid overusing medical terminology.
- Do not claim diagnostic authority.
- Do not reveal internal module names.

Acceptance criteria:

- Each normal response includes at least one concrete reflection.
- User-facing copy does not expose the Internal Analyst Agent (`AnalystNode`), `SafetyGate`, or `ResourceSelector`.
- P95 normal chat response target is under 3 seconds after context optimization.

### 6.3 Pattern Insight

**Goal:** Help users understand patterns without labeling them as having a disorder.

Triggers:

- The user asks whether something is wrong or requests analysis.
- Repeated signs appear in recent context.
- Screening suggests follow-up.
- Distress is elevated but not high-risk.
- Neo4j can improve resource or coping recommendations.

Internal output schema:

```json
{
  "pattern_group": "anxiety_related_signs",
  "evidence": ["observable_sign_1", "observable_sign_2"],
  "missing_info": ["duration", "functional_impact"],
  "confidence": "low | medium | high",
  "risk_level_hint": "low | moderate | elevated",
  "recommended_next_action": "offer_short_screening | suggest_grounding | suggest_journaling | suggest_referral",
  "resource_query": {
    "symptom_slugs": ["sleep_difficulty"],
    "coping_categories": ["grounding"]
  },
  "user_facing_policy": "screening_not_diagnosis"
}
```

User-facing policy:

- Use “signs compatible with,” not “you have.”
- Provide brief evidence.
- State limitations clearly.
- Offer one concrete next step.

Acceptance criteria:

- No disease probability is shown to the user.
- Insights include sufficient evidence or ask a follow-up question when evidence is missing.
- If a high-risk state is detected, pattern analysis stops and the Safety Agent (`SafetyFinalizer`) controls the turn.

### 6.4 Guided Screening

Requirements:

- Support short check-ins and approved scale flows such as PHQ-9, GAD-7, or PSS.
- Screening may be conversational or form-based.
- Users may skip or stop screening.
- Results are interpreted as screening indicators, not diagnosis.
- High-severity output sets safety flags and routes to the safe care pathway when needed.

### 6.5 Coping Recommendation

Requirements:

- Use Neo4j and rules to match symptom/trigger/cognitive patterns to coping actions.
- Candidate actions include grounding, breathing, journaling, task breakdown, sleep routine, social support scripts, and cognitive reframing.
- Present no more than two options in one turn.
- Include a short rationale and feedback hook.

### 6.6 Safe Care Pathway

Support pathway levels:

| Level | Meaning |
|---|---|
| Self-help | User can try a small action in the app. |
| Monitor | Continue tracking with a light check-in or screening. |
| Professional support recommended | User should consider real-world professional support. |
| Urgent support | Return a safety payload and referral/hotline options. |

Requirements:

- Risk levels 4–5 must not continue as normal chat in the same turn.
- Referral payloads use calm, non-alarming language.
- Counselor/clinician summaries are created only with user consent.
- Do not automatically contact third parties without consent and legal approval.

### 6.7 Personal Insight Dashboard

The dashboard should answer:

- What tends to trigger distress?
- What coping actions helped before?
- Is mood/stress improving, stable, or worsening?
- What should the user try next?
- When should the user consider real-world support?

Modules:

- mood trend;
- trigger map;
- pattern insight cards;
- coping history;
- weekly reflection;
- “what helped me before?” retrieval;
- optional screening history.

Acceptance criteria:

- The dashboard does not label the user as having a fixed disorder.
- Insight cards can be hidden or deleted.
- Sensitive data is summarized, not exposed as raw transcript.

### 6.8 Persona Progression, Heart Economy, Memory/Knowledge Layers

Requirements:

- `ban_than` and `nguoi_thay` are available from day one.
- `cun`, `meo`, and `crush` are unlockable rewards with clear safety gates.
- Hearts are awarded only for meaningful behaviors: check-ins, reflections, tiny actions, knowledge completion, memory review.
- Do not reward endless chat duration, spam, unsafe content, or high distress itself.
- Memory Cards are user-controllable: keep, edit, delete, disable future use.
- Knowledge Unlocks are psychoeducation, not treatment.
- Voice/TTS renders from the selected response plan or a safe summary; there is no separate hardcoded crisis voice branch.

---

<a id="sec-7"></a>
## 7. Canonical System Architecture

> **Section summary:** Defines the canonical runtime architecture and the rejected architecture.  
> **Agent checkpoint:** Do not implement Conversation/Screener/Resource/Escalation/SafetyGuardrail as autonomous LLM agents.


### 7.1 Accepted Runtime Model

In the diagram below, `FriendNode`, `AnalystNode`, and `SafetyFinalizer` are **LangGraph (or equivalent) step identifiers** for the **Serene Conversation Agent**, **Internal Analyst Agent**, and **Safety Agent** defined in the Reader Summary table.

```text
Frontend
  -> FastAPI ChatGateway
  -> ContextLoader (loads profile, mood, safety_flags, graph_patterns, nutrition_meals)
  -> SafetyGate
      -> if high-risk: SafetyFinalizer        // Safety Agent
           -> returns de-escalation payload + DistressConversationUi (DistressSupportPopup)
      -> else: DistressRouter
           -> sets route_decision, use_fast_friend_model
          -> friend_direct:
               -> ultra-fast path (distress < 0.20 AND msg ≤ 50 chars): minimal ~550-token prompt, no fewshot
               -> normal path: PersonaRouter -> FriendNode   // Serene Conversation Agent
          -> analyst_then_friend: AnalystNode -> AnalystBundle -> PersonaRouter -> FriendNode
               // ^ Internal Analyst Agent          ^ Serene Conversation Agent (same FriendNode step)
  -> SafetyOutputValidator
  -> SyncWriter
  -> AsyncWorkers
      -> MemoryWorker
      -> GraphSyncWorker
      -> InsightWorker (feeds AnalystPipelineService)
      -> TTSJobService
      -> SessionLifecycleService (on session close: summarize -> MemoryCard creation)

Offline Analyst Pipeline (async, not in-request):
  AnalystPipelineService: collect SourceEvents -> PrivacyFilter -> FeatureBuilder
    -> ContextPackBuilder -> LLMAnalyzer -> InsightAggregator -> InsightHypothesis / InsightEvidence
  Trigger types: "turn" | "daily" | "rolling_3d" | "weekly" | "on_demand_dashboard" | "post_screening"
```

### 7.2 Rejected Architecture

Do not implement these autonomous LLM agents:

```text
ConversationAgent
ScreenerAgent
ResourceAgent
EscalationAgent
SafetyGuardrailAgent
Persona agents
```

Correct mapping:

| Old concept | Correct implementation |
|---|---|
| ConversationAgent | **Serene Conversation Agent** (`FriendNode`) |
| ScreenerAgent | `ScreeningService` + optional **Internal Analyst Agent** (`AnalystNode`) |
| ResourceAgent | `ResourceSelector` |
| EscalationAgent | **Safety Agent** (`SafetyFinalizer`) + `ReferralService` |
| SafetyGuardrailAgent | `SafetyGate` + `SafetyOutputValidator` |
| Persona agents | style modes inside **Serene Conversation Agent** (`FriendNode`) |

The five-agent model is rejected because it creates role overlap, persona fragmentation, latency/cost inflation, debugging complexity, safety ambiguity, and weak MVP focus.

---

<a id="sec-8"></a>
## 8. Runtime Flow

> **Section summary:** Describes the three runtime flows: normal chat, pattern insight, and high-risk handling.  
> **Agent checkpoint:** Always verify that high-risk turns bypass normal flow.


### 8.1 Normal Chat Turn

```text
1. User sends a message.
2. ChatGateway validates auth, guest token, and session.
3. ContextLoader loads recent messages, profile, mood, screening, safety flags,
   graph_patterns (Neo4j async pre-fetch), nutrition_meals, optional pgvector memories.
4. SafetyGate runs first.
5. If no high-risk state:
   - DistressRouter decides route and sets use_fast_friend_model flag.
   - If ultra-fast eligible (distress_score < 0.20 AND message ≤ 50 chars):
     FriendNode uses minimal ~550-token prompt (no fewshot, no plan_hint, no memory hint).
   - If analyst_then_friend: Internal Analyst Agent (`AnalystNode`) runs and produces AnalystBundle.
   - PersonaRouter applies persona, unlock, cooldown, and safety fallback.
   - Serene Conversation Agent (`FriendNode`) generates the Serene response
     (uses openai_model_friend_fast when use_fast_friend_model=True and distress_score < 0.55).
6. SafetyOutputValidator validates the final response.
7. SyncWriter persists required records.
8. Async workers update memory/profile/Neo4j/dashboard/TTS.
```

### 8.2 Pattern Insight Turn

```text
User message
  -> SafetyGate: no high-risk
  -> DistressRouter: analysis_needed = true
  -> Internal Analyst Agent (`AnalystNode`): produces AnalystBundle
  -> PersonaRouter: applies safe style mode
  -> Serene Conversation Agent (`FriendNode`): converts bundle into non-diagnostic explanation
  -> SafetyOutputValidator
  -> SyncWriter
  -> AsyncWorkers
```

### 8.3 High-Risk Turn

```text
User message
  -> SafetyGate: high-risk = true
  -> Safety Agent (`SafetyFinalizer`)
       - no DistressRouter
       - no Internal Analyst Agent (`AnalystNode`)
       - no normal Serene Conversation Agent (`FriendNode`)
       - return de-escalation payload + DistressConversationUi containing DistressSupportPopup
         (character "Đạt" / dat_le; cooldown_seconds = 900; includes breathing_exercise_route and support_route)
  -> SyncWriter:
       - user message
       - assistant safety response
       - crisis_logs
       - admin_audit_log if configured
  -> optional async follow-up events
```

---

<a id="sec-9"></a>
## 9. Runtime State Contract

> **Section summary:** Defines RuntimeState and mutation permissions for each component.  
> **Agent checkpoint:** Do not pass free-form dictionaries or let async workers mutate in-request state after response return.


Use typed state. Do not scatter ad-hoc dictionaries across orchestration components.

```python
RouteDecision = "friend_direct | analyst_then_friend | safety_finalizer"
ConversationMode = "normal | de_escalation"
ConfidenceLevel = "low | medium | high"
RiskLevelHint = "low | moderate | elevated"

# Implementation reference: backend/app/services/langgraph_chat.py ChatGraphState
RuntimeState = {
    # === IMMUTABLE INPUTS (set once, never mutated by nodes) ===
    "request_id": str,
    "correlation_id": str,
    "user_id": str | None,
    "guest_id": str | None,
    "session_id": str,
    "user_message": str,
    "recent_messages": list,
    "profile_snapshot": dict,
    "mood_snapshot": dict,
    "screening_snapshot": dict,
    "safety_flags": dict,
    "distress_score": float,          # FROZEN — distress_router must never mutate this
    "risk_level": int,
    "graph_patterns": dict,           # UserPatternsResult from Neo4j, pre-fetched async; {} if unavailable
    "nutrition_meals": list | None,   # today's meal check-ins; None if none logged
    "long_term_memories": list[str],
    "mem0_facts": list[str],
    "top_triggers": list[str],
    "active_goals": list[str],
    "effective_coping": list[str],
    "clinical_trajectory": str | None,

    # === CONTROL FLAGS ===
    "use_fast_friend_model": bool,     # set by distress_router; True when distress < 0.55 and msg short

    # === ROUTER OUTPUT ===
    "route_decision": RouteDecision | None,
    "route_reason": str | None,
    "routing_history": list[str],

    # === INTERNAL ANALYST AGENT OUTPUT ===
    "analyst_bundle": dict | None,    # typed AnalystBundle; None until AnalystNode runs

    # === SERENE CONVERSATION AGENT OUTPUT ===
    "reply": str,
    "assistant_tone": str,
    "goi_y_nhanh": list[str],
    "the_dinh_kem": list[dict],

    # === ORCHESTRATION ===
    "persona_state": dict,
    "persona_router_decision": dict | None,
    "conversation_mode": ConversationMode,
    "crisis_route_finalized": bool,
}
```

Mutation rules (first column = orchestration identifier; see Reader Summary for agent names):

| Component | Allowed mutations |
|---|---|
| `SafetyGate` | `risk_level`, `distress_score`, `safety_flags`, `route_decision` |
| `SafetyFinalizer` (Safety Agent) | `conversation_mode`, `crisis_route_finalized`, forced persona safety metadata |
| `DistressRouter` | `route_decision`, `route_reason`, `use_fast_friend_model`, `routing_history` |
| `PersonaRouter` | `persona_state`, `persona_router_decision`, `routing_history` |
| `AnalystNode` (Internal Analyst Agent) | `analyst_bundle`, `routing_history` only |
| `FriendNode` (Serene Conversation Agent) | output-related fields and `routing_history` only |
| Async workers | Must not mutate in-request state after response return |

---

<a id="sec-10"></a>
## 10. Component Contracts

> **Section summary:** Defines short contracts for each component/service/worker and required fallback behavior.  
> **Agent checkpoint:** When assigning coding work, scope it to the relevant component contract only.


| Component | Short contract |
|---|---|
| `ChatGateway` | FastAPI entry point; validates session, generates IDs, loads context, runs runtime, persists writes, schedules async work. |
| `ContextLoader` | Loads fixed recent window, profile, mood, screening, safety flags; optional pgvector/Neo4j only when useful. |
| `SafetyGate` | Rule/classifier gate before normal flow; outputs `risk_level`, `distress_score`, `policy_action`. |
| `SafetyFinalizer` | **Safety Agent** — deterministic finalizer for high-risk turns; returns controlled payload; writes crisis/audit records synchronously. |
| `DistressRouter` | Cheap deterministic router; selects `friend_direct` or `analyst_then_friend`; never creates user-facing text. |
| `PersonaRegistryService` | Loads persona configuration, prompt blocks, safety bounds, TTS style mapping. |
| `PersonaRouter` | Keeps/switches/suggests/deactivates/rejects style modes based on unlock, cooldown, and safety. |
| `AnalystNode` | **Internal Analyst Agent** — internal conditional LLM; JSON only; no diagnosis; no final answer; timeout fallback. |
| `FriendNode` | **Serene Conversation Agent** — only user-facing LLM in normal flow; validates emotion, reflects context, offers one next step. |
| `ScreeningService` | Manages check-ins/scales, scoring, interpretation policy, and safety flags. |
| `ResourceSelector` | Selects coping/resources using state + Neo4j/rules; falls back to static resources. |
| `ReferralService` | Returns hotline/trusted-contact/counselor/clinic options based on config and risk level. |
| `SafetyOutputValidator` | Validates safety, non-diagnosis, privacy, and persona boundaries before response. |
| `SyncWriter` | Handles transactional writes for messages, crisis logs, audit, and ledger records. |
| `MemoryWorker` | Extracts safe memories, summaries, embeddings, and profile patches asynchronously. |
| `GraphSyncWorker` | Syncs derived non-sensitive pattern data to Neo4j through outbox. |
| `InsightWorker` | Builds dashboard cards, trends, and weekly summaries asynchronously. |
| `TTSJobService` | Renders voice asynchronously and never blocks chat. |
| `TTSDedupService` | Deduplicates TTS by content/persona/voice/risk hash before enqueue. |
| `AnalystPipelineService` | Offline async insight pipeline: collects `SourceEvent`s, applies `PrivacyFilter`, builds `FeatureSnapshot`, runs `LLMAnalyzer`, aggregates into `InsightHypothesis` / `InsightEvidence`. Idempotent via `idempotency_key`. Never runs in-request. |
| `SessionLifecycleService` | On session close (reason: `new_session`, `idle_timeout`, `explicit_end`, `logout`, etc.): generates summary, creates `MemoryCard` rows, invalidates Redis profile cache. |
| `MemoryRecallService` | Deterministic handler for factual recall turns (`TurnKind`: `factual_memory_recall`, `identity_recall`). Returns `RecallReply` from `MemoryCard` + pgvector + profile; bypasses normal LLM path for eligible turns. |

Failure behavior:

| Failure | Required behavior |
|---|---|
| Redis unavailable | Load profile from PostgreSQL; chat still works with higher latency. |
| Neo4j unavailable | Serene Conversation Agent (`FriendNode`) still works; Internal Analyst Agent (`AnalystNode`) uses profile/pgvector; resources fallback to static data. |
| Analyst timeout | Continue with Serene Conversation Agent (`FriendNode`) only. |
| Friend timeout | Serene Conversation Agent (`FriendNode`) timeout: return a safe fallback response. |
| Sync write fails | Return server error; do not pretend success. |
| Crisis log write fails | Treat as a critical operational incident. |

---

<a id="sec-11"></a>
## 11. Safety Requirements

> **Section summary:** Defines SafetyGate output, risk levels, and the required Safety Agent (`SafetyFinalizer`) payload.  
> **Agent checkpoint:** This section is mandatory when changing chat, safety, TTS, referral, or routing.


### 11.1 SafetyGate Output

```json
{
  "risk_level": 0,
  "distress_score": 0.0,
  "should_route_crisis": false,
  "matched_rules": [],
  "policy_action": "normal | de_escalation | crisis_finalizer",
  "reason": "..."
}
```

### 11.2 Risk Levels

| Level | Meaning | Runtime behavior |
|---:|---|---|
| 0 | No visible distress | Normal Serene Conversation Agent (`FriendNode`) |
| 1 | Mild distress | Supportive tone |
| 2 | Moderate distress | Support + possible resource |
| 3 | Elevated non-crisis distress | Internal Analyst Agent (`AnalystNode`) may enrich; careful tone |
| 4 | High risk | **Safety Agent** (`SafetyFinalizer`); no normal flow |
| 5 | Highest urgency | **Safety Agent** (`SafetyFinalizer`) + urgent referral payload + audit path |

Thresholds must be centralized in configuration, not hardcoded across files.

### 11.3 Safety Agent (`SafetyFinalizer`) payload contract

```json
{
  "conversation_mode": "de_escalation",
  "risk_level": 4,
  "agent_display_name": "Serene",
  "active_persona_id": "ban_than",
  "active_persona_label": "Bạn Tốt",
  "persona_style_applied": false,
  "persona_style_strength": 0.0,
  "assistant_text": "controlled_supportive_text",
  "assistant_strategy": {
    "keep_engaged": true,
    "encourage_external_help": true,
    "avoid_hard_stop": true
  },
  "micro_actions": [
    {"type": "grounding", "label": "short_safe_action"},
    {"type": "breathing", "label": "short_safe_action"}
  ],
  "hotline_cards": [
    {"label": "configured_emergency_or_support_resource", "phone": "configured_phone"}
  ],
  "referral_options": [
    {"type": "trusted_contact"},
    {"type": "counselor_or_clinic"}
  ],
  "followup_priority": true,
  "distress_ui": {
    "mode": "sos_soft_popup",
    "suppress_inline_crisis_cards": true,
    "support_popup": {
      "show": true,
      "popup_id": "sos_dat_le:{session_id}:{risk_level}",
      "character_id": "dat_le",
      "character_label": "Đạt",
      "asset_path": "/frontend/assets/dat-le-shock-sos.png",
      "title": "Đạt đang ở đây",
      "message_segments": [{"type": "text", ...}, {"type": "route_link", ...}],
      "support_route": "/serene/support",
      "breathing_exercise_route": "/serene/exercises?exercise=anxiety_breathing",
      "cooldown_seconds": 900
    },
    "allow_quick_replies": false,
    "preferred_input_focus": false
  }
}
```

`DistressConversationUi` is also returned on non-SOS elevated turns with `mode: "distress_soft_support"` and `DistressSupportPopup(show=false)`. The frontend (`DatLeSosPopup.tsx`) enforces the 900-second client-side cooldown via `useDistressPopupCooldown`.

Forbidden:

- Do not call `DistressRouter`, the Internal Analyst Agent (`AnalystNode`), or the normal Serene Conversation Agent (`FriendNode`) in a high-risk turn.
- Do not produce long psychological analysis in a high-risk turn.
- Do not store raw crisis transcripts in Neo4j.
- Do not claim third-party contact unless opt-in and valid integration exist.

---

<a id="sec-12"></a>
## 12. Neo4j Knowledge Graph Role

> **Section summary:** Defines Neo4j as graph reasoning for patterns/resources, not raw sensitive storage.  
> **Agent checkpoint:** Do not create user-has-disorder edges or write raw transcripts to the graph.


Neo4j is the graph layer for relationship reasoning. It is not an agent and not the source of truth.

Allowed use cases:

- symptom-to-symptom co-occurrence;
- symptom-to-coping matching;
- trigger-to-emotion/symptom paths;
- cognitive distortion mapping;
- resource recommendation;
- dashboard pattern insight;
- screening support without diagnosis.

Forbidden in Neo4j:

- raw messages;
- PII;
- phone/email/address;
- crisis logs;
- direct “user has disorder X” edge;
- unreviewed LLM conclusions as clinical facts.

Recommended graph concepts:

```text
:Symptom, :SymptomCategory, :Disorder, :DisorderCategory,
:CognitiveDistortion, :CopingAction, :CopingCategory,
:Resource, :ResourceCategory, :Trigger, :Emotion,
:Instrument, :Item, :SafetyKeyword, :MemoryNode
```

Core relationships:

```text
(:Disorder)-[:HAS_SYMPTOM]->(:Symptom)
(:Symptom)-[:CO_OCCURS_WITH]->(:Symptom)
(:CopingAction)-[:TARGETS_SYMPTOM]->(:Symptom)
(:Resource)-[:HELPS_WITH]->(:Symptom)
(:Trigger)-[:MANIFESTS_AS]->(:Symptom)
(:Trigger)-[:EVOKES]->(:Emotion)
(:CognitiveDistortion)-[:AMPLIFIES]->(:Symptom)
(:Instrument)-[:HAS_ITEM]->(:Item)
(:Item)-[:MEASURES]->(:Symptom)
```

Neo4j query results must be converted into an `AnalystBundle` or ranked resource candidates before the Serene Conversation Agent (`FriendNode`) uses them. Raw graph output must not be shown to the user.

---

<a id="sec-13"></a>
## 13. Data Architecture

> **Section summary:** Separates data-layer responsibilities across PostgreSQL, Redis, pgvector, Neo4j, and Celery/Outbox.  
> **Agent checkpoint:** Choose the correct source of truth before writing schema or persistence logic.


| Layer | Responsibility |
|---|---|
| PostgreSQL | Source of truth: users, sessions, messages, screening, profile, crisis logs, audit, ledger. |
| Redis | Hot-path cache, guest ephemeral state, rate limiting, idempotency, temporary orchestration. |
| pgvector | Semantic recall over approved summaries or masked content. |
| Neo4j | Derived knowledge/pattern graph; no raw sensitive data. |
| Celery/Outbox | Async memory, embedding, graph sync, dashboard, TTS. |

PostgreSQL tables:

```text
users, refresh_tokens, guest_sessions, conversations, messages,
mood_checkins, screening_results, clinical_profiles, crisis_logs,
admin_audit_log, user_profiles, user_profile_snapshots,
mem0_memories, session_summaries_archive, resources,
bookmarks, play_events, sync_outbox, heart_wallets,
heart_reward_events, heart_spend_events, reward_store_items,
user_inventory_items, persona_unlock_states, memory_cards,
analyst_runs, analyst_feature_snapshots,
insight_hypotheses, insight_evidence
```

`analyst_runs`: idempotent pipeline run records (`run_id`, `user_id`, `run_type`, `status`, `window_start/end`, `data_cutoff_at`, `idempotency_key`, `feature_version`).

`analyst_feature_snapshots`: serialized `AnalystFeatureSnapshotPayload` per run (mood, nutrition, screening, memory, conversation, engagement, safety_internal, data_quality domains).

`insight_hypotheses`: aggregated non-diagnostic insight per user (`hypothesis_type`, `title`, `user_safe_summary`, `confidence`, `severity_band`, `evidence_count`, `display_allowed`).

`insight_evidence`: evidence items linked to a hypothesis (`source_table`, `source_id`, `sensitivity`, `redacted_text`); restricted access, never shown raw to user.

Redis keys:

```text
profile:{user_id}
guest:{guest_id}
rate:{user_id}:{window}
idempotency:{request_id}
tts:{voice_id}:{persona_id}:{content_hash}:{risk_level}:{locale}
```

pgvector memory types:

```text
session_summary
coping_preference
recurring_trigger
user_goal
support_preference
```

Outbox event examples:

```text
memory.created
profile.trigger_observed
profile.emotion_observed
coping.used
session.ended
resource.helpful_feedback
persona.preference_updated
knowledge_pack.completed
analyst.run_requested
analyst.insight_ready
session.lifecycle_close
memory_card.created
memory_card.deduped
```

---

<a id="sec-14"></a>
## 14. API Plan

> **Section summary:** Lists API scope for guest, chat, screening, safety/referral, dashboard, persona/reward/memory/TTS.  
> **Agent checkpoint:** Check response shapes here before changing frontend/backend contracts.


### 14.1 Guest Onboarding

```http
POST /v1/guest/session/start
POST /v1/guest/session/heartbeat
POST /v1/guest/convert
```

Rules:

- Guest mode must not require email or phone.
- Guest persistence must be explicit and limited.
- Account conversion requires consent before long-term storage.

### 14.2 Chat

```http
POST /v1/chat/message
GET  /v1/chat/sessions
GET  /v1/chat/sessions/{session_id}
POST /v1/chat/sessions/{session_id}/close
```

Normal response shape:

```json
{
  "message_id": "msg_xxx",
  "session_id": "ses_xxx",
  "conversation_mode": "normal",
  "agent_display_name": "Serene",
  "active_persona_id": "ban_than",
  "active_persona_label": "Bạn Tốt",
  "persona_style_applied": true,
  "persona_style_strength": 1.0,
  "assistant_text": "...",
  "suggested_actions": [],
  "pattern_insight": null,
  "safety": {
    "risk_level": 0,
    "followup_priority": false
  },
  "distress_ui": {
    "mode": "none",
    "suppress_inline_crisis_cards": false,
    "support_popup": {"show": false},
    "allow_quick_replies": true,
    "preferred_input_focus": true
  }
}
```

`distress_ui` is always present. `mode` is `"none"` for low-risk turns, `"distress_soft_support"` for elevated non-SOS, `"sos_soft_popup"` for high-risk turns. Frontend enforces `cooldown_seconds` client-side.

### 14.3 Screening

```http
POST /v1/screening/start
POST /v1/screening/{screening_id}/answer
POST /v1/screening/{screening_id}/complete
GET  /v1/screening/history
```

### 14.4 Safety and Referral

```http
GET  /v1/safety/hotlines
GET  /v1/safety/referrals/options
POST /v1/safety/escalate
```

### 14.5 Dashboard

```http
GET /v1/dashboard/overview
GET /v1/dashboard/mood-trend
GET /v1/dashboard/triggers
GET /v1/dashboard/coping-history
GET /v1/dashboard/weekly-summary
```

### 14.6 Persona, Rewards, Memory, TTS

```http
GET  /v1/personas
POST /v1/personas/select
GET  /v1/rewards/store
POST /v1/rewards/purchase
GET  /v1/memory/cards
PATCH /v1/memory/cards/{card_id}
DELETE /v1/memory/cards/{card_id}
POST /v1/tts/jobs
GET  /v1/tts/jobs/{job_id}
```

### 14.7 Analyst Pipeline

```http
GET  /v1/analyst/dashboard/insights
GET  /v1/analyst/dashboard/insights/{insight_id}/evidence
POST /v1/analyst/refresh
GET  /v1/analyst/runs
GET  /v1/analyst/runs/{run_id}
```

`GET /analyst/dashboard/insights` returns `InsightHypothesis` rows with `display_allowed=true`; confidence, severity_band, evidence_count, window dates. No raw evidence text. Evidence detail requires separate call to `/evidence` endpoint (restricted). `POST /analyst/refresh` accepts `run_type` and optional `force` flag; enqueues or runs synchronously (`run_now=true` for dev/admin only).

---

<a id="sec-15"></a>
## 15. Memory, Privacy, Security

> **Section summary:** Defines memory, privacy, security, access control, deletion, and opt-out rules.  
> **Agent checkpoint:** Do not store long-term memory without consent and minimization.


### 15.1 Memory Layers

| Layer | Scope | Storage |
|---|---|---|
| Working memory | One request | RuntimeState only |
| Short-term memory | Current session | PostgreSQL messages/session state |
| Long-term memory | Cross-session | `user_profiles`, pgvector memories, derived Neo4j patterns |

Allowed long-term memory:

- recurring triggers;
- preferred support style;
- coping techniques that helped;
- user goals;
- repeated high-level emotional patterns;
- general schedule patterns if shared voluntarily.

Forbidden or minimized memory:

- raw sensitive confessions;
- unnecessary personal identifiers;
- private details about third parties;
- crisis content beyond safety/audit needs;
- unsupported diagnosis labels.

### 15.2 Privacy and Security Requirements

- Data minimization by default.
- Mask phone, email, and full names where possible.
- Avoid storing precise addresses.
- Crisis logs restricted to safety/admin role.
- Admin audit log is append-only.
- Users can delete chat history, memory profile, and account; export basic data; opt out of long-term personalization; and disable memory card usage.

Access control:

| Data | Access |
|---|---|
| messages | user + service role |
| screening_results | user + restricted service role |
| clinical_profiles | restricted service role only |
| crisis_logs | safety/admin role only |
| admin_audit_log | append-only admin/service role |
| Neo4j user subgraph | service role only; no raw PII |
| heart_wallets / heart_reward_events / heart_spend_events | user read + service write |
| memory_cards | user controls + service role |
| sync_outbox (voice.tts_request jobs) | user read via API + service write |
| analyst_runs, analyst_feature_snapshots | service role only; user may read own run status via API |
| insight_hypotheses | user read (display_allowed=true rows) + restricted service role |
| insight_evidence | restricted service role only; never shown raw to user |

---

<a id="sec-16"></a>
## 16. Observability and Graceful Degradation

> **Section summary:** Defines metrics, logging fields, and graceful degradation when Redis/Neo4j/LLM/PostgreSQL/TTS fails.  
> **Agent checkpoint:** Do not let TTS or Neo4j failure break normal text chat.


### 16.1 Metrics

| Metric | Target |
|---|---:|
| P95 normal chat latency (full path) | < 3s |
| P95 ultra-fast chat latency (distress < 0.20, msg ≤ 50 chars) | < 1s target |
| Safety high-risk recall | Near 100% for configured rules |
| Average LLM calls per normal turn | <= 1.3 target |
| Internal Analyst Agent (`AnalystNode`) invocation rate | Monitor and avoid overuse |
| Internal Analyst Agent (`AnalystNode`) timeout rate | Monitor |
| `AnalystPipelineService` run completion rate | Monitor (`completed` / total started) |
| `AnalystPipelineService` `skipped_insufficient_data` rate | Monitor; high rate = user data gaps |
| `AnalystPipelineService` `blocked_by_safety` rate | Monitor; safety boundary is working |
| Memory card extraction rate per session close | Monitor |
| Outbox success rate | >= 99.5% |
| Redis profile cache hit | >= 80% |
| Neo4j sync lag | < 10s target |
| Crisis payload render success | 100% |
| TTS dedup hit rate | Monitor and improve |
| `DistressSupportPopup` shown rate per SOS turn | Monitor; frontend cooldown compliance |

Logs per request:

```text
correlation_id
request_id
user_id or guest_id
session_id
route_decision
risk_level
latency_ms
llm_call_count
neo4j_read_used
outbox_event_count
error_code
```

Do not log raw sensitive content in normal application logs.

### 16.2 Degradation Policy

| Dependency failure | Required behavior |
|---|---|
| Neo4j unavailable | Serene Conversation Agent (`FriendNode`) works; Internal Analyst Agent (`AnalystNode`) uses profile/pgvector; resources fallback static; outbox pending. |
| Redis unavailable | Read profile from PostgreSQL; chat works with higher latency. |
| LLM unavailable | Safety Agent (`SafetyFinalizer`) via templates; basic supportive fallback; screening/dashboard reads work. |
| PostgreSQL unavailable | Fail closed for write operations; do not pretend persistence succeeded. |
| TTS unavailable | Text succeeds; voice status returns degraded/failed without blocking chat. |

---

<a id="sec-17"></a>
## 17. Success Metrics

> **Section summary:** Defines success metrics for activation, engagement, pattern quality, safety, and system health.  
> **Agent checkpoint:** Evaluate features through metrics, not only subjective UX impressions.


| Category | Metrics |
|---|---|
| Activation | first chat completion, guest-to-account conversion, privacy note acknowledgement, first-session helpfulness |
| Engagement | D1/D7/D30 retention, meaningful turns/session, next-step action usage, dashboard revisit, persona unlock, memory card review |
| Pattern quality | insight usefulness, false over-labeling, insights with sufficient evidence, disclaimer + next-step rate |
| Safety | high-risk recall, false-positive review, Safety Agent (`SafetyFinalizer`) latency, crisis payload success, crisis/audit write success |
| System | P95 latency, Internal Analyst Agent timeout, graph query latency, outbox success, Redis hit rate, TTS completion/dedup |

---

<a id="sec-18"></a>
## 18. MVP Scope

> **Section summary:** Locks MVP scope and out-of-scope boundaries to prevent scope creep.  
> **Agent checkpoint:** If a task is out-of-scope, do not implement it in MVP without a new decision.


### 18.1 In Scope

- Private onboarding.
- Serene chat surface.
- `SafetyGate` and **Safety Agent** (`SafetyFinalizer`).
- `DistressRouter`.
- **Serene Conversation Agent** (`FriendNode`).
- Conditional **Internal Analyst Agent** (`AnalystNode`) and `AnalystBundle`.
- Neo4j pattern insight for non-diagnostic support.
- Guided screening flow.
- Basic resource recommendation.
- Sync/async persistence.
- Dashboard overview.
- Basic referral/hotline payload.
- Persona registry and `PersonaRouter`.
- Heart economy, Reward Store, Memory Cards, Knowledge Unlocks.
- TTS deduplication.
- Observability and graceful degradation.
- Privacy controls for memory deletion and opt-out.

### 18.2 Out of Scope

- Medical diagnosis.
- Medication advice.
- Autonomous clinical decision-making.
- Five independent user-facing agents.
- Personas with separate memory, authority, safety behavior, or clinical claims.
- Frontend-owned wallet arithmetic or hardcoded reward catalog.
- Autonomous emergency contact without explicit consent and legal review.
- Unmoderated community.
- Storing raw crisis conversations in Neo4j.
- Outbound call/SMS integration unless legal/product review explicitly approves it.

---

<a id="sec-19"></a>
## 19. Implementation Phases

> **Section summary:** Breaks delivery into phases A-E from core safety/chat to hardening.  
> **Agent checkpoint:** Prioritize Phase A before complex engagement layers.


| Phase | Goal | Deliverables |
|---|---|---|
| A — Safety, core chat, core persona | Reliable MVP chat | `/v1/chat/message`, guest session, `ChatGateway`, `ContextLoader`, `SafetyGate`, Safety Agent (`SafetyFinalizer`), Serene Conversation Agent (`FriendNode`), basic `DistressRouter`, `PersonaRegistryService`, `PersonaRouter` for `ban_than`/`nguoi_thay`, sync writes, audit/crisis logging |
| B — Conditional insight | Meaningful insight without diagnosis | Internal Analyst Agent (`AnalystNode`), `AnalystBundle`, Neo4j read queries, Pattern Insight policy, screening integration, feedback, timeout fallback |
| C — Memory/dashboard | Retention and continuity | `MemoryWorker`, session summarizer, Memory Cards, pgvector, profile patch, persona preference, dashboard overview, mood trend, trigger map, coping history, weekly summary |
| D — Resource/referral/progression | Useful graph + engagement | `ResourceSelector`, `ReferralService`, Neo4j resource matching, region-aware referral data, outbox worker, graph health, Heart economy, Reward Store, Knowledge Unlocks, TTS dedup |
| E — Hardening | Safer release | PII masking, retention jobs, right-to-delete, test suite, monitoring dashboards, safety review, legal/product review for proactive escalation |

---

<a id="sec-20"></a>
## 20. Open Product and Legal Decisions

> **Section summary:** Lists unresolved product/legal decisions.  
> **Agent checkpoint:** Do not guess thresholds, retention, hotline sources, or outbound contact policy.


1. Exact thresholds for `risk_level`, `distress_score`, and `ANALYST_DISTRESS_THRESHOLD`.
2. Whether guest chat is persisted before account conversion.
3. Retention period for messages, screening results, memories, TTS artifacts, and crisis logs.
4. Whether trusted contact is opt-in only or excluded from MVP.
5. Whether outbound call/SMS is allowed; if yes, provider and consent model.
6. Which screening instruments are included in MVP.
7. Whether clinical review is required before changing graph seed.
8. Whether dashboard shows raw scores, bands, or user-friendly labels.
9. Which hotline/referral sources are officially approved.
10. How to handle minors or users outside target age range.
11. Whether TTS audio is stored, cached temporarily, or regenerated.
12. Whether persona unlock requirements are fixed or remotely configurable.
13. Whether `AnalystPipelineService` runs are user-visible in full or only surfaced as dashboard insight cards.
14. Whether insight evidence detail endpoint should be admin-only or accessible to the owning user.
15. Retention period for `analyst_runs` and `analyst_feature_snapshots`.
16. Whether `DistressSupportPopup` cooldown should be server-enforced (currently client-side only via `useDistressPopupCooldown`).

---

<a id="sec-21"></a>
## 21. Non-Negotiable Acceptance Criteria

> **Section summary:** Defines non-negotiable release acceptance criteria.  
> **Agent checkpoint:** Use this as the final QA gate before merge or release.


Before MVP release:

1. A normal user experiences one stable Serene identity.
2. Persona cards are style modes, not agents.
3. The **Serene Conversation Agent** (`FriendNode`) is the only normal user-facing LLM orchestration step.
4. The **Internal Analyst Agent** (`AnalystNode`) never produces final user-facing text.
5. `SafetyGate` always runs before normal orchestration.
6. High-risk turns bypass normal Internal Analyst Agent / Serene Conversation Agent flow.
7. The **Safety Agent** (`SafetyFinalizer`) is deterministic, auditable, and final for that turn.
8. Pattern insight never exposes disease probabilities.
9. Screening results are framed as screening, not diagnosis.
10. Neo4j never stores raw messages, PII, crisis logs, or direct disorder assignment.
11. Neo4j writes happen through outbox only.
12. Async workers never block normal chat response.
13. Safety-critical writes are synchronous in high-risk path.
14. Persona/style modes cannot override safety, privacy, or medical-boundary policy.
15. User can delete or disable long-term memory.
16. TTS failure never blocks text response.
17. Logs do not contain raw sensitive content.
18. The system degrades safely when Redis, Neo4j, LLM, or TTS is unavailable.
