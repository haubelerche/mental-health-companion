// =============================================================================
// CBT FOR DUMMIES ENRICHMENT PATCH
// Generated from: backend/app/data/data_raw/cbt_dummies_extracted.json
// Source PDF: docs/cognitive-behavioural-therapy-for-dummies-copy.pdf
// =============================================================================

// ---------- 1) CognitiveDistortion candidates ----------
MERGE (d1:CognitiveDistortion {slug: 'core_belief_globalizing'})
SET d1.name_en = 'Core belief globalizing',
    d1.name_vi = coalesce(d1.name_vi, 'Niềm tin cốt lõi toàn cục tiêu cực'),
    d1.definition_en = 'Rigid global negative self-beliefs.',
    d1.definition_vi = 'Niềm tin cốt lõi cứng nhắc, tiêu cực và khái quát về bản thân.';

MERGE (d2:CognitiveDistortion {slug: 'all_or_nothing'})
SET d2.name_en = 'All-or-nothing thinking',
    d2.name_vi = coalesce(d2.name_vi, 'Tư duy tất cả hoặc không'),
    d2.definition_en = 'Binary evaluations with no gradient.',
    d2.definition_vi = 'Đánh giá theo hai cực tuyệt đối, thiếu sắc thái trung gian.';

MERGE (d3:CognitiveDistortion {slug: 'mental_filter'})
SET d3.name_en = 'Mental filter',
    d3.name_vi = coalesce(d3.name_vi, 'Bộ lọc tinh thần tiêu cực'),
    d3.definition_en = 'Selective attention to negative information.',
    d3.definition_vi = 'Chọn lọc chú ý vào thông tin tiêu cực và bỏ qua bằng chứng tích cực.';

MATCH (d:CognitiveDistortion {slug: 'core_belief_globalizing'}), (s:Symptom {slug: 'low_mood'})
MERGE (d)-[:AMPLIFIES {strength: 0.80, source: 'cbt_dummies'}]->(s);
MATCH (d:CognitiveDistortion {slug: 'core_belief_globalizing'}), (s:Symptom {slug: 'guilt'})
MERGE (d)-[:AMPLIFIES {strength: 0.73, source: 'cbt_dummies'}]->(s);
MATCH (d:CognitiveDistortion {slug: 'all_or_nothing'}), (s:Symptom {slug: 'low_mood'})
MERGE (d)-[:AMPLIFIES {strength: 0.71, source: 'cbt_dummies'}]->(s);
MATCH (d:CognitiveDistortion {slug: 'mental_filter'}), (s:Symptom {slug: 'excessive_worry'})
MERGE (d)-[:AMPLIFIES {strength: 0.67, source: 'cbt_dummies'}]->(s);

// ---------- 2) CopingAction candidates ----------
MERGE (ca1:CopingAction {action_id: 'thought_recording'})
SET ca1.name_en = 'Thought Record',
    ca1.name_vi = coalesce(ca1.name_vi, 'Ghi nhật ký suy nghĩ'),
    ca1.is_adaptive = true;

MERGE (ca2:CopingAction {action_id: 'erp'})
SET ca2.name_en = 'Exposure and Response Prevention',
    ca2.name_vi = coalesce(ca2.name_vi, 'Phơi nhiễm và ngăn đáp ứng'),
    ca2.is_adaptive = true;

MERGE (ca3:CopingAction {action_id: 'activity_scheduling'})
SET ca3.name_en = 'Activity Scheduling',
    ca3.name_vi = coalesce(ca3.name_vi, 'Lập lịch hoạt động'),
    ca3.is_adaptive = true;

MATCH (a:CopingAction {action_id: 'thought_recording'}), (c:CopingCategory {slug: 'cognitive'})
MERGE (a)-[:IN_COPING_CATEGORY]->(c);
MATCH (a:CopingAction {action_id: 'erp'}), (c:CopingCategory {slug: 'behavioral'})
MERGE (a)-[:IN_COPING_CATEGORY]->(c);
MATCH (a:CopingAction {action_id: 'activity_scheduling'}), (c:CopingCategory {slug: 'behavioral'})
MERGE (a)-[:IN_COPING_CATEGORY]->(c);

