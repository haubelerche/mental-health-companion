# Runtime Naming Glossary

This file is the naming source of truth for Serene runtime terms across backend code, docs, and implementation plans.

## Why this file exists

Serene uses multiple naming layers on purpose:
- Product role names in prose (for human clarity).
- Orchestration identifiers in code and traces (for implementation stability).
- Graph keys and routing tokens (for runtime wiring and telemetry).

These layers are not conflicts. They must map 1-1 and stay explicit.

## Canonical runtime mapping

| Product role name (docs/prose) | Orchestration identifier (code + traces) | LangGraph node key | `routing_history` token | Trace span names (examples) |
|---|---|---|---|---|
| Serene Conversation Agent | `FriendNode` | `"friend"` | `"friend"` | `friend_generate`, `stream_friend_generate`, `run_non_sos_turn_total` |
| Internal Analyst Agent | `AnalystNode` | `"analyst"` | `"analyst"` | `analyst_generate` |
| Distress router (not an agent) | `DistressRouter` | `"distress_router"` | `"distress_router"` | `distress_router_decision` |
| Safety Agent (high-risk path) | `SafetyFinalizer` | N/A in non-SOS LangGraph | `"sos_handler"` in SOS handler output | N/A in `langgraph_chat.py` spans |

## Guardrails for terminology

- Do not call `FriendNode` "Friend agent". The product-facing name is **Serene Conversation Agent**.
- Do not call `AnalystNode` a user-facing agent. It is internal-only and outputs `AnalystBundle`.
- Do not call services/routers/workers "agents" unless they are explicitly listed as runtime agents in `docs/PRD.md`.
- Do not use the word "node" for agent naming in prose. Use "node" for graph structure only.
- Do not confuse LangGraph nodes with Neo4j nodes (for example `:MemoryNode` in graph schema).

## Python naming rules (backend)

- Use English `snake_case` for local variables, function names, and state keys.
- Prefer domain-specific names over generic names (`distress_score`, `route_decision`, `persona_id`).
- Generic containers such as `payload` and `data` are acceptable only in short, typed, local scopes.
- Keep orchestration identifiers stable when they are part of traces, graph wiring, or cross-file contracts.

## API and response naming rules

- Public response keys in the current contract remain stable (for example `tone_cam_xuc`, `goi_y_nhanh`, `the_dinh_kem`).
- If internal refactors use English variable names, map them to contract keys only at API boundaries.
- Any contract key rename requires coordinated API spec, backend, frontend, and migration updates.

## Cross-reference

- Product/runtime source of truth: `docs/PRD.md`
- Runtime implementation reference: `backend/app/services/langgraph_chat.py`
- Chat API contract reference: `docs/API_SPEC.md`
