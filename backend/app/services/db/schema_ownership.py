from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

SchemaDisposition = Literal[
    "active_canonical",
    "active_product_questionable",
    "drop_after_owner_removal_in_this_pr",
    "legacy_retired_drop_now",
    "docs_only_drift",
    "unknown_needs_manual_decision",
]


@dataclass(frozen=True)
class TableOwnership:
    table_name: str
    schema_disposition: SchemaDisposition
    canonical_domain: str
    owner_summary: str
    notes: str = ""


SCHEMA_OWNERSHIP: dict[str, TableOwnership] = {
    "users": TableOwnership("users", "active_canonical", "identity", "Auth and user account source of truth."),
    "user_identities": TableOwnership("user_identities", "active_canonical", "identity", "OAuth and identity linking."),
    "refresh_tokens": TableOwnership("refresh_tokens", "active_canonical", "identity", "Session refresh-token persistence."),
    "email_verification_tokens": TableOwnership(
        "email_verification_tokens", "active_canonical", "identity", "Email verification flow."
    ),
    "password_reset_tokens": TableOwnership(
        "password_reset_tokens", "active_canonical", "identity", "Password reset flow."
    ),
    "conversations": TableOwnership(
        "conversations", "active_canonical", "conversation", "Chat session metadata."
    ),
    "messages": TableOwnership("messages", "active_canonical", "conversation", "Canonical chat transcript store."),
    "mood_checkins": TableOwnership(
        "mood_checkins", "active_canonical", "mood", "Mood and reflect evidence store."
    ),
    "resources": TableOwnership("resources", "active_canonical", "resources", "Approved wellness resource catalog."),
    "bookmarks": TableOwnership("bookmarks", "legacy_retired_drop_now", "resource_engagement", "Retired."),
    "play_events": TableOwnership("play_events", "legacy_retired_drop_now", "resource_engagement", "Retired."),
    "journal_prompts": TableOwnership("journal_prompts", "legacy_retired_drop_now", "journaling", "Retired."),
    "journal_entries": TableOwnership("journal_entries", "legacy_retired_drop_now", "journaling", "Retired."),
    "mem0_memories": TableOwnership(
        "mem0_memories",
        "active_canonical",
        "memory",
        "Canonical user-memory persistence store.",
        "This is the only canonical user-memory persistence table.",
    ),
    "session_summaries_archive": TableOwnership(
        "session_summaries_archive",
        "active_canonical",
        "memory",
        "Canonical durable session-summary archive.",
    ),
    "user_profiles": TableOwnership(
        "user_profiles", "active_canonical", "profile_cache", "Derived profile cache and rollup state."
    ),
    "user_profile_snapshots": TableOwnership(
        "user_profile_snapshots", "active_canonical", "profile_cache", "Profile history snapshots."
    ),
    "onboarding_tour_states": TableOwnership(
        "onboarding_tour_states",
        "active_canonical",
        "onboarding",
        "Deterministic first-run guided tour state.",
    ),
    "clinical_profiles": TableOwnership(
        "clinical_profiles",
        "active_canonical",
        "screening_derived",
        "Derived internal screening/risk summary; not raw answer storage.",
    ),
    "screening_answers": TableOwnership(
        "screening_answers",
        "active_canonical",
        "screening_raw",
        "Canonical raw screening answer history.",
    ),
    "risk_inference_log": TableOwnership(
        "risk_inference_log", "legacy_retired_drop_now", "safety", "Merged into crisis_logs."
    ),
    "session_risk_snapshots": TableOwnership(
        "session_risk_snapshots", "active_canonical", "safety", "Per-session risk snapshots."
    ),
    "crisis_logs": TableOwnership("crisis_logs", "active_canonical", "safety", "SOS/crisis audit log."),
    "analyst_signals": TableOwnership(
        "analyst_signals",
        "active_canonical",
        "analyst",
        "Canonical internal analyst signal persistence.",
        "Use analyst_signals plus insight_hypotheses/dashboard_safe_insights; no analyst_bundles table.",
    ),
    "insight_hypotheses": TableOwnership(
        "insight_hypotheses", "active_canonical", "analyst", "Canonical internal insight aggregation."
    ),
    "dashboard_safe_insights": TableOwnership(
        "dashboard_safe_insights", "active_canonical", "analyst", "Frontend-safe dashboard insight projection."
    ),
    "sync_outbox": TableOwnership(
        "sync_outbox",
        "active_canonical",
        "async_outbox",
        "Canonical persistence table for async jobs and worker events.",
        "sync_outbox is the persistence table; async_outbox.py is code, not a table.",
    ),
    "admin_audit_log": TableOwnership(
        "admin_audit_log", "active_canonical", "admin", "Admin audit trail."
    ),
    "heart_wallets": TableOwnership(
        "heart_wallets", "active_canonical", "heart_economy", "Bounded reward-economy wallet snapshot."
    ),
    "heart_reward_events": TableOwnership(
        "heart_reward_events", "active_canonical", "heart_economy", "Reward ledger events."
    ),
    "heart_spend_events": TableOwnership(
        "heart_spend_events", "active_canonical", "heart_economy", "Spend ledger events."
    ),
    "streak_states": TableOwnership(
        "streak_states", "active_canonical", "engagement", "Streak progression state."
    ),
    "nutrition_meal_checkins": TableOwnership(
        "nutrition_meal_checkins", "active_canonical", "nutrition", "Nutrition check-in source of truth."
    ),
    "persona_unlock_states": TableOwnership(
        "persona_unlock_states", "active_canonical", "persona_unlocks", "Persona unlock progression state."
    ),
    "reward_store_items": TableOwnership(
        "reward_store_items", "active_canonical", "heart_economy", "Reward store catalog."
    ),
    "user_inventory_items": TableOwnership(
        "user_inventory_items", "active_canonical", "heart_economy", "Reward inventory state."
    ),
    "knowledge_packs": TableOwnership(
        "knowledge_packs",
        "active_product_questionable",
        "knowledge_unlocks",
        "Used by knowledge progress service and reward-linked unlock flow.",
    ),
    "knowledge_cards": TableOwnership(
        "knowledge_cards",
        "active_product_questionable",
        "knowledge_unlocks",
        "Used by knowledge progress service and reward-linked unlock flow.",
    ),
    "user_knowledge_progress": TableOwnership(
        "user_knowledge_progress",
        "active_product_questionable",
        "knowledge_unlocks",
        "Used by knowledge completion/reward flow.",
    ),
    "therapy_letters": TableOwnership(
        "therapy_letters", "active_canonical", "letters", "Therapy/social letter source of truth."
    ),
    "letter_review_events": TableOwnership(
        "letter_review_events", "active_canonical", "letters", "Narrow safety/audit log for letter review."
    ),
    "counseling_knowledge": TableOwnership(
        "counseling_knowledge",
        "active_canonical",
        "counseling_source_corpus",
        "Immutable raw counseling Q&A corpus retained as source material for advisor_case_library processing.",
    ),
    "advisor_case_library": TableOwnership(
        "advisor_case_library",
        "active_canonical",
        "counseling_case_library",
        "Processed internal counseling guidance cases used by CounselingAdvisorService.",
    ),
    "advisor_domains": TableOwnership(
        "advisor_domains",
        "active_canonical",
        "counseling_case_library",
        "Runtime advisor domain catalog mapping short domains to advisor IDs.",
    ),
    "advisor_case_domain_map": TableOwnership(
        "advisor_case_domain_map",
        "active_canonical",
        "counseling_case_library",
        "Many-to-many case to advisor-domain mapping for runtime retrieval.",
    ),
    "advisor_dataset_imports": TableOwnership(
        "advisor_dataset_imports",
        "active_canonical",
        "counseling_case_library",
        "Import batch audit table for advisor JSONL staging.",
    ),
    "advisor_dataset_staging": TableOwnership(
        "advisor_dataset_staging",
        "active_canonical",
        "counseling_case_library",
        "Validated staging rows before promotion into advisor_case_library.",
    ),
    "advisor_consultation_events": TableOwnership(
        "advisor_consultation_events",
        "active_canonical",
        "counseling_case_library",
        "Privacy-safe runtime trace for advisor-assisted turns.",
    ),
    "user_notifications": TableOwnership(
        "user_notifications", "active_canonical", "notifications", "Notification history."
    ),
    "user_notification_preferences": TableOwnership(
        "user_notification_preferences", "active_canonical", "notifications", "User notification preferences."
    ),
    "conversation_memories": TableOwnership(
        "conversation_memories",
        "legacy_retired_drop_now",
        "memory",
        "Historical-only memory table; not part of active runtime schema.",
    ),
    "memory_cards": TableOwnership(
        "memory_cards",
        "legacy_retired_drop_now",
        "memory",
        "Retired user-facing memory-card table; must not be recreated.",
    ),
    "memory_card_audit_events": TableOwnership(
        "memory_card_audit_events",
        "legacy_retired_drop_now",
        "memory",
        "Retired memory-card audit table; must not be recreated.",
    ),
    "screening_results": TableOwnership(
        "screening_results",
        "legacy_retired_drop_now",
        "screening",
        "Superseded by screening_answers plus clinical_profiles.",
    ),
    "mem0_memories_entities": TableOwnership(
        "mem0_memories_entities",
        "legacy_retired_drop_now",
        "memory",
        "Legacy duplicate mem0 support table; not canonical runtime state.",
    ),
    "mem0migrations": TableOwnership(
        "mem0migrations",
        "legacy_retired_drop_now",
        "memory",
        "Legacy duplicate mem0 migration bookkeeping table.",
    ),
    "analyst_bundles": TableOwnership(
        "analyst_bundles",
        "docs_only_drift",
        "analyst",
        "Docs drift only; there is no canonical analyst_bundles table.",
    ),
    "async_outbox": TableOwnership(
        "async_outbox",
        "docs_only_drift",
        "async_outbox",
        "Table-name drift only; async_outbox is service code, not persistence schema.",
    ),
}


def tables_by_disposition(*dispositions: SchemaDisposition) -> tuple[str, ...]:
    return tuple(
        name
        for name, ownership in SCHEMA_OWNERSHIP.items()
        if ownership.schema_disposition in dispositions
    )


ACTIVE_TABLES = tables_by_disposition(
    "active_canonical",
    "active_product_questionable",
    "drop_after_owner_removal_in_this_pr",
)
ACTIVE_CANONICAL_TABLES = tables_by_disposition("active_canonical")
ACTIVE_PRODUCT_QUESTIONABLE_TABLES = tables_by_disposition("active_product_questionable")
CANDIDATE_RETIREMENT_TABLES = tables_by_disposition("drop_after_owner_removal_in_this_pr")
LEGACY_RETIRED_TABLES = tables_by_disposition("legacy_retired_drop_now")
DOCS_ONLY_DRIFT_TABLES = tables_by_disposition("docs_only_drift")
FORBIDDEN_SCHEMA_TABLES = LEGACY_RETIRED_TABLES + DOCS_ONLY_DRIFT_TABLES
