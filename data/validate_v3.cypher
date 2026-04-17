// =============================================================================
// File: change_schema/validate_v3.cypher
// Purpose: Post-migration + post-bootstrap validation.
// Run each block in Neo4j Browser (or cypher-shell). Expected results in comments.
// =============================================================================

// ---- CHECK 1: No orphan category strings remain ----
// Expected: 0 rows
MATCH (n) WHERE n.category IS NOT NULL RETURN labels(n), count(n);

// ---- CHECK 2: No duplicate nodes by slug (case-insensitive) ----
// Expected: 0 rows
MATCH (n)
WHERE n.slug IS NOT NULL
WITH toLower(trim(n.slug)) AS key, labels(n) AS lbl, collect(n) AS nodes
WHERE size(nodes) > 1
RETURN lbl, key, size(nodes);

// ---- CHECK 3: Every Resource has exactly one :IN_RESOURCE_CATEGORY edge ----
// Expected: all rows categories = 1
MATCH (r:Resource)
OPTIONAL MATCH (r)-[:IN_RESOURCE_CATEGORY]->(rc:ResourceCategory)
RETURN r.resource_id, r.title_vi, count(rc) AS categories;

// ---- CHECK 4: Every Symptom has exactly one :IN_SYMPTOM_CATEGORY edge ----
// Expected: all rows categories = 1
MATCH (s:Symptom)
OPTIONAL MATCH (s)-[:IN_SYMPTOM_CATEGORY]->(sc:SymptomCategory)
RETURN s.slug, count(sc) AS categories;

// ---- CHECK 5: Every CopingAction has exactly one :IN_COPING_CATEGORY ----
// Expected: 0 rows
MATCH (c:CopingAction)
OPTIONAL MATCH (c)-[:IN_COPING_CATEGORY]->(cc:CopingCategory)
WITH c, count(cc) AS n
WHERE n <> 1
RETURN c.action_id AS action_id, n AS category_count;

// ---- CHECK 5b (optional): CopingActions linked to a Resource should have exactly one IS_RESOURCE ----
// Expected: 0 rows — journaling / talk_to_someone / maladaptive seed may legitimately have 0
MATCH (c:CopingAction)-[:IS_RESOURCE]->(r:Resource)
WITH c, count(DISTINCT r) AS n
WHERE n > 1
RETURN c.action_id, n;

// ---- CHECK 6: Every Disorder — symptom + category counts (review rows with 0 symptoms) ----
MATCH (d:Disorder)
OPTIONAL MATCH (d)-[:HAS_SYMPTOM]->(s:Symptom)
OPTIONAL MATCH (d)-[:IN_DISORDER_CATEGORY]->(dc:DisorderCategory)
RETURN d.slug, d.icd_code, d.name_vi, count(DISTINCT s) AS symptoms, count(DISTINCT dc) AS categories;

// ---- CHECK 6a (strict): Disorder must have exactly one :IN_DISORDER_CATEGORY ----
// Expected: 0 rows after clean load
MATCH (d:Disorder)
WITH d, size([(d)-[:IN_DISORDER_CATEGORY]->() | 1]) AS n
WHERE n <> 1
RETURN d.slug AS slug, d.icd_code AS icd_code, n AS in_category_count;

// ---- CHECK 6c (strict): No legacy polymorphic :IN_CATEGORY on taxonomy pairs (v3.3+) ----
// Expected: 0
MATCH ()-[r:IN_CATEGORY]->() RETURN count(r) AS legacy_in_category_count;

// ---- CHECK 6d (strict): No legacy :DIFFERENTIAL_DUE_TO (renamed RULE_OUT_SCREEN in v3.3) ----
MATCH ()-[r:DIFFERENTIAL_DUE_TO]->() RETURN count(r) AS legacy_differential_due_to;

// ---- CHECK 6e (strict): PsychProcess must not :UNDERLIES Symptom (use :PSYCH_BASIS_FOR) ----
MATCH (:PsychProcess)-[r:UNDERLIES]->(:Symptom) RETURN count(r) AS psych_underlies_symptom_count;

// ---- CHECK 6b: No legacy :BELONGS_TO relationships remain ----
// Expected: 0
MATCH ()-[r:BELONGS_TO]->() RETURN count(r) AS belongs_to_count;

// ---- CHECK 7: No denormalized Item.instrument_code remains ----
// Expected: 0 rows
MATCH (q:Item) WHERE q.instrument_code IS NOT NULL RETURN count(q);

// ---- CHECK 8: No Session.dominant_emotion string remains ----
// Expected: 0 rows
MATCH (s:Session) WHERE s.dominant_emotion IS NOT NULL RETURN count(s);

// ---- CHECK 9: All Trigger/Emotion keys use `slug`, not `label` ----
// Expected: both rows 0
MATCH (t:Trigger) WHERE t.label IS NOT NULL RETURN 'Trigger with label' AS issue, count(t);
MATCH (e:Emotion) WHERE e.label IS NOT NULL RETURN 'Emotion with label' AS issue, count(e);

// ---- CHECK 9a (strict): Trigger / Emotion must have name_en (v3 display contract) ----
// Expected: 0 rows
MATCH (t:Trigger) WHERE t.name_en IS NULL OR trim(t.name_en) = '' RETURN 'Trigger missing name_en' AS issue, t.slug AS slug;
MATCH (e:Emotion) WHERE e.name_en IS NULL OR trim(e.name_en) = '' RETURN 'Emotion missing name_en' AS issue, e.slug AS slug;