MATCH (a:CopingAction {action_id: 'thought_recording'}), (s:Symptom {slug: 'low_mood'})
MERGE (a)-[:TARGETS_SYMPTOM {strength: 0.68, source: 'cbt_dummies'}]->(s);
MATCH (a:CopingAction {action_id: 'thought_recording'}), (s:Symptom {slug: 'guilt'})
MERGE (a)-[:TARGETS_SYMPTOM {strength: 0.66, source: 'cbt_dummies'}]->(s);
MATCH (a:CopingAction {action_id: 'erp'}), (s:Symptom {slug: 'excessive_worry'})
MERGE (a)-[:TARGETS_SYMPTOM {strength: 0.74, source: 'cbt_dummies'}]->(s);
MATCH (a:CopingAction {action_id: 'erp'}), (s:Symptom {slug: 'hypervigilance'})
MERGE (a)-[:TARGETS_SYMPTOM {strength: 0.72, source: 'cbt_dummies'}]->(s);
MATCH (a:CopingAction {action_id: 'activity_scheduling'}), (s:Symptom {slug: 'anhedonia'})
MERGE (a)-[:TARGETS_SYMPTOM {strength: 0.76, source: 'cbt_dummies'}]->(s);
MATCH (a:CopingAction {action_id: 'activity_scheduling'}), (s:Symptom {slug: 'social_withdrawal'})
MERGE (a)-[:TARGETS_SYMPTOM {strength: 0.74, source: 'cbt_dummies'}]->(s);

MATCH (a:CopingAction {action_id: 'thought_recording'}), (d:Disorder {slug: 'mdd'})
MERGE (a)-[:HELPS_WITH {source: 'cbt_dummies'}]->(d);
MATCH (a:CopingAction {action_id: 'thought_recording'}), (d:Disorder {slug: 'gad'})
MERGE (a)-[:HELPS_WITH {source: 'cbt_dummies'}]->(d);
MATCH (a:CopingAction {action_id: 'erp'}), (d:Disorder {slug: 'ocd'})
MERGE (a)-[:HELPS_WITH {source: 'cbt_dummies'}]->(d);
MATCH (a:CopingAction {action_id: 'activity_scheduling'}), (d:Disorder {slug: 'mdd'})
MERGE (a)-[:HELPS_WITH {source: 'cbt_dummies'}]->(d);
MATCH (a:CopingAction {action_id: 'activity_scheduling'}), (d:Disorder {slug: 'pdd'})
MERGE (a)-[:HELPS_WITH {source: 'cbt_dummies'}]->(d);

// ---------- 3) PsychProcess candidates ----------
MERGE (p1:PsychProcess {slug: 'schema_activation'})
SET p1.name_en = 'Schema Activation',
    p1.name_vi = coalesce(p1.name_vi, 'Kích hoạt lược đồ nhận thức'),
    p1.definition_en = 'Activation of deep cognitive templates.',
    p1.definition_vi = 'Kích hoạt các lược đồ nhận thức sâu định hình cách diễn giải tình huống.';

MATCH (p:PsychProcess {slug: 'schema_activation'}), (c:Construct {slug: 'cognition'})
MERGE (p)-[:UNDERLIES]->(c);
MATCH (p:PsychProcess {slug: 'schema_activation'}), (s:Symptom {slug: 'low_mood'})
MERGE (p)-[:PSYCH_BASIS_FOR {source: 'cbt_dummies'}]->(s);
MATCH (p:PsychProcess {slug: 'schema_activation'}), (s:Symptom {slug: 'excessive_worry'})
MERGE (p)-[:PSYCH_BASIS_FOR {source: 'cbt_dummies'}]->(s);
