// =============================================================================
// VALIDATION — CBT ENRICHMENT PATCHES
// Run after:
//   1) neo4j_patch_cbt_workbook.cypher
//   2) neo4j_patch_cbt_dummies.cypher
// =============================================================================

// ---------- 1) Node count checks ----------
UNWIND [
  'behavioural_activation','graded_exposure','cognitive_restructuring','problem_solving',
  'worry_containment','smart_goal_setting','sleep_hygiene_practice','physical_exercise',
  'abc_model_mapping','thought_recording','erp','activity_scheduling'
] AS action_id
OPTIONAL MATCH (a:CopingAction {action_id: action_id})
RETURN 'coping_actions_expected_12' AS check, count(a) AS actual, 12 AS expected;

UNWIND [
  'jumping_to_conclusions','magnification',
  'core_belief_globalizing','all_or_nothing','mental_filter'
] AS distortion_slug
OPTIONAL MATCH (d:CognitiveDistortion {slug: distortion_slug})
RETURN 'new_distortions_expected_5' AS check, count(d) AS actual, 5 AS expected;

UNWIND [
  'fight_flight_response','negative_automatic_thought','avoidance_behaviour',
  'rumination','schema_activation'
] AS process_slug
OPTIONAL MATCH (p:PsychProcess {slug: process_slug})
RETURN 'new_psych_processes_expected_5' AS check, count(p) AS actual, 5 AS expected;

UNWIND ['social_withdrawal','hypervigilance'] AS symptom_slug
OPTIONAL MATCH (s:Symptom {slug: symptom_slug})
RETURN 'new_symptoms_expected_2' AS check, count(s) AS actual, 2 AS expected;

UNWIND ['physical_symptom_awareness','crowded_public_spaces'] AS trigger_slug
OPTIONAL MATCH (t:Trigger {slug: trigger_slug})
RETURN 'new_triggers_expected_2' AS check, count(t) AS actual, 2 AS expected;

// ---------- 2) HELPS_WITH integrity ----------
// Should return 0 rows. Any row means an invalid/missing Disorder endpoint.
MATCH (a:CopingAction)-[r:HELPS_WITH]->(d)
WHERE a.action_id IN [
  'behavioural_activation','graded_exposure','cognitive_restructuring','problem_solving',
  'worry_containment','smart_goal_setting','sleep_hygiene_practice','physical_exercise',
  'abc_model_mapping','thought_recording','erp','activity_scheduling'
]
  AND d.slug IS NULL
RETURN a.action_id AS action_id, r AS bad_rel, d AS bad_target;

// Coverage check: every new coping action should have at least one HELPS_WITH edge.
UNWIND [
  'behavioural_activation','graded_exposure','cognitive_restructuring','problem_solving',
  'worry_containment','smart_goal_setting','sleep_hygiene_practice','physical_exercise',
  'abc_model_mapping','thought_recording','erp','activity_scheduling'
] AS action_id
OPTIONAL MATCH (:CopingAction {action_id: action_id})-[r:HELPS_WITH]->(:Disorder)
RETURN action_id, count(r) AS helps_with_count
ORDER BY helps_with_count ASC, action_id ASC;

// ---------- 3) TARGETS_SYMPTOM strength checks ----------
// Should return 0 rows. Any row means missing/invalid strength property.
MATCH (a:CopingAction)-[r:TARGETS_SYMPTOM]->(s:Symptom)
WHERE a.action_id IN [
  'behavioural_activation','graded_exposure','cognitive_restructuring','problem_solving',
  'worry_containment','smart_goal_setting','sleep_hygiene_practice','physical_exercise',
  'abc_model_mapping','thought_recording','erp','activity_scheduling'
]
  AND (
    r.strength IS NULL OR
    toFloat(r.strength) < 0.0 OR
    toFloat(r.strength) > 1.0
  )
RETURN a.action_id AS action_id, s.slug AS symptom_slug, r.strength AS strength;

// Coverage check: every new coping action should have at least one TARGETS_SYMPTOM edge.
UNWIND [
  'behavioural_activation','graded_exposure','cognitive_restructuring','problem_solving',
  'worry_containment','smart_goal_setting','sleep_hygiene_practice','physical_exercise',
  'abc_model_mapping','thought_recording','erp','activity_scheduling'
] AS action_id
OPTIONAL MATCH (:CopingAction {action_id: action_id})-[r:TARGETS_SYMPTOM]->(:Symptom)
RETURN action_id, count(r) AS targets_symptom_count
ORDER BY targets_symptom_count ASC, action_id ASC;