// ---- CHECK 9b (strict): Seeded Resource should have type + language for indexing ----
// Expected: 0 rows (adjust if you add Resources without these fields)
MATCH (r:Resource)
WHERE r.type IS NULL OR trim(toString(r.type)) = ''
   OR r.language IS NULL OR trim(toString(r.language)) = ''
RETURN r.resource_id, r.title_vi, r.type, r.language;

// ---- CHECK 10: Summary counts by label ----
MATCH (n)
UNWIND labels(n) AS lbl
RETURN lbl, count(*) AS node_count
ORDER BY lbl;

// ---- CHECK 11: Summary counts by relationship type ----
MATCH ()-[r]->()
RETURN type(r) AS rel_type, count(*) AS rel_count
ORDER BY rel_type;

// ---- CHECK 12: Trigger "meditate" issue is resolved ----
MATCH (r:Resource)-[:IN_RESOURCE_CATEGORY]->(rc:ResourceCategory)
RETURN rc.name_vi AS category, collect(r.title_vi) AS resources
ORDER BY category;

// ---- CHECK 13 (strict): Parallel duplicate relationships (same type + same properties) ----
// Expected: 0 rows — indicates missing MERGE or double seed
MATCH (a)-[r]->(b)
WITH a, b, type(r) AS relType, properties(r) AS props, count(r) AS parallel
WHERE parallel > 1
RETURN labels(a) AS from_labels, coalesce(a.slug, a.code, a.resource_id, elementId(a)) AS from_key,
       relType, labels(b) AS to_labels, coalesce(b.slug, b.code, b.resource_id, elementId(b)) AS to_key,
       props, parallel;

// ---- CHECK 14 (strict): DiagnosticCriterion orphan (no incoming HAS_CRITERION) ----
// Expected: 0 rows for production graph; informational if you only store criteria linked to disorders
MATCH (c:DiagnosticCriterion)
WHERE NOT ()-[:HAS_CRITERION]->(c)
RETURN c.code AS orphan_criterion;

// ---- CHECK 15 (strict): Seeded disorders mdd / gad should have HAS_CRITERION ----
// Expected: 0 rows if bootstrap ran; if disorder missing entirely, no row (not flagged)
UNWIND ['mdd', 'gad'] AS expected_slug
OPTIONAL MATCH (d:Disorder {slug: expected_slug})
OPTIONAL MATCH (d)-[:HAS_CRITERION]->(crit:DiagnosticCriterion)
WITH expected_slug, d, count(crit) AS n
WHERE d IS NOT NULL AND n = 0
RETURN expected_slug AS slug_missing_criteria, 'missing HAS_CRITERION' AS issue;

// ---- CHECK 16 (informational): Runtime tier — Session / MemoryNode / User counts ----
MATCH (u:User) RETURN 'User' AS label, count(u) AS n
UNION ALL
MATCH (s:Session) RETURN 'Session' AS label, count(s) AS n
UNION ALL
MATCH (m:MemoryNode) RETURN 'MemoryNode' AS label, count(m) AS n;

// ---- CHECK 17 (strict): EXPERIENCED edge should carry count + first_seen + last_seen ----
// Expected: 0 for well-formed runtime edges
MATCH ()-[r:EXPERIENCED]->()
WHERE r.count IS NULL OR r.last_seen IS NULL OR r.first_seen IS NULL
RETURN count(r) AS bad_experienced_edges;

// ---- CHECK 17b (strict): FELT edge should carry count + first_seen + last_seen ----
MATCH ()-[r:FELT]->()
WHERE r.count IS NULL OR r.last_seen IS NULL OR r.first_seen IS NULL
RETURN count(r) AS bad_felt_edges;

// ---- CHECK 17c (strict): USED_COPING edge should carry count + first_used + last_used ----
MATCH ()-[r:USED_COPING]->()
WHERE r.count IS NULL OR r.last_used IS NULL OR r.first_used IS NULL
RETURN count(r) AS bad_used_coping_edges;

// ---- CHECK 18 (after patch): CopingAction must declare is_adaptive when Agent nodes exist ----
// Expected: 0 rows when patch ran; skip if no Agent (core-only graph)
MATCH (:Agent)
WITH count(*) AS agentCount
WHERE agentCount >= 1
MATCH (c:CopingAction)
WHERE c.is_adaptive IS NULL
RETURN c.action_id AS missing_is_adaptive;

// ---- CHECK 19 (after patch): core Agents + capabilities present ----
// Expected: 3 agents, 3 capabilities if patch applied once
OPTIONAL MATCH (ag:Agent)
OPTIONAL MATCH (cap:AgentCapability)
RETURN count(DISTINCT ag) AS agents, count(DISTINCT cap) AS capabilities;

// ---- CHECK 20a (after patch): EVOKES edges exist ----
// Expected: count > 0 when patch ran; 0 if core-only
MATCH ()-[r:EVOKES]->() RETURN count(r) AS evokes_rels;

// ---- CHECK 20b (after patch): HANDLES_DOMAIN edges exist ----
MATCH ()-[h:HANDLES_DOMAIN]->() RETURN count(h) AS handles_domain_rels;

// Expected output shape (CHECK 12):
//   "Chánh niệm"       → ["Thiền cho người lo âu"]
//   "Hơi thở"          → ["Thở 4-7-8"]
//   "Âm thanh ngủ"     → ["The Midnight Woods"]
//   "Giáo dục CBT"     → ["Nhận diện suy nghĩ tiêu cực"]
