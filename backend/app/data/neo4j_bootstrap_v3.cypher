// =============================================================================
// SECTION 1 — CONSTRAINTS
// =============================================================================

// Tier 1: Foundations
CREATE CONSTRAINT construct_slug          IF NOT EXISTS FOR (n:Construct)          REQUIRE n.slug IS UNIQUE;
CREATE CONSTRAINT psychprocess_slug       IF NOT EXISTS FOR (n:PsychProcess)       REQUIRE n.slug IS UNIQUE;
CREATE CONSTRAINT term_slug               IF NOT EXISTS FOR (n:Term)               REQUIRE n.slug IS UNIQUE;

// Tier 2: Clinical
CREATE CONSTRAINT disorder_slug           IF NOT EXISTS FOR (n:Disorder)           REQUIRE n.slug IS UNIQUE;
CREATE CONSTRAINT disorder_category_slug  IF NOT EXISTS FOR (n:DisorderCategory)   REQUIRE n.slug IS UNIQUE;
CREATE CONSTRAINT episode_slug            IF NOT EXISTS FOR (n:Episode)            REQUIRE n.slug IS UNIQUE;
CREATE CONSTRAINT criterion_code          IF NOT EXISTS FOR (n:DiagnosticCriterion) REQUIRE n.code IS UNIQUE;
CREATE CONSTRAINT symptom_slug            IF NOT EXISTS FOR (n:Symptom)            REQUIRE n.slug IS UNIQUE;
CREATE CONSTRAINT symptom_category_slug   IF NOT EXISTS FOR (n:SymptomCategory)    REQUIRE n.slug IS UNIQUE;
CREATE CONSTRAINT instrument_code         IF NOT EXISTS FOR (n:Instrument)         REQUIRE n.code IS UNIQUE;
CREATE CONSTRAINT item_code               IF NOT EXISTS FOR (n:Item)               REQUIRE n.code IS UNIQUE;
CREATE CONSTRAINT substance_slug          IF NOT EXISTS FOR (n:Substance)          REQUIRE n.slug IS UNIQUE;
CREATE CONSTRAINT medical_condition_slug  IF NOT EXISTS FOR (n:MedicalCondition)   REQUIRE n.slug IS UNIQUE;
CREATE CONSTRAINT distortion_slug         IF NOT EXISTS FOR (n:CognitiveDistortion) REQUIRE n.slug IS UNIQUE;

// Tier 3: Intervention + User
CREATE CONSTRAINT resource_id             IF NOT EXISTS FOR (n:Resource)           REQUIRE n.resource_id IS UNIQUE;
CREATE CONSTRAINT resource_category_slug  IF NOT EXISTS FOR (n:ResourceCategory)   REQUIRE n.slug IS UNIQUE;
CREATE CONSTRAINT coping_action_id        IF NOT EXISTS FOR (n:CopingAction)       REQUIRE n.action_id IS UNIQUE;
CREATE CONSTRAINT coping_category_slug    IF NOT EXISTS FOR (n:CopingCategory)     REQUIRE n.slug IS UNIQUE;
CREATE CONSTRAINT trigger_slug            IF NOT EXISTS FOR (n:Trigger)            REQUIRE n.slug IS UNIQUE;
CREATE CONSTRAINT emotion_slug            IF NOT EXISTS FOR (n:Emotion)            REQUIRE n.slug IS UNIQUE;
CREATE CONSTRAINT safety_keyword_phrase   IF NOT EXISTS FOR (n:SafetyKeyword)      REQUIRE n.phrase IS UNIQUE;
CREATE CONSTRAINT user_id                 IF NOT EXISTS FOR (n:User)               REQUIRE n.user_id IS UNIQUE;
CREATE CONSTRAINT session_id              IF NOT EXISTS FOR (n:Session)            REQUIRE n.session_id IS UNIQUE;
// RiskProfile — explainability / audit theo session (docs/description.md §VI.2); worker MERGE theo profile_id
CREATE CONSTRAINT risk_profile_id         IF NOT EXISTS FOR (n:RiskProfile)         REQUIRE n.profile_id IS UNIQUE;
CREATE CONSTRAINT memory_node_id          IF NOT EXISTS FOR (n:MemoryNode)         REQUIRE n.memory_id IS UNIQUE;

// GraphRAG / Multi-Agent / Assessment (seed + runtime shapes; optional patch extends data)
CREATE CONSTRAINT agent_slug                IF NOT EXISTS FOR (a:Agent)               REQUIRE a.slug IS UNIQUE;
CREATE CONSTRAINT agent_capability_slug    IF NOT EXISTS FOR (c:AgentCapability)     REQUIRE c.slug IS UNIQUE;
CREATE CONSTRAINT assessment_id            IF NOT EXISTS FOR (a:Assessment)          REQUIRE a.assessment_id IS UNIQUE;


// =============================================================================
// SECTION 2 — INDEXES
// =============================================================================

CREATE FULLTEXT INDEX idx_symptom_fulltext IF NOT EXISTS
    FOR (s:Symptom) ON EACH [s.name_vi, s.name_en, s.definition];
CREATE FULLTEXT INDEX idx_disorder_fulltext IF NOT EXISTS
    FOR (d:Disorder) ON EACH [d.name_vi, d.name_en, d.definition];
CREATE FULLTEXT INDEX idx_term_fulltext IF NOT EXISTS
    FOR (t:Term) ON EACH [t.name_vi, t.name_en, t.definition_vi];



CREATE INDEX idx_disorder_icd    IF NOT EXISTS FOR (n:Disorder) ON (n.icd_code);
CREATE INDEX idx_disorder_dsm5   IF NOT EXISTS FOR (n:Disorder) ON (n.dsm5_code);
CREATE INDEX idx_session_sos     IF NOT EXISTS FOR (s:Session) ON (s.sos_triggered);
CREATE INDEX idx_session_started IF NOT EXISTS FOR (s:Session) ON (s.started_at);
CREATE INDEX idx_session_risk_updated IF NOT EXISTS FOR (s:Session) ON (s.risk_updated_at);
CREATE INDEX idx_risk_profile_created IF NOT EXISTS FOR (p:RiskProfile) ON (p.created_at);
CREATE INDEX idx_experienced_last_seen     IF NOT EXISTS FOR ()-[r:EXPERIENCED]-()  ON (r.last_seen);
CREATE INDEX idx_experienced_count         IF NOT EXISTS FOR ()-[r:EXPERIENCED]-()  ON (r.count);
CREATE INDEX idx_felt_last_seen            IF NOT EXISTS FOR ()-[r:FELT]-()          ON (r.last_seen);
CREATE INDEX idx_used_coping_last_used     IF NOT EXISTS FOR ()-[r:USED_COPING]-()   ON (r.last_used);
CREATE INDEX idx_used_coping_effectiveness IF NOT EXISTS FOR ()-[r:USED_COPING]-()   ON (r.effectiveness);
// idx_item_instrument removed: instrument_code property was dropped in v3 (CHANGES #2)
CREATE INDEX idx_user_email IF NOT EXISTS FOR (n:User) ON (n.email);
CREATE INDEX idx_resource_type IF NOT EXISTS FOR (n:Resource) ON (n.type);
CREATE INDEX idx_resource_language IF NOT EXISTS FOR (n:Resource) ON (n.language);



// =============================================================================
// SECTION 3 — TAXONOMY NODES
// =============================================================================

// ---------- 3.1 SymptomCategory ----------

MERGE (sc1:SymptomCategory {slug: 'mood'})      SET sc1.name_vi = 'Tâm trạng',    sc1.name_en = 'Mood';
MERGE (sc2:SymptomCategory {slug: 'anxiety'})   SET sc2.name_vi = 'Lo âu',        sc2.name_en = 'Anxiety';
MERGE (sc3:SymptomCategory {slug: 'sleep'})     SET sc3.name_vi = 'Giấc ngủ',     sc3.name_en = 'Sleep';
MERGE (sc4:SymptomCategory {slug: 'energy'})    SET sc4.name_vi = 'Năng lượng',   sc4.name_en = 'Energy';
MERGE (sc5:SymptomCategory {slug: 'cognition'}) SET sc5.name_vi = 'Nhận thức',    sc5.name_en = 'Cognition';
MERGE (sc6:SymptomCategory {slug: 'somatic'})   SET sc6.name_vi = 'Cơ thể',       sc6.name_en = 'Somatic';
MERGE (sc7:SymptomCategory {slug: 'safety'})    SET sc7.name_vi = 'An toàn',      sc7.name_en = 'Safety';
MERGE (sc8:SymptomCategory {slug: 'psychotic'}) SET sc8.name_vi = 'Loạn thần',    sc8.name_en = 'Psychotic';
MERGE (sc9:SymptomCategory {slug: 'behavioral'}) SET sc9.name_vi = 'Hành vi',     sc9.name_en = 'Behavioral';

// ---------- 3.2 ResourceCategory (+ hierarchy) ----------

MERGE (rc_med:ResourceCategory {slug: 'meditate'})      SET rc_med.name_vi = 'Thiền',           rc_med.name_en = 'Meditation';
MERGE (rc_slp:ResourceCategory {slug: 'sleep'})         SET rc_slp.name_vi = 'Giấc ngủ',        rc_slp.name_en = 'Sleep';
MERGE (rc_wis:ResourceCategory {slug: 'wisdom'})        SET rc_wis.name_vi = 'Tri thức tâm lý', rc_wis.name_en = 'Wisdom';

// Sub-categories under meditate
MERGE (rc_breath:ResourceCategory {slug: 'breathwork'})      SET rc_breath.name_vi = 'Hơi thở',        rc_breath.name_en = 'Breathwork';
MERGE (rc_mind:ResourceCategory  {slug: 'mindfulness'})      SET rc_mind.name_vi  = 'Chánh niệm',      rc_mind.name_en  = 'Mindfulness';
MERGE (rc_body:ResourceCategory  {slug: 'body_scan'})        SET rc_body.name_vi  = 'Quét cơ thể',     rc_body.name_en  = 'Body scan';
MERGE (rc_lk:ResourceCategory    {slug: 'loving_kindness'})  SET rc_lk.name_vi    = 'Từ bi',            rc_lk.name_en    = 'Loving-kindness';
MERGE (rc_breath)-[:SUBCATEGORY_OF]->(rc_med);
MERGE (rc_mind)-[:SUBCATEGORY_OF]->(rc_med);
MERGE (rc_body)-[:SUBCATEGORY_OF]->(rc_med);
MERGE (rc_lk)-[:SUBCATEGORY_OF]->(rc_med);

// Sub-categories under sleep
MERGE (rc_sound:ResourceCategory {slug: 'sleep_soundscape'}) SET rc_sound.name_vi = 'Âm thanh ngủ',      rc_sound.name_en = 'Sleep soundscape';
MERGE (rc_hyg:ResourceCategory   {slug: 'sleep_hygiene'})    SET rc_hyg.name_vi   = 'Vệ sinh giấc ngủ',  rc_hyg.name_en   = 'Sleep hygiene';
MERGE (rc_sound)-[:SUBCATEGORY_OF]->(rc_slp);
MERGE (rc_hyg)-[:SUBCATEGORY_OF]->(rc_slp);

// Sub-categories under wisdom
MERGE (rc_cbt:ResourceCategory {slug: 'cbt_education'})   SET rc_cbt.name_vi = 'Giáo dục CBT',    rc_cbt.name_en = 'CBT education';
MERGE (rc_psy:ResourceCategory {slug: 'psychoeducation'}) SET rc_psy.name_vi = 'Tâm lý giáo dục', rc_psy.name_en = 'Psychoeducation';
MERGE (rc_cbt)-[:SUBCATEGORY_OF]->(rc_wis);
MERGE (rc_psy)-[:SUBCATEGORY_OF]->(rc_wis);

// ---------- 3.3 CopingCategory ----------

MERGE (cop1:CopingCategory {slug: 'behavioral'}) SET cop1.name_vi = 'Hành vi',   cop1.name_en = 'Behavioral';
MERGE (cop2:CopingCategory {slug: 'cognitive'})  SET cop2.name_vi = 'Nhận thức', cop2.name_en = 'Cognitive';
MERGE (cop3:CopingCategory {slug: 'somatic'})    SET cop3.name_vi = 'Cơ thể',    cop3.name_en = 'Somatic';
MERGE (cop4:CopingCategory {slug: 'social'})     SET cop4.name_vi = 'Xã hội',    cop4.name_en = 'Social';

// ---------- 3.4 DisorderCategory (17 chapters of DSM-5) ----------
// Ch.1
MERGE (dc_nd:DisorderCategory   {slug: 'neurodevelopmental_disorders'})    SET dc_nd.name_vi   = 'Rối loạn phát triển thần kinh',         dc_nd.name_en   = 'Neurodevelopmental Disorders',         dc_nd.dsm5_chapter = 1;
// Ch.2
MERGE (dc_psy:DisorderCategory  {slug: 'psychotic_disorders'})             SET dc_psy.name_vi  = 'Rối loạn phổ tâm thần phân liệt',       dc_psy.name_en  = 'Schizophrenia Spectrum & Psychotic Disorders', dc_psy.dsm5_chapter = 2;
// Ch.3  (tách khỏi mood_disorders — DSM-5 coi Bipolar là chapter riêng)
MERGE (dc_bip:DisorderCategory  {slug: 'bipolar_disorders'})               SET dc_bip.name_vi  = 'Rối loạn lưỡng cực',                    dc_bip.name_en  = 'Bipolar & Related Disorders',          dc_bip.dsm5_chapter = 3;
// Ch.4  (chỉ depressive, KHÔNG gộp bipolar)
MERGE (dc_dep:DisorderCategory  {slug: 'depressive_disorders'})            SET dc_dep.name_vi  = 'Rối loạn trầm cảm',                     dc_dep.name_en  = 'Depressive Disorders',                  dc_dep.dsm5_chapter = 4;
// Ch.5
MERGE (dc_anx:DisorderCategory  {slug: 'anxiety_disorders'})               SET dc_anx.name_vi  = 'Rối loạn lo âu',                        dc_anx.name_en  = 'Anxiety Disorders',                    dc_anx.dsm5_chapter = 5;
// Ch.6
MERGE (dc_ocd:DisorderCategory  {slug: 'obsessive_compulsive_disorders'})  SET dc_ocd.name_vi  = 'Rối loạn ám ảnh cưỡng chế',             dc_ocd.name_en  = 'Obsessive-Compulsive & Related Disorders', dc_ocd.dsm5_chapter = 6;
// Ch.7
MERGE (dc_tra:DisorderCategory  {slug: 'trauma_stress_disorders'})         SET dc_tra.name_vi  = 'Rối loạn liên quan sang chấn & stress',  dc_tra.name_en  = 'Trauma & Stressor-Related Disorders',  dc_tra.dsm5_chapter = 7;
// Ch.8
MERGE (dc_dis:DisorderCategory  {slug: 'dissociative_disorders'})          SET dc_dis.name_vi  = 'Rối loạn phân ly',                      dc_dis.name_en  = 'Dissociative Disorders',                dc_dis.dsm5_chapter = 8;
// Ch.9
MERGE (dc_som:DisorderCategory  {slug: 'somatic_symptom_disorders'})       SET dc_som.name_vi  = 'Rối loạn triệu chứng cơ thể',           dc_som.name_en  = 'Somatic Symptom & Related Disorders',  dc_som.dsm5_chapter = 9;
// Ch.10
MERGE (dc_eat:DisorderCategory  {slug: 'feeding_eating_disorders'})        SET dc_eat.name_vi  = 'Rối loạn ăn uống',                      dc_eat.name_en  = 'Feeding & Eating Disorders',           dc_eat.dsm5_chapter = 10;
// Ch.11
MERGE (dc_eli:DisorderCategory  {slug: 'elimination_disorders'})           SET dc_eli.name_vi  = 'Rối loạn bài tiết',                     dc_eli.name_en  = 'Elimination Disorders',                dc_eli.dsm5_chapter = 11;
// Ch.12
MERGE (dc_slp:DisorderCategory  {slug: 'sleep_wake_disorders'})            SET dc_slp.name_vi  = 'Rối loạn thức-ngủ',                     dc_slp.name_en  = 'Sleep-Wake Disorders',                 dc_slp.dsm5_chapter = 12;
// Ch.13
MERGE (dc_sex:DisorderCategory  {slug: 'sexual_dysfunctions'})             SET dc_sex.name_vi  = 'Rối loạn chức năng tình dục',           dc_sex.name_en  = 'Sexual Dysfunctions',                  dc_sex.dsm5_chapter = 13;
// Ch.14
MERGE (dc_imp:DisorderCategory  {slug: 'disruptive_impulse_conduct'})      SET dc_imp.name_vi  = 'Rối loạn hành vi phá vỡ & kiểm soát xung động', dc_imp.name_en = 'Disruptive, Impulse-Control & Conduct Disorders', dc_imp.dsm5_chapter = 14;
// Ch.15
MERGE (dc_sub:DisorderCategory  {slug: 'substance_disorders'})             SET dc_sub.name_vi  = 'Rối loạn liên quan đến chất',           dc_sub.name_en  = 'Substance-Related & Addictive Disorders', dc_sub.dsm5_chapter = 15;
// Ch.16
MERGE (dc_ncg:DisorderCategory  {slug: 'neurocognitive_disorders'})        SET dc_ncg.name_vi  = 'Rối loạn thần kinh-nhận thức',          dc_ncg.name_en  = 'Neurocognitive Disorders',             dc_ncg.dsm5_chapter = 16;
// Ch.17
MERGE (dc_per:DisorderCategory  {slug: 'personality_disorders'})           SET dc_per.name_vi  = 'Rối loạn nhân cách',                    dc_per.name_en  = 'Personality Disorders',                dc_per.dsm5_chapter = 17;


// =============================================================================
// SECTION 4 — TIER 1: FOUNDATIONS (Psychology 101 textbook)
// =============================================================================

// ---------- 4.1 Construct (14 core psychological constructs) ----------

MERGE (c1:Construct {slug: 'cognition'})
    SET c1.name_vi = 'Nhận thức', c1.name_en = 'Cognition',
        c1.definition_vi = 'Quá trình tâm lý phản ánh hiện thực khách quan';
MERGE (c2:Construct {slug: 'emotion'})
    SET c2.name_vi = 'Cảm xúc', c2.name_en = 'Emotion',
        c2.definition_vi = 'Trạng thái tâm lý phản ánh thái độ của con người với sự vật';
MERGE (c3:Construct {slug: 'personality'})
    SET c3.name_vi = 'Nhân cách', c3.name_en = 'Personality',
        c3.definition_vi = 'Tổ hợp những thuộc tính tâm lý ổn định của cá nhân';
MERGE (c4:Construct {slug: 'temperament'})
    SET c4.name_vi = 'Khí chất', c4.name_en = 'Temperament',
        c4.definition_vi = 'Đặc điểm tâm lý cá nhân về cường độ và tốc độ hoạt động thần kinh';
MERGE (c5:Construct {slug: 'character'})
    SET c5.name_vi = 'Tính cách', c5.name_en = 'Character',
        c5.definition_vi = 'Hệ thống thái độ ổn định đối với hiện thực, thể hiện qua hành vi';
MERGE (c6:Construct {slug: 'ability'})
    SET c6.name_vi = 'Năng lực', c6.name_en = 'Ability',
        c6.definition_vi = 'Thuộc tính tâm lý đáp ứng yêu cầu của một hoạt động nhất định';
MERGE (c7:Construct {slug: 'motivation'})
    SET c7.name_vi = 'Động cơ', c7.name_en = 'Motivation',
        c7.definition_vi = 'Cái thúc đẩy hành động nhằm thoả mãn nhu cầu';
MERGE (c8:Construct {slug: 'need'})
    SET c8.name_vi = 'Nhu cầu', c8.name_en = 'Need',
        c8.definition_vi = 'Đòi hỏi cần được thoả mãn để tồn tại và phát triển';
MERGE (c9:Construct {slug: 'will'})
    SET c9.name_vi = 'Ý chí', c9.name_en = 'Will',
        c9.definition_vi = 'Năng lực điều khiển, điều chỉnh hành vi có ý thức';
MERGE (c10:Construct {slug: 'consciousness'})
    SET c10.name_vi = 'Ý thức', c10.name_en = 'Consciousness',
        c10.definition_vi = 'Hình thức phản ánh tâm lý cao nhất của con người';
MERGE (c11:Construct {slug: 'activity'})
    SET c11.name_vi = 'Hoạt động', c11.name_en = 'Activity',
        c11.definition_vi = 'Phương thức tồn tại của con người, quan hệ tích cực với thế giới';
MERGE (c12:Construct {slug: 'communication'})
    SET c12.name_vi = 'Giao tiếp', c12.name_en = 'Communication',
        c12.definition_vi = 'Quá trình tiếp xúc tâm lý giữa người với người';
MERGE (c13:Construct {slug: 'self_awareness'})
    SET c13.name_vi = 'Tự ý thức', c13.name_en = 'Self-awareness',
        c13.definition_vi = 'Ý thức về bản thân mình';
MERGE (c14:Construct {slug: 'interest'})
    SET c14.name_vi = 'Hứng thú', c14.name_en = 'Interest',
        c14.definition_vi = 'Thái độ lựa chọn đặc biệt đối với đối tượng';

// ---------- 4.2 PsychProcess (8 basic processes) ----------

MERGE (p1:PsychProcess {slug: 'sensation'})
    SET p1.name_vi = 'Cảm giác', p1.name_en = 'Sensation',
        p1.definition_vi = 'Phản ánh từng thuộc tính riêng lẻ của sự vật khi tác động lên giác quan';
MERGE (p2:PsychProcess {slug: 'perception'})
    SET p2.name_vi = 'Tri giác', p2.name_en = 'Perception',
        p2.definition_vi = 'Phản ánh trọn vẹn các thuộc tính của sự vật khi tác động trực tiếp';
MERGE (p3:PsychProcess {slug: 'thinking'})
    SET p3.name_vi = 'Tư duy', p3.name_en = 'Thinking',
        p3.definition_vi = 'Quá trình nhận thức phản ánh các thuộc tính bản chất và mối quan hệ của sự vật';
MERGE (p4:PsychProcess {slug: 'imagination'})
    SET p4.name_vi = 'Tưởng tượng', p4.name_en = 'Imagination',
        p4.definition_vi = 'Quá trình tạo ra hình ảnh mới trên cơ sở hình ảnh đã có';
MERGE (p5:PsychProcess {slug: 'memory'})
    SET p5.name_vi = 'Trí nhớ', p5.name_en = 'Memory',
        p5.definition_vi = 'Quá trình ghi nhận, gìn giữ và tái hiện kinh nghiệm';
MERGE (p6:PsychProcess {slug: 'attention'})
    SET p6.name_vi = 'Chú ý', p6.name_en = 'Attention',
        p6.definition_vi = 'Sự tập trung của ý thức vào một hay vài đối tượng';
MERGE (p7:PsychProcess {slug: 'language'})
    SET p7.name_vi = 'Ngôn ngữ', p7.name_en = 'Language',
        p7.definition_vi = 'Phương tiện giao tiếp và công cụ của tư duy';
MERGE (p8:PsychProcess {slug: 'affect'})
    SET p8.name_vi = 'Xúc cảm', p8.name_en = 'Affect',
        p8.definition_vi = 'Rung động trực tiếp mang tính tình huống';

// Link PsychProcess → Construct only (:UNDERLIES). Bridges to Symptom use :PSYCH_BASIS_FOR (§5.2).
MATCH (p:PsychProcess {slug: 'sensation'}),  (c:Construct {slug: 'cognition'}) MERGE (p)-[:UNDERLIES]->(c);
MATCH (p:PsychProcess {slug: 'perception'}), (c:Construct {slug: 'cognition'}) MERGE (p)-[:UNDERLIES]->(c);
MATCH (p:PsychProcess {slug: 'thinking'}),   (c:Construct {slug: 'cognition'}) MERGE (p)-[:UNDERLIES]->(c);
MATCH (p:PsychProcess {slug: 'imagination'}),(c:Construct {slug: 'cognition'}) MERGE (p)-[:UNDERLIES]->(c);
MATCH (p:PsychProcess {slug: 'memory'}),     (c:Construct {slug: 'cognition'}) MERGE (p)-[:UNDERLIES]->(c);
MATCH (p:PsychProcess {slug: 'attention'}),  (c:Construct {slug: 'cognition'}) MERGE (p)-[:UNDERLIES]->(c);
MATCH (p:PsychProcess {slug: 'language'}),   (c:Construct {slug: 'cognition'}) MERGE (p)-[:UNDERLIES]->(c);
MATCH (p:PsychProcess {slug: 'affect'}),     (c:Construct {slug: 'emotion'})   MERGE (p)-[:UNDERLIES]->(c);

// ---------- 4.3 Term (core glossary, extensible) ----------

MERGE (t1:Term {slug: 'prodromal'})
    SET t1.name_vi = 'Tiền triệu', t1.name_en = 'Prodromal',
        t1.definition_vi = 'Giai đoạn triệu chứng sớm, nhẹ trước khi bệnh bùng phát đầy đủ',
        t1.source = 'DSM-5';
MERGE (t2:Term {slug: 'residual'})
    SET t2.name_vi = 'Di chứng', t2.name_en = 'Residual',
        t2.definition_vi = 'Triệu chứng còn sót lại sau giai đoạn bùng phát',
        t2.source = 'DSM-5';
MERGE (t3:Term {slug: 'remission'})
    SET t3.name_vi = 'Thuyên giảm', t3.name_en = 'Remission',
        t3.definition_vi = 'Giảm hoặc mất triệu chứng trong một thời gian',
        t3.source = 'DSM-5';
MERGE (t4:Term {slug: 'differential_diagnosis'})
    SET t4.name_vi = 'Chẩn đoán phân biệt', t4.name_en = 'Differential diagnosis',
        t4.definition_vi = 'Quy trình phân biệt bệnh này với các bệnh khác có triệu chứng tương tự',
        t4.source = 'DSM-5';
MERGE (t5:Term {slug: 'comorbidity'})
    SET t5.name_vi = 'Đồng mắc', t5.name_en = 'Comorbidity',
        t5.definition_vi = 'Sự xuất hiện đồng thời của hai hoặc nhiều rối loạn ở cùng một người',
        t5.source = 'DSM-5';


// =============================================================================
// SECTION 5 — TIER 2: CLINICAL (DSM-5 + SCID-5-CV seed)
// =============================================================================

// ---------- 5.1 Instrument + Item (PHQ-9, GAD-7) ----------

MERGE (phq9:Instrument {code: 'PHQ-9'})
    SET phq9.name = 'Patient Health Questionnaire-9', phq9.domain = 'depression', phq9.max_score = 27;
MERGE (gad7:Instrument {code: 'GAD-7'})
    SET gad7.name = 'Generalized Anxiety Disorder-7', gad7.domain = 'anxiety', gad7.max_score = 21;

// PHQ-9 items (một câu lệnh / Item+HAS_ITEM — Neo4j 5 Bolt chỉ một statement mỗi RUN; tách `;` làm mất scope biến)
MATCH (phq9:Instrument {code: 'PHQ-9'})
MERGE (phq_q1:Item {code: 'PHQ9_Q1'})
    SET phq_q1.order = 1, phq_q1.text_vi = 'Ít hứng thú hoặc không thấy vui khi làm bất cứ điều gì'
MERGE (phq9)-[:HAS_ITEM {order: 1}]->(phq_q1);
MATCH (phq9:Instrument {code: 'PHQ-9'})
MERGE (phq_q2:Item {code: 'PHQ9_Q2'})
    SET phq_q2.order = 2, phq_q2.text_vi = 'Cảm thấy chán nản, u sầu hoặc tuyệt vọng'
MERGE (phq9)-[:HAS_ITEM {order: 2}]->(phq_q2);
MATCH (phq9:Instrument {code: 'PHQ-9'})
MERGE (phq_q3:Item {code: 'PHQ9_Q3'})
    SET phq_q3.order = 3, phq_q3.text_vi = 'Khó ngủ, ngủ không yên hoặc ngủ quá nhiều'
MERGE (phq9)-[:HAS_ITEM {order: 3}]->(phq_q3);
MATCH (phq9:Instrument {code: 'PHQ-9'})
MERGE (phq_q4:Item {code: 'PHQ9_Q4'})
    SET phq_q4.order = 4, phq_q4.text_vi = 'Cảm thấy mệt mỏi hoặc ít năng lượng'
MERGE (phq9)-[:HAS_ITEM {order: 4}]->(phq_q4);
MATCH (phq9:Instrument {code: 'PHQ-9'})
MERGE (phq_q5:Item {code: 'PHQ9_Q5'})
    SET phq_q5.order = 5, phq_q5.text_vi = 'Ăn kém ngon hoặc ăn quá nhiều'
MERGE (phq9)-[:HAS_ITEM {order: 5}]->(phq_q5);
MATCH (phq9:Instrument {code: 'PHQ-9'})
MERGE (phq_q6:Item {code: 'PHQ9_Q6'})
    SET phq_q6.order = 6, phq_q6.text_vi = 'Cảm thấy tệ về bản thân — thất bại hoặc làm thất vọng bản thân/gia đình'
MERGE (phq9)-[:HAS_ITEM {order: 6}]->(phq_q6);
MATCH (phq9:Instrument {code: 'PHQ-9'})
MERGE (phq_q7:Item {code: 'PHQ9_Q7'})
    SET phq_q7.order = 7, phq_q7.text_vi = 'Khó tập trung vào mọi việc'
MERGE (phq9)-[:HAS_ITEM {order: 7}]->(phq_q7);
MATCH (phq9:Instrument {code: 'PHQ-9'})
MERGE (phq_q8:Item {code: 'PHQ9_Q8'})
    SET phq_q8.order = 8, phq_q8.text_vi = 'Chuyển động/nói chậm đến mức người khác nhận ra, hoặc bồn chồn không yên'
MERGE (phq9)-[:HAS_ITEM {order: 8}]->(phq_q8);
MATCH (phq9:Instrument {code: 'PHQ-9'})
MERGE (phq_q9:Item {code: 'PHQ9_Q9'})
    SET phq_q9.order = 9, phq_q9.text_vi = 'Có ý nghĩ rằng thà chết còn hơn, hoặc muốn tự làm hại bản thân'
MERGE (phq9)-[:HAS_ITEM {order: 9}]->(phq_q9);

// GAD-7 items (cùng nguyên tắc một statement / Item+HAS_ITEM)
MATCH (gad7:Instrument {code: 'GAD-7'})
MERGE (gad_q1:Item {code: 'GAD7_Q1'})
    SET gad_q1.order = 1, gad_q1.text_vi = 'Cảm thấy lo lắng, bồn chồn hoặc căng thẳng'
MERGE (gad7)-[:HAS_ITEM {order: 1}]->(gad_q1);
MATCH (gad7:Instrument {code: 'GAD-7'})
MERGE (gad_q2:Item {code: 'GAD7_Q2'})
    SET gad_q2.order = 2, gad_q2.text_vi = 'Không kiểm soát được lo lắng của bản thân'
MERGE (gad7)-[:HAS_ITEM {order: 2}]->(gad_q2);
MATCH (gad7:Instrument {code: 'GAD-7'})
MERGE (gad_q3:Item {code: 'GAD7_Q3'})
    SET gad_q3.order = 3, gad_q3.text_vi = 'Lo lắng quá nhiều về nhiều điều khác nhau'
MERGE (gad7)-[:HAS_ITEM {order: 3}]->(gad_q3);
MATCH (gad7:Instrument {code: 'GAD-7'})
MERGE (gad_q4:Item {code: 'GAD7_Q4'})
    SET gad_q4.order = 4, gad_q4.text_vi = 'Khó thư giãn'
MERGE (gad7)-[:HAS_ITEM {order: 4}]->(gad_q4);
MATCH (gad7:Instrument {code: 'GAD-7'})
MERGE (gad_q5:Item {code: 'GAD7_Q5'})
    SET gad_q5.order = 5, gad_q5.text_vi = 'Bồn chồn đến mức khó ngồi yên'
MERGE (gad7)-[:HAS_ITEM {order: 5}]->(gad_q5);
MATCH (gad7:Instrument {code: 'GAD-7'})
MERGE (gad_q6:Item {code: 'GAD7_Q6'})
    SET gad_q6.order = 6, gad_q6.text_vi = 'Dễ bực bội hoặc dễ cáu kỉnh'
MERGE (gad7)-[:HAS_ITEM {order: 6}]->(gad_q6);
MATCH (gad7:Instrument {code: 'GAD-7'})
MERGE (gad_q7:Item {code: 'GAD7_Q7'})
    SET gad_q7.order = 7, gad_q7.text_vi = 'Sợ rằng điều gì đó tồi tệ có thể xảy ra'
MERGE (gad7)-[:HAS_ITEM {order: 7}]->(gad_q7);

// ---------- 5.2 Symptom nodes (linked to SymptomCategory via :IN_SYMPTOM_CATEGORY) ----------
// definition field populates idx_symptom_fulltext — do not leave null.

MERGE (s_insomnia:Symptom {slug: 'insomnia'})
    SET s_insomnia.name_vi = 'Mất ngủ', s_insomnia.name_en = 'Insomnia',
        s_insomnia.definition = 'Khó đi vào giấc ngủ, duy trì giấc ngủ, hoặc thức dậy sớm gây suy giảm chức năng';
MERGE (s_fatigue:Symptom {slug: 'fatigue'})
    SET s_fatigue.name_vi = 'Mệt mỏi', s_fatigue.name_en = 'Fatigue',
        s_fatigue.definition = 'Cảm giác kiệt sức dai dẳng không giảm sau nghỉ ngơi, giảm năng lượng rõ rệt';
MERGE (s_anhedonia:Symptom {slug: 'anhedonia'})
    SET s_anhedonia.name_vi = 'Mất hứng thú', s_anhedonia.name_en = 'Anhedonia',
        s_anhedonia.definition = 'Giảm hoặc mất khả năng trải nghiệm niềm vui từ các hoạt động trước đây thú vị';
MERGE (s_low_mood:Symptom {slug: 'low_mood'})
    SET s_low_mood.name_vi = 'Tâm trạng thấp', s_low_mood.name_en = 'Low mood',
        s_low_mood.definition = 'Trạng thái buồn bã, trống rỗng hoặc tuyệt vọng kéo dài phần lớn trong ngày';
MERGE (s_guilt:Symptom {slug: 'guilt'})
    SET s_guilt.name_vi = 'Tự trách bản thân', s_guilt.name_en = 'Guilt',
        s_guilt.definition = 'Cảm giác vô dụng hoặc tội lỗi không phù hợp, có thể đạt mức hoang tưởng';
MERGE (s_poor_concentration:Symptom {slug: 'poor_concentration'})
    SET s_poor_concentration.name_vi = 'Khó tập trung', s_poor_concentration.name_en = 'Poor concentration',
        s_poor_concentration.definition = 'Giảm khả năng suy nghĩ, tập trung hoặc đưa ra quyết định';
MERGE (s_appetite_change:Symptom {slug: 'appetite_change'})
    SET s_appetite_change.name_vi = 'Thay đổi ăn uống', s_appetite_change.name_en = 'Appetite change',
        s_appetite_change.definition = 'Giảm hoặc tăng khẩu vị đáng kể dẫn đến thay đổi cân nặng không chủ đích';
MERGE (s_psychomotor:Symptom {slug: 'psychomotor_disturbance'})
    SET s_psychomotor.name_vi = 'Vận động chậm/bồn chồn', s_psychomotor.name_en = 'Psychomotor disturbance',
        s_psychomotor.definition = 'Chậm chạp tâm thần vận động hoặc bồn chồn kích động quan sát được bởi người khác';
MERGE (s_si:Symptom {slug: 'suicidal_ideation'})
    SET s_si.name_vi = 'Ý nghĩ tự hại', s_si.name_en = 'Suicidal ideation',
        s_si.definition = 'Suy nghĩ về cái chết, tự làm hại bản thân hoặc có kế hoạch tự tử';
MERGE (s_worry:Symptom {slug: 'excessive_worry'})
    SET s_worry.name_vi = 'Lo lắng quá mức', s_worry.name_en = 'Excessive worry',
        s_worry.definition = 'Lo lắng quá mức và khó kiểm soát về nhiều lĩnh vực trong cuộc sống, ≥6 tháng';
MERGE (s_irritable:Symptom {slug: 'irritability'})
    SET s_irritable.name_vi = 'Dễ cáu kỉnh', s_irritable.name_en = 'Irritability',
        s_irritable.definition = 'Xu hướng bực bội, cáu kỉnh hoặc mất kiên nhẫn không tương xứng với tình huống';
MERGE (s_tension:Symptom {slug: 'tension'})
    SET s_tension.name_vi = 'Căng thẳng cơ thể', s_tension.name_en = 'Tension',
        s_tension.definition = 'Căng cơ, đau đầu hoặc khó chịu thể chất do trạng thái lo âu kéo dài';

// Symptom → SymptomCategory (typed edge; avoids polymorphic :IN_CATEGORY across labels)
MATCH (s:Symptom {slug: 'insomnia'}),               (c:SymptomCategory {slug: 'sleep'})     MERGE (s)-[:IN_SYMPTOM_CATEGORY]->(c);
MATCH (s:Symptom {slug: 'fatigue'}),                (c:SymptomCategory {slug: 'energy'})    MERGE (s)-[:IN_SYMPTOM_CATEGORY]->(c);
MATCH (s:Symptom {slug: 'anhedonia'}),              (c:SymptomCategory {slug: 'mood'})      MERGE (s)-[:IN_SYMPTOM_CATEGORY]->(c);
MATCH (s:Symptom {slug: 'low_mood'}),               (c:SymptomCategory {slug: 'mood'})      MERGE (s)-[:IN_SYMPTOM_CATEGORY]->(c);
MATCH (s:Symptom {slug: 'guilt'}),                  (c:SymptomCategory {slug: 'cognition'}) MERGE (s)-[:IN_SYMPTOM_CATEGORY]->(c);
MATCH (s:Symptom {slug: 'poor_concentration'}),     (c:SymptomCategory {slug: 'cognition'}) MERGE (s)-[:IN_SYMPTOM_CATEGORY]->(c);
MATCH (s:Symptom {slug: 'appetite_change'}),        (c:SymptomCategory {slug: 'somatic'})   MERGE (s)-[:IN_SYMPTOM_CATEGORY]->(c);
MATCH (s:Symptom {slug: 'psychomotor_disturbance'}),(c:SymptomCategory {slug: 'somatic'})   MERGE (s)-[:IN_SYMPTOM_CATEGORY]->(c);
MATCH (s:Symptom {slug: 'suicidal_ideation'}),      (c:SymptomCategory {slug: 'safety'})    MERGE (s)-[:IN_SYMPTOM_CATEGORY]->(c);
MATCH (s:Symptom {slug: 'excessive_worry'}),        (c:SymptomCategory {slug: 'anxiety'})   MERGE (s)-[:IN_SYMPTOM_CATEGORY]->(c);
MATCH (s:Symptom {slug: 'irritability'}),           (c:SymptomCategory {slug: 'mood'})      MERGE (s)-[:IN_SYMPTOM_CATEGORY]->(c);
MATCH (s:Symptom {slug: 'tension'}),                (c:SymptomCategory {slug: 'somatic'})   MERGE (s)-[:IN_SYMPTOM_CATEGORY]->(c);

// PsychProcess → Symptom (:PSYCH_BASIS_FOR) — distinct from :UNDERLIES to Construct (§4.2).
MATCH (p:PsychProcess {slug: 'attention'}),  (s:Symptom {slug: 'poor_concentration'}) MERGE (p)-[:PSYCH_BASIS_FOR]->(s);
MATCH (p:PsychProcess {slug: 'affect'}),     (s:Symptom {slug: 'low_mood'})           MERGE (p)-[:PSYCH_BASIS_FOR]->(s);
MATCH (p:PsychProcess {slug: 'affect'}),     (s:Symptom {slug: 'irritability'})       MERGE (p)-[:PSYCH_BASIS_FOR]->(s);
MATCH (p:PsychProcess {slug: 'thinking'}),   (s:Symptom {slug: 'excessive_worry'})    MERGE (p)-[:PSYCH_BASIS_FOR]->(s);

// ---------- 5.3 Item → Symptom (MEASURES) ----------

MATCH (q:Item {code: 'PHQ9_Q1'}), (s:Symptom {slug: 'anhedonia'})               MERGE (q)-[:MEASURES]->(s);
MATCH (q:Item {code: 'PHQ9_Q2'}), (s:Symptom {slug: 'low_mood'})                MERGE (q)-[:MEASURES]->(s);
MATCH (q:Item {code: 'PHQ9_Q3'}), (s:Symptom {slug: 'insomnia'})                MERGE (q)-[:MEASURES]->(s);
MATCH (q:Item {code: 'PHQ9_Q4'}), (s:Symptom {slug: 'fatigue'})                 MERGE (q)-[:MEASURES]->(s);
MATCH (q:Item {code: 'PHQ9_Q5'}), (s:Symptom {slug: 'appetite_change'})         MERGE (q)-[:MEASURES]->(s);
MATCH (q:Item {code: 'PHQ9_Q6'}), (s:Symptom {slug: 'guilt'})                   MERGE (q)-[:MEASURES]->(s);
MATCH (q:Item {code: 'PHQ9_Q7'}), (s:Symptom {slug: 'poor_concentration'})      MERGE (q)-[:MEASURES]->(s);
MATCH (q:Item {code: 'PHQ9_Q8'}), (s:Symptom {slug: 'psychomotor_disturbance'}) MERGE (q)-[:MEASURES]->(s);
MATCH (q:Item {code: 'PHQ9_Q9'}), (s:Symptom {slug: 'suicidal_ideation'})       MERGE (q)-[:MEASURES]->(s);
MATCH (q:Item {code: 'GAD7_Q1'}), (s:Symptom {slug: 'excessive_worry'})         MERGE (q)-[:MEASURES]->(s);
MATCH (q:Item {code: 'GAD7_Q2'}), (s:Symptom {slug: 'excessive_worry'})         MERGE (q)-[:MEASURES]->(s);
MATCH (q:Item {code: 'GAD7_Q3'}), (s:Symptom {slug: 'excessive_worry'})         MERGE (q)-[:MEASURES]->(s);
MATCH (q:Item {code: 'GAD7_Q4'}), (s:Symptom {slug: 'tension'})                 MERGE (q)-[:MEASURES]->(s);
MATCH (q:Item {code: 'GAD7_Q5'}), (s:Symptom {slug: 'tension'})                 MERGE (q)-[:MEASURES]->(s);
MATCH (q:Item {code: 'GAD7_Q6'}), (s:Symptom {slug: 'irritability'})            MERGE (q)-[:MEASURES]->(s);
MATCH (q:Item {code: 'GAD7_Q7'}), (s:Symptom {slug: 'excessive_worry'})         MERGE (q)-[:MEASURES]->(s);

// ---------- 5.4 Symptom co-occurrence (clinical) ----------
// Convention: single directed edge, query undirected with -[:CO_OCCURS_WITH]-.
// DO NOT create reverse edges — they double storage and skew count queries.

MATCH (a:Symptom {slug: 'insomnia'}),        (b:Symptom {slug: 'fatigue'})           MERGE (a)-[:CO_OCCURS_WITH {weight: 0.75}]->(b);
MATCH (a:Symptom {slug: 'insomnia'}),        (b:Symptom {slug: 'poor_concentration'}) MERGE (a)-[:CO_OCCURS_WITH {weight: 0.65}]->(b);
MATCH (a:Symptom {slug: 'low_mood'}),        (b:Symptom {slug: 'anhedonia'})          MERGE (a)-[:CO_OCCURS_WITH {weight: 0.80}]->(b);
MATCH (a:Symptom {slug: 'guilt'}),           (b:Symptom {slug: 'low_mood'})           MERGE (a)-[:CO_OCCURS_WITH {weight: 0.70}]->(b);
MATCH (a:Symptom {slug: 'excessive_worry'}), (b:Symptom {slug: 'insomnia'})           MERGE (a)-[:CO_OCCURS_WITH {weight: 0.68}]->(b);
MATCH (a:Symptom {slug: 'excessive_worry'}), (b:Symptom {slug: 'tension'})            MERGE (a)-[:CO_OCCURS_WITH {weight: 0.72}]->(b);
MATCH (a:Symptom {slug: 'irritability'}),    (b:Symptom {slug: 'tension'})            MERGE (a)-[:CO_OCCURS_WITH {weight: 0.60}]->(b);
MATCH (a:Symptom {slug: 'fatigue'}),         (b:Symptom {slug: 'appetite_change'})    MERGE (a)-[:CO_OCCURS_WITH {weight: 0.55}]->(b);

// ---------- 5.5 Disorder nodes (DSM-5 seed — 45 most common) ----------
// Primary key: slug (ASCII snake_case). icd_code is a secondary indexed property.
// Uses SET so reruns repair accidental edits.
// CSV load script may overwrite with ON MATCH SET — run bootstrap BEFORE CSV.

// — Ch.1 Neurodevelopmental —
MERGE (d_adhd:Disorder {slug: 'adhd'})
    SET d_adhd.icd_code = 'F90.9', d_adhd.dsm5_code = '314.01',
        d_adhd.name_vi = 'Rối loạn tăng động/giảm chú ý', d_adhd.name_en = 'Attention-Deficit/Hyperactivity Disorder',
        d_adhd.definition = 'Mẫu dai dẳng giảm chú ý và/hoặc tăng động-xung động ảnh hưởng chức năng';
MERGE (d_asd:Disorder {slug: 'asd'})
    SET d_asd.icd_code = 'F84.0', d_asd.dsm5_code = '299.00',
        d_asd.name_vi = 'Rối loạn phổ tự kỷ', d_asd.name_en = 'Autism Spectrum Disorder',
        d_asd.definition = 'Khiếm khuyết dai dẳng trong giao tiếp xã hội và hành vi lặp lại hạn chế';

// — Ch.2 Psychotic —
MERGE (d_schiz:Disorder {slug: 'schizophrenia'})
    SET d_schiz.icd_code = 'F20.9', d_schiz.dsm5_code = '295.90',
        d_schiz.name_vi = 'Tâm thần phân liệt', d_schiz.name_en = 'Schizophrenia',
        d_schiz.definition = '≥2 trong: hoang tưởng, ảo giác, ngôn ngữ vô tổ chức, hành vi bất thường, triệu chứng âm tính; ≥6 tháng';

// — Ch.3 Bipolar —
MERGE (d_bp1:Disorder {slug: 'bipolar_i'})
    SET d_bp1.icd_code = 'F31.9', d_bp1.dsm5_code = '296.41',
        d_bp1.name_vi = 'Rối loạn lưỡng cực I', d_bp1.name_en = 'Bipolar I Disorder',
        d_bp1.definition = 'Ít nhất 1 giai đoạn hưng cảm ≥7 ngày, có thể xen kẽ giai đoạn trầm cảm';
MERGE (d_bp2:Disorder {slug: 'bipolar_ii'})
    SET d_bp2.icd_code = 'F31.81', d_bp2.dsm5_code = '296.89',
        d_bp2.name_vi = 'Rối loạn lưỡng cực II', d_bp2.name_en = 'Bipolar II Disorder',
        d_bp2.definition = 'Ít nhất 1 giai đoạn hưng cảm nhẹ và 1 giai đoạn trầm cảm chủ yếu';
MERGE (d_cyc:Disorder {slug: 'cyclothymia'})
    SET d_cyc.icd_code = 'F34.0', d_cyc.dsm5_code = '301.13',
        d_cyc.name_vi = 'Rối loạn khí sắc chu kỳ', d_cyc.name_en = 'Cyclothymic Disorder',
        d_cyc.definition = 'Nhiều giai đoạn hưng cảm nhẹ và trầm cảm nhẹ ≥2 năm, không đáp ứng tiêu chuẩn đầy đủ';

// — Ch.4 Depressive —
MERGE (d_mdd:Disorder {slug: 'mdd'})
    SET d_mdd.icd_code = 'F32.9', d_mdd.dsm5_code = '296.2x',
        d_mdd.name_vi = 'Rối loạn trầm cảm chủ yếu', d_mdd.name_en = 'Major Depressive Disorder',
        d_mdd.definition = 'Giai đoạn trầm cảm ≥2 tuần với ≥5 triệu chứng theo DSM-5';
MERGE (d_pdd:Disorder {slug: 'pdd'})
    SET d_pdd.icd_code = 'F34.1', d_pdd.dsm5_code = '300.4',
        d_pdd.name_vi = 'Rối loạn trầm cảm dai dẳng', d_pdd.name_en = 'Persistent Depressive Disorder',
        d_pdd.definition = 'Khí sắc trầm kéo dài ≥2 năm';
MERGE (d_dmdd:Disorder {slug: 'dmdd'})
    SET d_dmdd.icd_code = 'F34.8', d_dmdd.dsm5_code = '296.99',
        d_dmdd.name_vi = 'Rối loạn điều chỉnh khí sắc', d_dmdd.name_en = 'Disruptive Mood Dysregulation Disorder',
        d_dmdd.definition = 'Bùng phát giận dữ nghiêm trọng ≥3 lần/tuần, khí sắc trầm/cáu kỉnh liên tục giữa các cơn; ở trẻ ≤18 tuổi';
MERGE (d_pmdd:Disorder {slug: 'pmdd'})
    SET d_pmdd.icd_code = 'N94.3', d_pmdd.dsm5_code = '625.4',
        d_pmdd.name_vi = 'Rối loạn cảm xúc tiền kinh nguyệt', d_pmdd.name_en = 'Premenstrual Dysphoric Disorder',
        d_pmdd.definition = 'Triệu chứng tâm trạng đáng kể trong tuần trước hành kinh, cải thiện sau hành kinh';

// — Ch.5 Anxiety —
MERGE (d_gad:Disorder {slug: 'gad'})
    SET d_gad.icd_code = 'F41.1', d_gad.dsm5_code = '300.02',
        d_gad.name_vi = 'Rối loạn lo âu lan toả', d_gad.name_en = 'Generalized Anxiety Disorder',
        d_gad.definition = 'Lo lắng quá mức ≥6 tháng, khó kiểm soát, kèm ≥3 triệu chứng thể chất';
MERGE (d_panic:Disorder {slug: 'panic_disorder'})
    SET d_panic.icd_code = 'F41.0', d_panic.dsm5_code = '300.01',
        d_panic.name_vi = 'Rối loạn hoảng sợ', d_panic.name_en = 'Panic Disorder',
        d_panic.definition = 'Cơn hoảng sợ tái phát bất ngờ kèm lo sợ tái phát hoặc thay đổi hành vi';
MERGE (d_agora:Disorder {slug: 'agoraphobia'})
    SET d_agora.icd_code = 'F40.00', d_agora.dsm5_code = '300.22',
        d_agora.name_vi = 'Ám ảnh sợ khoảng trống', d_agora.name_en = 'Agoraphobia',
        d_agora.definition = 'Sợ và tránh né ≥2 trong 5 tình huống (phương tiện công cộng, không gian mở, đám đông, hàng dài, ở nhà một mình)';
MERGE (d_sad:Disorder {slug: 'social_anxiety_disorder'})
    SET d_sad.icd_code = 'F40.10', d_sad.dsm5_code = '300.23',
        d_sad.name_vi = 'Rối loạn lo âu xã hội', d_sad.name_en = 'Social Anxiety Disorder',
        d_sad.definition = 'Sợ đáng kể các tình huống xã hội có thể bị người khác đánh giá tiêu cực';
MERGE (d_phobia:Disorder {slug: 'specific_phobia'})
    SET d_phobia.icd_code = 'F40.218', d_phobia.dsm5_code = '300.29',
        d_phobia.name_vi = 'Ám ảnh sợ chuyên biệt', d_phobia.name_en = 'Specific Phobia',
        d_phobia.definition = 'Sợ đáng kể và dai dẳng về một đối tượng hoặc tình huống cụ thể';
MERGE (d_sep:Disorder {slug: 'separation_anxiety'})
    SET d_sep.icd_code = 'F93.0', d_sep.dsm5_code = '309.21',
        d_sep.name_vi = 'Rối loạn lo âu chia tách', d_sep.name_en = 'Separation Anxiety Disorder',
        d_sep.definition = 'Lo âu quá mức khi tách khỏi người gắn bó, không phù hợp với giai đoạn phát triển';

// — Ch.6 OCD & Related —
MERGE (d_ocd:Disorder {slug: 'ocd'})
    SET d_ocd.icd_code = 'F42', d_ocd.dsm5_code = '300.3',
        d_ocd.name_vi = 'Rối loạn ám ảnh cưỡng chế', d_ocd.name_en = 'Obsessive-Compulsive Disorder',
        d_ocd.definition = 'Ám ảnh và/hoặc cưỡng chế tiêu tốn >1 giờ/ngày, gây đau khổ đáng kể';
MERGE (d_bdd:Disorder {slug: 'body_dysmorphic'})
    SET d_bdd.icd_code = 'F45.22', d_bdd.dsm5_code = '300.7',
        d_bdd.name_vi = 'Rối loạn ám ảnh dị hình', d_bdd.name_en = 'Body Dysmorphic Disorder',
        d_bdd.definition = 'Bận tâm với ≥1 khiếm khuyết ngoại hình mà người khác thấy nhẹ hoặc không thể quan sát';
MERGE (d_hoard:Disorder {slug: 'hoarding'})
    SET d_hoard.icd_code = 'F42.3', d_hoard.dsm5_code = '300.3',
        d_hoard.name_vi = 'Rối loạn tích trữ', d_hoard.name_en = 'Hoarding Disorder',
        d_hoard.definition = 'Khó khăn dai dẳng trong việc bỏ/chia tay đồ vật, dẫn đến tích tụ lộn xộn';
MERGE (d_trich:Disorder {slug: 'trichotillomania'})
    SET d_trich.icd_code = 'F63.3', d_trich.dsm5_code = '312.39',
        d_trich.name_vi = 'Rối loạn nhổ tóc', d_trich.name_en = 'Trichotillomania',
        d_trich.definition = 'Nhổ tóc tái diễn dẫn đến rụng tóc, nhiều lần cố gắng giảm hoặc dừng';

// — Ch.7 Trauma & Stressor-Related —
MERGE (d_ptsd:Disorder {slug: 'ptsd'})
    SET d_ptsd.icd_code = 'F43.10', d_ptsd.dsm5_code = '309.81',
        d_ptsd.name_vi = 'Rối loạn stress sau sang chấn', d_ptsd.name_en = 'Posttraumatic Stress Disorder',
        d_ptsd.definition = 'Triệu chứng xâm nhập, né tránh, nhận thức/khí sắc âm tính, kích thích tăng sau sang chấn ≥1 tháng';
MERGE (d_asd_trauma:Disorder {slug: 'acute_stress_disorder'})
    SET d_asd_trauma.icd_code = 'F43.0', d_asd_trauma.dsm5_code = '308.3',
        d_asd_trauma.name_vi = 'Rối loạn stress cấp', d_asd_trauma.name_en = 'Acute Stress Disorder',
        d_asd_trauma.definition = '≥9 triệu chứng (xâm nhập, tâm trạng âm tính, phân ly, né tránh, kích thích) trong 3 ngày–1 tháng sau sang chấn';
MERGE (d_adj:Disorder {slug: 'adjustment_disorder'})
    SET d_adj.icd_code = 'F43.20', d_adj.dsm5_code = '309.0',
        d_adj.name_vi = 'Rối loạn thích ứng', d_adj.name_en = 'Adjustment Disorder',
        d_adj.definition = 'Đáp ứng cảm xúc/hành vi đối với một tác nhân gây stress có thể xác định được, mức độ không tương xứng';

// — Ch.8 Dissociative —
MERGE (d_did:Disorder {slug: 'dissociative_identity'})
    SET d_did.icd_code = 'F44.81', d_did.dsm5_code = '300.14',
        d_did.name_vi = 'Rối loạn xác định phân ly', d_did.name_en = 'Dissociative Identity Disorder',
        d_did.definition = '≥2 trạng thái nhân cách/ý thức khác biệt, mất trí nhớ tái diễn không thể giải thích được';
MERGE (d_damn:Disorder {slug: 'dissociative_amnesia'})
    SET d_damn.icd_code = 'F44.0', d_damn.dsm5_code = '300.12',
        d_damn.name_vi = 'Mất trí nhớ phân ly', d_damn.name_en = 'Dissociative Amnesia',
        d_damn.definition = 'Không thể nhớ lại thông tin tiểu sử quan trọng, thường liên quan sang chấn';
MERGE (d_dper:Disorder {slug: 'depersonalization_derealization'})
    SET d_dper.icd_code = 'F48.1', d_dper.dsm5_code = '300.6',
        d_dper.name_vi = 'Rối loạn giải thể nhân cách/giải thể thực tại', d_dper.name_en = 'Depersonalization/Derealization Disorder',
        d_dper.definition = 'Trải nghiệm tách rời dai dẳng khỏi bản thân hoặc môi trường xung quanh';

// — Ch.9 Somatic Symptom —
MERGE (d_ssd:Disorder {slug: 'somatic_symptom'})
    SET d_ssd.icd_code = 'F45.1', d_ssd.dsm5_code = '300.82',
        d_ssd.name_vi = 'Rối loạn triệu chứng cơ thể', d_ssd.name_en = 'Somatic Symptom Disorder',
        d_ssd.definition = '≥1 triệu chứng cơ thể gây đau khổ với suy nghĩ/cảm xúc/hành vi quá mức liên quan đến sức khỏe';
MERGE (d_iad:Disorder {slug: 'illness_anxiety'})
    SET d_iad.icd_code = 'F45.21', d_iad.dsm5_code = '300.7',
        d_iad.name_vi = 'Rối loạn lo âu có bệnh', d_iad.name_en = 'Illness Anxiety Disorder',
        d_iad.definition = 'Bận tâm về việc mắc bệnh nghiêm trọng, ít hoặc không có triệu chứng cơ thể';

// — Ch.10 Eating —
MERGE (d_anorex:Disorder {slug: 'anorexia_nervosa'})
    SET d_anorex.icd_code = 'F50.01', d_anorex.dsm5_code = '307.1',
        d_anorex.name_vi = 'Chán ăn tâm thần', d_anorex.name_en = 'Anorexia Nervosa',
        d_anorex.definition = 'Hạn chế lượng calo dẫn đến cân nặng thấp đáng kể; sợ tăng cân; hình ảnh cơ thể bị bóp méo';
MERGE (d_bulia:Disorder {slug: 'bulimia_nervosa'})
    SET d_bulia.icd_code = 'F50.2', d_bulia.dsm5_code = '307.51',
        d_bulia.name_vi = 'Ăn nhiều rồi nôn tâm thần', d_bulia.name_en = 'Bulimia Nervosa',
        d_bulia.definition = 'Ăn vô độ tái diễn kèm hành vi bù trừ không thích hợp ≥1 lần/tuần ×3 tháng';
MERGE (d_bed:Disorder {slug: 'binge_eating'})
    SET d_bed.icd_code = 'F50.81', d_bed.dsm5_code = '307.51',
        d_bed.name_vi = 'Rối loạn ăn vô độ', d_bed.name_en = 'Binge-Eating Disorder',
        d_bed.definition = 'Ăn vô độ tái diễn (≥1 lần/tuần ×3 tháng) không kèm hành vi bù trừ';

// — Ch.11 Elimination —
MERGE (d_enur:Disorder {slug: 'enuresis'})
    SET d_enur.icd_code = 'F98.0', d_enur.dsm5_code = '307.6',
        d_enur.name_vi = 'Đái dầm', d_enur.name_en = 'Enuresis',
        d_enur.definition = 'Tiểu tiện không tự chủ tái diễn (≥2 lần/tuần ×3 tháng) ở trẻ ≥5 tuổi';

// — Ch.12 Sleep-Wake —
MERGE (d_insom:Disorder {slug: 'insomnia_disorder'})
    SET d_insom.icd_code = 'G47.00', d_insom.dsm5_code = '307.42',
        d_insom.name_vi = 'Rối loạn mất ngủ', d_insom.name_en = 'Insomnia Disorder',
        d_insom.definition = 'Không hài lòng với số lượng/chất lượng giấc ngủ ≥3 đêm/tuần ×3 tháng, dù có đủ điều kiện ngủ';
MERGE (d_narc:Disorder {slug: 'narcolepsy'})
    SET d_narc.icd_code = 'G47.419', d_narc.dsm5_code = '347.00',
        d_narc.name_vi = 'Ngủ lịm', d_narc.name_en = 'Narcolepsy',
        d_narc.definition = 'Buồn ngủ ban ngày quá mức, cataplexy, ảo giác khi ngủ/thức dậy ≥3 lần/tuần ×3 tháng';

// — Ch.14 Disruptive/Impulse —
MERGE (d_odd:Disorder {slug: 'odd'})
    SET d_odd.icd_code = 'F91.3', d_odd.dsm5_code = '313.81',
        d_odd.name_vi = 'Rối loạn chống đối thách thức', d_odd.name_en = 'Oppositional Defiant Disorder',
        d_odd.definition = 'Mẫu giận dữ/cáu kỉnh, tranh cãi/thách thức, hoặc trả thù ≥6 tháng';
MERGE (d_ied:Disorder {slug: 'ied'})
    SET d_ied.icd_code = 'F63.81', d_ied.dsm5_code = '312.34',
        d_ied.name_vi = 'Rối loạn bùng nổ từng cơn', d_ied.name_en = 'Intermittent Explosive Disorder',
        d_ied.definition = 'Bùng phát hành vi hung hăng tái diễn, không tương xứng với tác nhân gây ra';

// — Ch.15 Substance —
MERGE (d_aud:Disorder {slug: 'alcohol_use_disorder'})
    SET d_aud.icd_code = 'F10.20', d_aud.dsm5_code = '303.90',
        d_aud.name_vi = 'Rối loạn sử dụng rượu', d_aud.name_en = 'Alcohol Use Disorder',
        d_aud.definition = 'Mẫu sử dụng rượu có hại với ≥2/11 tiêu chuẩn trong 12 tháng';
MERGE (d_oud:Disorder {slug: 'opioid_use_disorder'})
    SET d_oud.icd_code = 'F11.20', d_oud.dsm5_code = '304.00',
        d_oud.name_vi = 'Rối loạn sử dụng opioid', d_oud.name_en = 'Opioid Use Disorder',
        d_oud.definition = 'Mẫu sử dụng opioid có hại với ≥2/11 tiêu chuẩn trong 12 tháng';
// Substance-induced depressive disorders (tách khỏi MDD — P0-3)
MERGE (d_aidep:Disorder {slug: 'alcohol_induced_depressive'})
    SET d_aidep.icd_code = 'F10.14', d_aidep.dsm5_code = '291.89',
        d_aidep.name_vi = 'Rối loạn trầm cảm do rượu', d_aidep.name_en = 'Alcohol-Induced Depressive Disorder',
        d_aidep.definition = 'Triệu chứng trầm cảm đáng kể do sử dụng/cai rượu, không phải MDD độc lập';
MERGE (d_stidep:Disorder {slug: 'stimulant_induced_depressive'})
    SET d_stidep.icd_code = 'F15.14', d_stidep.dsm5_code = '292.84',
        d_stidep.name_vi = 'Rối loạn trầm cảm do chất kích thích', d_stidep.name_en = 'Stimulant-Induced Depressive Disorder',
        d_stidep.definition = 'Triệu chứng trầm cảm đáng kể trong giai đoạn cai chất kích thích';

// — Ch.16 Neurocognitive —
MERGE (d_del:Disorder {slug: 'delirium'})
    SET d_del.icd_code = 'F05', d_del.dsm5_code = '293.0',
        d_del.name_vi = 'Sảng', d_del.name_en = 'Delirium',
        d_del.definition = 'Rối loạn ý thức/nhận thức phát triển nhanh, dao động trong ngày, do nguyên nhân y tế';
MERGE (d_alz:Disorder {slug: 'major_ncd_alzheimer'})
    SET d_alz.icd_code = 'F02.80', d_alz.dsm5_code = '294.1x',
        d_alz.name_vi = 'Rối loạn thần kinh-nhận thức chủ yếu do Alzheimer', d_alz.name_en = 'Major NCD Due to Alzheimer Disease',
        d_alz.definition = 'Suy giảm nhận thức đáng kể trong ≥1 lĩnh vực theo tiến trình Alzheimer điển hình';

// — Ch.17 Personality —
MERGE (d_bpd:Disorder {slug: 'borderline_pd'})
    SET d_bpd.icd_code = 'F60.3', d_bpd.dsm5_code = '301.83',
        d_bpd.name_vi = 'Rối loạn nhân cách ranh giới', d_bpd.name_en = 'Borderline Personality Disorder',
        d_bpd.definition = 'Mẫu không ổn định trong quan hệ, hình ảnh bản thân, cảm xúc và xung động đánh dấu từ đầu tuổi trưởng thành';
MERGE (d_aspd:Disorder {slug: 'antisocial_pd'})
    SET d_aspd.icd_code = 'F60.2', d_aspd.dsm5_code = '301.7',
        d_aspd.name_vi = 'Rối loạn nhân cách chống xã hội', d_aspd.name_en = 'Antisocial Personality Disorder',
        d_aspd.definition = 'Mẫu coi thường và vi phạm quyền của người khác từ ≥15 tuổi';
MERGE (d_npd:Disorder {slug: 'narcissistic_pd'})
    SET d_npd.icd_code = 'F60.81', d_npd.dsm5_code = '301.81',
        d_npd.name_vi = 'Rối loạn nhân cách tự ái', d_npd.name_en = 'Narcissistic Personality Disorder',
        d_npd.definition = 'Mẫu tự cao, cần được ngưỡng mộ và thiếu đồng cảm bắt đầu từ đầu tuổi trưởng thành';

// — Disorder → DisorderCategory (:IN_DISORDER_CATEGORY; legacy :IN_CATEGORY removed in §11) —
MATCH (d:Disorder {slug: 'adhd'}),                       (c:DisorderCategory {slug: 'neurodevelopmental_disorders'})     MERGE (d)-[:IN_DISORDER_CATEGORY]->(c);
MATCH (d:Disorder {slug: 'asd'}),                        (c:DisorderCategory {slug: 'neurodevelopmental_disorders'})     MERGE (d)-[:IN_DISORDER_CATEGORY]->(c);
MATCH (d:Disorder {slug: 'schizophrenia'}),              (c:DisorderCategory {slug: 'psychotic_disorders'})              MERGE (d)-[:IN_DISORDER_CATEGORY]->(c);
MATCH (d:Disorder {slug: 'bipolar_i'}),                  (c:DisorderCategory {slug: 'bipolar_disorders'})                MERGE (d)-[:IN_DISORDER_CATEGORY]->(c);
MATCH (d:Disorder {slug: 'bipolar_ii'}),                 (c:DisorderCategory {slug: 'bipolar_disorders'})                MERGE (d)-[:IN_DISORDER_CATEGORY]->(c);
MATCH (d:Disorder {slug: 'cyclothymia'}),                (c:DisorderCategory {slug: 'bipolar_disorders'})                MERGE (d)-[:IN_DISORDER_CATEGORY]->(c);
MATCH (d:Disorder {slug: 'mdd'}),                        (c:DisorderCategory {slug: 'depressive_disorders'})             MERGE (d)-[:IN_DISORDER_CATEGORY]->(c);
MATCH (d:Disorder {slug: 'pdd'}),                        (c:DisorderCategory {slug: 'depressive_disorders'})             MERGE (d)-[:IN_DISORDER_CATEGORY]->(c);
MATCH (d:Disorder {slug: 'dmdd'}),                       (c:DisorderCategory {slug: 'depressive_disorders'})             MERGE (d)-[:IN_DISORDER_CATEGORY]->(c);
MATCH (d:Disorder {slug: 'pmdd'}),                       (c:DisorderCategory {slug: 'depressive_disorders'})             MERGE (d)-[:IN_DISORDER_CATEGORY]->(c);
MATCH (d:Disorder {slug: 'gad'}),                        (c:DisorderCategory {slug: 'anxiety_disorders'})                MERGE (d)-[:IN_DISORDER_CATEGORY]->(c);
MATCH (d:Disorder {slug: 'panic_disorder'}),             (c:DisorderCategory {slug: 'anxiety_disorders'})                MERGE (d)-[:IN_DISORDER_CATEGORY]->(c);
MATCH (d:Disorder {slug: 'agoraphobia'}),                (c:DisorderCategory {slug: 'anxiety_disorders'})                MERGE (d)-[:IN_DISORDER_CATEGORY]->(c);
MATCH (d:Disorder {slug: 'social_anxiety_disorder'}),    (c:DisorderCategory {slug: 'anxiety_disorders'})                MERGE (d)-[:IN_DISORDER_CATEGORY]->(c);
MATCH (d:Disorder {slug: 'specific_phobia'}),            (c:DisorderCategory {slug: 'anxiety_disorders'})                MERGE (d)-[:IN_DISORDER_CATEGORY]->(c);
MATCH (d:Disorder {slug: 'separation_anxiety'}),         (c:DisorderCategory {slug: 'anxiety_disorders'})                MERGE (d)-[:IN_DISORDER_CATEGORY]->(c);
MATCH (d:Disorder {slug: 'ocd'}),                        (c:DisorderCategory {slug: 'obsessive_compulsive_disorders'})   MERGE (d)-[:IN_DISORDER_CATEGORY]->(c);
MATCH (d:Disorder {slug: 'body_dysmorphic'}),            (c:DisorderCategory {slug: 'obsessive_compulsive_disorders'})   MERGE (d)-[:IN_DISORDER_CATEGORY]->(c);
MATCH (d:Disorder {slug: 'hoarding'}),                   (c:DisorderCategory {slug: 'obsessive_compulsive_disorders'})   MERGE (d)-[:IN_DISORDER_CATEGORY]->(c);
MATCH (d:Disorder {slug: 'trichotillomania'}),           (c:DisorderCategory {slug: 'obsessive_compulsive_disorders'})   MERGE (d)-[:IN_DISORDER_CATEGORY]->(c);
MATCH (d:Disorder {slug: 'ptsd'}),                       (c:DisorderCategory {slug: 'trauma_stress_disorders'})          MERGE (d)-[:IN_DISORDER_CATEGORY]->(c);
MATCH (d:Disorder {slug: 'acute_stress_disorder'}),      (c:DisorderCategory {slug: 'trauma_stress_disorders'})          MERGE (d)-[:IN_DISORDER_CATEGORY]->(c);
MATCH (d:Disorder {slug: 'adjustment_disorder'}),        (c:DisorderCategory {slug: 'trauma_stress_disorders'})          MERGE (d)-[:IN_DISORDER_CATEGORY]->(c);
MATCH (d:Disorder {slug: 'dissociative_identity'}),      (c:DisorderCategory {slug: 'dissociative_disorders'})           MERGE (d)-[:IN_DISORDER_CATEGORY]->(c);
MATCH (d:Disorder {slug: 'dissociative_amnesia'}),       (c:DisorderCategory {slug: 'dissociative_disorders'})           MERGE (d)-[:IN_DISORDER_CATEGORY]->(c);
MATCH (d:Disorder {slug: 'depersonalization_derealization'}),(c:DisorderCategory {slug: 'dissociative_disorders'})       MERGE (d)-[:IN_DISORDER_CATEGORY]->(c);
MATCH (d:Disorder {slug: 'somatic_symptom'}),            (c:DisorderCategory {slug: 'somatic_symptom_disorders'})        MERGE (d)-[:IN_DISORDER_CATEGORY]->(c);
MATCH (d:Disorder {slug: 'illness_anxiety'}),            (c:DisorderCategory {slug: 'somatic_symptom_disorders'})        MERGE (d)-[:IN_DISORDER_CATEGORY]->(c);
MATCH (d:Disorder {slug: 'anorexia_nervosa'}),           (c:DisorderCategory {slug: 'feeding_eating_disorders'})         MERGE (d)-[:IN_DISORDER_CATEGORY]->(c);
MATCH (d:Disorder {slug: 'bulimia_nervosa'}),            (c:DisorderCategory {slug: 'feeding_eating_disorders'})         MERGE (d)-[:IN_DISORDER_CATEGORY]->(c);
MATCH (d:Disorder {slug: 'binge_eating'}),               (c:DisorderCategory {slug: 'feeding_eating_disorders'})         MERGE (d)-[:IN_DISORDER_CATEGORY]->(c);
MATCH (d:Disorder {slug: 'enuresis'}),                   (c:DisorderCategory {slug: 'elimination_disorders'})            MERGE (d)-[:IN_DISORDER_CATEGORY]->(c);
MATCH (d:Disorder {slug: 'insomnia_disorder'}),          (c:DisorderCategory {slug: 'sleep_wake_disorders'})             MERGE (d)-[:IN_DISORDER_CATEGORY]->(c);
MATCH (d:Disorder {slug: 'narcolepsy'}),                 (c:DisorderCategory {slug: 'sleep_wake_disorders'})             MERGE (d)-[:IN_DISORDER_CATEGORY]->(c);
MATCH (d:Disorder {slug: 'odd'}),                        (c:DisorderCategory {slug: 'disruptive_impulse_conduct'})       MERGE (d)-[:IN_DISORDER_CATEGORY]->(c);
MATCH (d:Disorder {slug: 'ied'}),                        (c:DisorderCategory {slug: 'disruptive_impulse_conduct'})       MERGE (d)-[:IN_DISORDER_CATEGORY]->(c);
MATCH (d:Disorder {slug: 'alcohol_use_disorder'}),       (c:DisorderCategory {slug: 'substance_disorders'})              MERGE (d)-[:IN_DISORDER_CATEGORY]->(c);
MATCH (d:Disorder {slug: 'opioid_use_disorder'}),        (c:DisorderCategory {slug: 'substance_disorders'})              MERGE (d)-[:IN_DISORDER_CATEGORY]->(c);
MATCH (d:Disorder {slug: 'alcohol_induced_depressive'}), (c:DisorderCategory {slug: 'substance_disorders'})              MERGE (d)-[:IN_DISORDER_CATEGORY]->(c);
MATCH (d:Disorder {slug: 'stimulant_induced_depressive'}),(c:DisorderCategory {slug: 'substance_disorders'})             MERGE (d)-[:IN_DISORDER_CATEGORY]->(c);
MATCH (d:Disorder {slug: 'delirium'}),                   (c:DisorderCategory {slug: 'neurocognitive_disorders'})         MERGE (d)-[:IN_DISORDER_CATEGORY]->(c);
MATCH (d:Disorder {slug: 'major_ncd_alzheimer'}),        (c:DisorderCategory {slug: 'neurocognitive_disorders'})         MERGE (d)-[:IN_DISORDER_CATEGORY]->(c);
MATCH (d:Disorder {slug: 'borderline_pd'}),              (c:DisorderCategory {slug: 'personality_disorders'})            MERGE (d)-[:IN_DISORDER_CATEGORY]->(c);
MATCH (d:Disorder {slug: 'antisocial_pd'}),              (c:DisorderCategory {slug: 'personality_disorders'})            MERGE (d)-[:IN_DISORDER_CATEGORY]->(c);
MATCH (d:Disorder {slug: 'narcissistic_pd'}),            (c:DisorderCategory {slug: 'personality_disorders'})            MERGE (d)-[:IN_DISORDER_CATEGORY]->(c);

// ---------- 5.6 Episode nodes ----------

MERGE (ep_mde:Episode {slug: 'major_depressive_episode'})
    SET ep_mde.name_vi = 'Giai đoạn trầm cảm chủ yếu', ep_mde.name_en = 'Major Depressive Episode',
        ep_mde.duration_criterion = '>=2 weeks';
MERGE (ep_man:Episode {slug: 'manic_episode'})
    SET ep_man.name_vi = 'Giai đoạn hưng cảm', ep_man.name_en = 'Manic Episode',
        ep_man.duration_criterion = '>=1 week';
MERGE (ep_hyp:Episode {slug: 'hypomanic_episode'})
    SET ep_hyp.name_vi = 'Giai đoạn hưng cảm nhẹ', ep_hyp.name_en = 'Hypomanic Episode',
        ep_hyp.duration_criterion = '>=4 days';

// ---------- 5.7 Disorder → Symptom (HAS_SYMPTOM) ----------
// required=true → core criterion (A criteria); false → supporting (B criteria)

// ---------- 5.7a DiagnosticCriterion + HAS_CRITERION ----------
// Kept concise for seed quality; can be extended by clinical import pipeline later.
MERGE (dc_mdd_a:DiagnosticCriterion {code: 'MDD-A'})
    SET dc_mdd_a.letter = 'A',
        dc_mdd_a.text_vi = '>=5 triệu chứng trong cùng 2 tuần, gồm khí sắc trầm hoặc mất hứng thú',
        dc_mdd_a.threshold = '>=5/9 symptoms, >=2 weeks',
        dc_mdd_a.disorder_code = 'mdd';
MERGE (dc_mdd_b:DiagnosticCriterion {code: 'MDD-B'})
    SET dc_mdd_b.letter = 'B',
        dc_mdd_b.text_vi = 'Gây suy giảm đáng kể chức năng xã hội, nghề nghiệp hoặc lĩnh vực quan trọng khác',
        dc_mdd_b.threshold = 'clinically significant distress/impairment',
        dc_mdd_b.disorder_code = 'mdd';
MERGE (dc_mdd_c:DiagnosticCriterion {code: 'MDD-C'})
    SET dc_mdd_c.letter = 'C',
        dc_mdd_c.text_vi = 'Không do tác động sinh lý trực tiếp của chất hay bệnh cơ thể',
        dc_mdd_c.threshold = 'rule-out substance/medical etiology',
        dc_mdd_c.disorder_code = 'mdd';

MERGE (dc_gad_a:DiagnosticCriterion {code: 'GAD-A'})
    SET dc_gad_a.letter = 'A',
        dc_gad_a.text_vi = 'Lo âu và lo nghĩ quá mức, khó kiểm soát, kéo dài >=6 tháng',
        dc_gad_a.threshold = '>=6 months',
        dc_gad_a.disorder_code = 'gad';
MERGE (dc_gad_b:DiagnosticCriterion {code: 'GAD-B'})
    SET dc_gad_b.letter = 'B',
        dc_gad_b.text_vi = 'Lo âu đi kèm >=3 triệu chứng cơ thể/nhận thức (người lớn)',
        dc_gad_b.threshold = '>=3 associated symptoms',
        dc_gad_b.disorder_code = 'gad';
MERGE (dc_gad_c:DiagnosticCriterion {code: 'GAD-C'})
    SET dc_gad_c.letter = 'C',
        dc_gad_c.text_vi = 'Gây suy giảm đáng kể chức năng hoặc đau khổ lâm sàng',
        dc_gad_c.threshold = 'clinically significant distress/impairment',
        dc_gad_c.disorder_code = 'gad';

MATCH (d:Disorder {slug: 'mdd'}), (c:DiagnosticCriterion {code: 'MDD-A'}) MERGE (d)-[:HAS_CRITERION]->(c);
MATCH (d:Disorder {slug: 'mdd'}), (c:DiagnosticCriterion {code: 'MDD-B'}) MERGE (d)-[:HAS_CRITERION]->(c);
MATCH (d:Disorder {slug: 'mdd'}), (c:DiagnosticCriterion {code: 'MDD-C'}) MERGE (d)-[:HAS_CRITERION]->(c);
MATCH (d:Disorder {slug: 'gad'}), (c:DiagnosticCriterion {code: 'GAD-A'}) MERGE (d)-[:HAS_CRITERION]->(c);
MATCH (d:Disorder {slug: 'gad'}), (c:DiagnosticCriterion {code: 'GAD-B'}) MERGE (d)-[:HAS_CRITERION]->(c);
MATCH (d:Disorder {slug: 'gad'}), (c:DiagnosticCriterion {code: 'GAD-C'}) MERGE (d)-[:HAS_CRITERION]->(c);

// MDD — 9 symptoms per DSM-5 Criterion A (≥1 of first 2 required, ≥5 total)
MATCH (d:Disorder {slug: 'mdd'}), (s:Symptom {slug: 'low_mood'})                MERGE (d)-[:HAS_SYMPTOM {required: true}]->(s);
MATCH (d:Disorder {slug: 'mdd'}), (s:Symptom {slug: 'anhedonia'})               MERGE (d)-[:HAS_SYMPTOM {required: true}]->(s);
MATCH (d:Disorder {slug: 'mdd'}), (s:Symptom {slug: 'insomnia'})                MERGE (d)-[:HAS_SYMPTOM {required: false}]->(s);
MATCH (d:Disorder {slug: 'mdd'}), (s:Symptom {slug: 'fatigue'})                 MERGE (d)-[:HAS_SYMPTOM {required: false}]->(s);
MATCH (d:Disorder {slug: 'mdd'}), (s:Symptom {slug: 'appetite_change'})         MERGE (d)-[:HAS_SYMPTOM {required: false}]->(s);
MATCH (d:Disorder {slug: 'mdd'}), (s:Symptom {slug: 'guilt'})                   MERGE (d)-[:HAS_SYMPTOM {required: false}]->(s);
MATCH (d:Disorder {slug: 'mdd'}), (s:Symptom {slug: 'poor_concentration'})      MERGE (d)-[:HAS_SYMPTOM {required: false}]->(s);
MATCH (d:Disorder {slug: 'mdd'}), (s:Symptom {slug: 'psychomotor_disturbance'}) MERGE (d)-[:HAS_SYMPTOM {required: false}]->(s);
MATCH (d:Disorder {slug: 'mdd'}), (s:Symptom {slug: 'suicidal_ideation'})       MERGE (d)-[:HAS_SYMPTOM {required: false}]->(s);

// GAD — Criterion A + 6 somatic/cognitive symptoms (≥3 required for adults)
MATCH (d:Disorder {slug: 'gad'}), (s:Symptom {slug: 'excessive_worry'})         MERGE (d)-[:HAS_SYMPTOM {required: true}]->(s);
MATCH (d:Disorder {slug: 'gad'}), (s:Symptom {slug: 'tension'})                 MERGE (d)-[:HAS_SYMPTOM {required: false}]->(s);
MATCH (d:Disorder {slug: 'gad'}), (s:Symptom {slug: 'irritability'})            MERGE (d)-[:HAS_SYMPTOM {required: false}]->(s);
MATCH (d:Disorder {slug: 'gad'}), (s:Symptom {slug: 'poor_concentration'})      MERGE (d)-[:HAS_SYMPTOM {required: false}]->(s);
MATCH (d:Disorder {slug: 'gad'}), (s:Symptom {slug: 'fatigue'})                 MERGE (d)-[:HAS_SYMPTOM {required: false}]->(s);
MATCH (d:Disorder {slug: 'gad'}), (s:Symptom {slug: 'insomnia'})                MERGE (d)-[:HAS_SYMPTOM {required: false}]->(s);

// Disorder → Episode (:HAS_EPISODE) — all Bipolar nodes now seeded above
MATCH (d:Disorder {slug: 'mdd'}),       (e:Episode {slug: 'major_depressive_episode'}) MERGE (d)-[:HAS_EPISODE]->(e);
MATCH (d:Disorder {slug: 'bipolar_i'}), (e:Episode {slug: 'manic_episode'})             MERGE (d)-[:HAS_EPISODE]->(e);
MATCH (d:Disorder {slug: 'bipolar_i'}), (e:Episode {slug: 'major_depressive_episode'}) MERGE (d)-[:HAS_EPISODE]->(e);
MATCH (d:Disorder {slug: 'bipolar_ii'}),(e:Episode {slug: 'hypomanic_episode'})         MERGE (d)-[:HAS_EPISODE]->(e);
MATCH (d:Disorder {slug: 'bipolar_ii'}),(e:Episode {slug: 'major_depressive_episode'}) MERGE (d)-[:HAS_EPISODE]->(e);

// Symptom → Episode (:MANIFESTS_IN) — all 9 DSM-5 MDE criteria
MATCH (s:Symptom {slug: 'low_mood'}),                (e:Episode {slug: 'major_depressive_episode'}) MERGE (s)-[:MANIFESTS_IN]->(e);
MATCH (s:Symptom {slug: 'anhedonia'}),               (e:Episode {slug: 'major_depressive_episode'}) MERGE (s)-[:MANIFESTS_IN]->(e);
MATCH (s:Symptom {slug: 'insomnia'}),                (e:Episode {slug: 'major_depressive_episode'}) MERGE (s)-[:MANIFESTS_IN]->(e);
MATCH (s:Symptom {slug: 'fatigue'}),                 (e:Episode {slug: 'major_depressive_episode'}) MERGE (s)-[:MANIFESTS_IN]->(e);
MATCH (s:Symptom {slug: 'appetite_change'}),         (e:Episode {slug: 'major_depressive_episode'}) MERGE (s)-[:MANIFESTS_IN]->(e);
MATCH (s:Symptom {slug: 'guilt'}),                   (e:Episode {slug: 'major_depressive_episode'}) MERGE (s)-[:MANIFESTS_IN]->(e);
MATCH (s:Symptom {slug: 'poor_concentration'}),      (e:Episode {slug: 'major_depressive_episode'}) MERGE (s)-[:MANIFESTS_IN]->(e);
MATCH (s:Symptom {slug: 'psychomotor_disturbance'}), (e:Episode {slug: 'major_depressive_episode'}) MERGE (s)-[:MANIFESTS_IN]->(e);
MATCH (s:Symptom {slug: 'suicidal_ideation'}),       (e:Episode {slug: 'major_depressive_episode'}) MERGE (s)-[:MANIFESTS_IN]->(e);

// ---------- 5.8 Differential diagnosis ----------
// Single directed edge per pair — query undirected with -[:DIFFERENTIAL_WITH]-.
MATCH (a:Disorder {slug: 'mdd'}),           (b:Disorder {slug: 'gad'})              MERGE (a)-[:DIFFERENTIAL_WITH]->(b);
MATCH (a:Disorder {slug: 'ptsd'}),          (b:Disorder {slug: 'mdd'})              MERGE (a)-[:DIFFERENTIAL_WITH]->(b);
MATCH (a:Disorder {slug: 'panic_disorder'}),(b:Disorder {slug: 'gad'})              MERGE (a)-[:DIFFERENTIAL_WITH]->(b);
MATCH (a:Disorder {slug: 'mdd'}),           (b:Disorder {slug: 'bipolar_ii'})       MERGE (a)-[:DIFFERENTIAL_WITH]->(b);
MATCH (a:Disorder {slug: 'mdd'}),           (b:Disorder {slug: 'pdd'})              MERGE (a)-[:DIFFERENTIAL_WITH]->(b);
MATCH (a:Disorder {slug: 'ocd'}),           (b:Disorder {slug: 'gad'})              MERGE (a)-[:DIFFERENTIAL_WITH]->(b);
MATCH (a:Disorder {slug: 'social_anxiety_disorder'}),(b:Disorder {slug: 'panic_disorder'}) MERGE (a)-[:DIFFERENTIAL_WITH]->(b);
// Substance-induced disorders differential with their primary counterparts
MATCH (a:Disorder {slug: 'alcohol_induced_depressive'}),(b:Disorder {slug: 'mdd'})  MERGE (a)-[:DIFFERENTIAL_WITH]->(b);
MATCH (a:Disorder {slug: 'stimulant_induced_depressive'}),(b:Disorder {slug: 'mdd'}) MERGE (a)-[:DIFFERENTIAL_WITH]->(b);

// ---------- 5.9 Substance + MedicalCondition (etiological) ----------

MERGE (sub1:Substance {slug: 'alcohol'})   SET sub1.name_vi = 'Rượu bia',        sub1.name_en = 'Alcohol',    sub1.dsm5_class = 'alcohol';
MERGE (sub2:Substance {slug: 'cannabis'})  SET sub2.name_vi = 'Cần sa',          sub2.name_en = 'Cannabis',   sub2.dsm5_class = 'cannabis';
MERGE (sub3:Substance {slug: 'stimulant'}) SET sub3.name_vi = 'Chất kích thích', sub3.name_en = 'Stimulant',  sub3.dsm5_class = 'stimulant';
MERGE (sub4:Substance {slug: 'opioid'})    SET sub4.name_vi = 'Opioid',          sub4.name_en = 'Opioid',     sub4.dsm5_class = 'opioid';

MERGE (mc1:MedicalCondition {slug: 'hypothyroidism'})      SET mc1.name_vi = 'Suy giáp',         mc1.name_en = 'Hypothyroidism';
MERGE (mc2:MedicalCondition {slug: 'stroke'})              SET mc2.name_vi = 'Đột quỵ',          mc2.name_en = 'Stroke';
MERGE (mc3:MedicalCondition {slug: 'parkinson'})           SET mc3.name_vi = 'Bệnh Parkinson',   mc3.name_en = "Parkinson's disease";
MERGE (mc4:MedicalCondition {slug: 'traumatic_brain_injury'}) SET mc4.name_vi = 'Chấn thương sọ não', mc4.name_en = 'Traumatic brain injury';

// ---------- 5.10 INDUCED_BY edges (Substance-Induced Disorder → Substance) ----------
// Per DSM-5: substance-induced disorders are SEPARATE nodes from primary disorders.
// Primary MDD (slug:'mdd') is NOT induced by substances — it is an independent diagnosis.
// Substance-induced depressive disorders (alcohol_induced_depressive, stimulant_induced_depressive)
// are the correct targets of INDUCED_BY.
// Read as: disorder diagnosis is (partly) explained by substance mechanism — direction is Disorder → Substance.
// `context` distinguishes parallel edges (MERGE is per full property map).

MATCH (d:Disorder {slug: 'alcohol_induced_depressive'}),  (s:Substance {slug: 'alcohol'})   MERGE (d)-[ia1:INDUCED_BY {context: 'substance_use'}]->(s) SET ia1.intent = 'etiological_substance';
MATCH (d:Disorder {slug: 'alcohol_induced_depressive'}),  (s:Substance {slug: 'alcohol'})   MERGE (d)-[ia2:INDUCED_BY {context: 'withdrawal'}]->(s) SET ia2.intent = 'etiological_substance';
MATCH (d:Disorder {slug: 'stimulant_induced_depressive'}),(s:Substance {slug: 'stimulant'}) MERGE (d)-[ia3:INDUCED_BY {context: 'withdrawal'}]->(s) SET ia3.intent = 'etiological_substance';

// ---------- 5.11 RULE_OUT_SCREEN (Disorder → MedicalCondition) ----------
// Per DSM-5: hypothyroidism/stroke/etc. do NOT cause MDD; they cause
// "Depressive Disorder Due to Another Medical Condition" — a distinct diagnosis.
// Rel name reads as: when assessing this disorder, also screen / rule out these medical mimics.
// Property `intent` remains stable metadata for downstream logic.

MATCH (d:Disorder {slug: 'mdd'}), (mc:MedicalCondition {slug: 'hypothyroidism'})          MERGE (d)-[r1:RULE_OUT_SCREEN]->(mc) SET r1.intent = 'differential_screening';
MATCH (d:Disorder {slug: 'mdd'}), (mc:MedicalCondition {slug: 'stroke'})                  MERGE (d)-[r2:RULE_OUT_SCREEN]->(mc) SET r2.intent = 'differential_screening';
MATCH (d:Disorder {slug: 'mdd'}), (mc:MedicalCondition {slug: 'parkinson'})               MERGE (d)-[r3:RULE_OUT_SCREEN]->(mc) SET r3.intent = 'differential_screening';
MATCH (d:Disorder {slug: 'mdd'}), (mc:MedicalCondition {slug: 'traumatic_brain_injury'}) MERGE (d)-[r4:RULE_OUT_SCREEN]->(mc) SET r4.intent = 'differential_screening';

// ---------- 5.12 CognitiveDistortion (key renamed name→slug) ----------

MERGE (d1:CognitiveDistortion {slug: 'catastrophizing'})    SET d1.name_vi = 'Thảm họa hoá',              d1.name_en = 'Catastrophizing';
MERGE (d2:CognitiveDistortion {slug: 'black_and_white'})    SET d2.name_vi = 'Suy nghĩ trắng đen',        d2.name_en = 'Black-and-white thinking';
MERGE (d3:CognitiveDistortion {slug: 'mind_reading'})       SET d3.name_vi = 'Đọc suy nghĩ người khác',   d3.name_en = 'Mind reading';
MERGE (d4:CognitiveDistortion {slug: 'overgeneralization'}) SET d4.name_vi = 'Khái quát hoá quá mức',     d4.name_en = 'Overgeneralization';
MERGE (d5:CognitiveDistortion {slug: 'personalization'})    SET d5.name_vi = 'Đổ lỗi bản thân',           d5.name_en = 'Personalization';
MERGE (d6:CognitiveDistortion {slug: 'should_statements'})  SET d6.name_vi = 'Suy nghĩ phải/nên cứng nhắc', d6.name_en = 'Should statements';
MERGE (d7:CognitiveDistortion {slug: 'emotional_reasoning'})SET d7.name_vi = 'Suy luận cảm tính',         d7.name_en = 'Emotional reasoning';
MERGE (d8:CognitiveDistortion {slug: 'filtering'})          SET d8.name_vi = 'Chỉ thấy mặt tiêu cực',    d8.name_en = 'Mental filtering';
MERGE (d9:CognitiveDistortion {slug: 'labeling'})           SET d9.name_vi = 'Dán nhãn bản thân',         d9.name_en = 'Labeling';
MERGE (d10:CognitiveDistortion {slug: 'fortune_telling'})   SET d10.name_vi = 'Tiên tri tiêu cực',        d10.name_en = 'Fortune telling';

// CognitiveDistortion → Symptom (AMPLIFIES)
MATCH (d:CognitiveDistortion {slug: 'catastrophizing'}),    (s:Symptom {slug: 'excessive_worry'}) MERGE (d)-[:AMPLIFIES {strength: 0.85}]->(s);
MATCH (d:CognitiveDistortion {slug: 'catastrophizing'}),    (s:Symptom {slug: 'tension'})         MERGE (d)-[:AMPLIFIES {strength: 0.70}]->(s);
MATCH (d:CognitiveDistortion {slug: 'personalization'}),    (s:Symptom {slug: 'guilt'})           MERGE (d)-[:AMPLIFIES {strength: 0.90}]->(s);
MATCH (d:CognitiveDistortion {slug: 'personalization'}),    (s:Symptom {slug: 'low_mood'})        MERGE (d)-[:AMPLIFIES {strength: 0.75}]->(s);
MATCH (d:CognitiveDistortion {slug: 'black_and_white'}),    (s:Symptom {slug: 'low_mood'})        MERGE (d)-[:AMPLIFIES {strength: 0.75}]->(s);
MATCH (d:CognitiveDistortion {slug: 'black_and_white'}),    (s:Symptom {slug: 'anhedonia'})       MERGE (d)-[:AMPLIFIES {strength: 0.65}]->(s);
MATCH (d:CognitiveDistortion {slug: 'mind_reading'}),       (s:Symptom {slug: 'excessive_worry'}) MERGE (d)-[:AMPLIFIES {strength: 0.70}]->(s);
MATCH (d:CognitiveDistortion {slug: 'overgeneralization'}), (s:Symptom {slug: 'low_mood'})        MERGE (d)-[:AMPLIFIES {strength: 0.80}]->(s);
MATCH (d:CognitiveDistortion {slug: 'overgeneralization'}), (s:Symptom {slug: 'guilt'})           MERGE (d)-[:AMPLIFIES {strength: 0.65}]->(s);
MATCH (d:CognitiveDistortion {slug: 'should_statements'}),  (s:Symptom {slug: 'guilt'})           MERGE (d)-[:AMPLIFIES {strength: 0.80}]->(s);
MATCH (d:CognitiveDistortion {slug: 'emotional_reasoning'}),(s:Symptom {slug: 'excessive_worry'}) MERGE (d)-[:AMPLIFIES {strength: 0.72}]->(s);
MATCH (d:CognitiveDistortion {slug: 'filtering'}),          (s:Symptom {slug: 'anhedonia'})       MERGE (d)-[:AMPLIFIES {strength: 0.75}]->(s);
MATCH (d:CognitiveDistortion {slug: 'labeling'}),           (s:Symptom {slug: 'low_mood'})        MERGE (d)-[:AMPLIFIES {strength: 0.85}]->(s);
MATCH (d:CognitiveDistortion {slug: 'fortune_telling'}),    (s:Symptom {slug: 'excessive_worry'}) MERGE (d)-[:AMPLIFIES {strength: 0.88}]->(s);
MATCH (d:CognitiveDistortion {slug: 'fortune_telling'}),    (s:Symptom {slug: 'tension'})         MERGE (d)-[:AMPLIFIES {strength: 0.65}]->(s);


// =============================================================================
// SECTION 6 — TIER 3: INTERVENTION (Resource + CopingAction)
// =============================================================================

// ---------- 6.1 Resource nodes (no category string — use IN_RESOURCE_CATEGORY) ----------

MERGE (r001:Resource {resource_id: 'res_001'}) SET r001.title_vi = 'Thiền chánh niệm cho người lo âu', r001.format = 'audio',   r001.duration_sec = 600,  r001.type = 'guided_practice', r001.language = 'vi';
MERGE (r002:Resource {resource_id: 'res_002'}) SET r002.title_vi = 'The Midnight Woods',              r002.format = 'audio',   r002.duration_sec = 1800, r002.type = 'sleep_audio',     r002.language = 'en';
MERGE (r003:Resource {resource_id: 'res_003'}) SET r003.title_vi = 'Thở 4-7-8',                      r003.format = 'audio',   r003.duration_sec = 180,  r003.type = 'breath_exercise', r003.language = 'vi';
MERGE (r004:Resource {resource_id: 'res_004'}) SET r004.title_vi = 'Nhận diện suy nghĩ tiêu cực',    r004.format = 'article', r004.duration_sec = 300,  r004.type = 'psychoeducation', r004.language = 'vi';
// res_005: dedicated body scan resource (distinct from mindfulness in res_001)
MERGE (r005:Resource {resource_id: 'res_005'}) SET r005.title_vi = 'Quét cơ thể toàn thân',          r005.format = 'audio',   r005.duration_sec = 900,  r005.type = 'guided_practice', r005.language = 'vi';

// Resource → ResourceCategory (use most specific sub-category)
MATCH (r:Resource {resource_id: 'res_001'}), (c:ResourceCategory {slug: 'mindfulness'})      MERGE (r)-[:IN_RESOURCE_CATEGORY]->(c);
MATCH (r:Resource {resource_id: 'res_002'}), (c:ResourceCategory {slug: 'sleep_soundscape'}) MERGE (r)-[:IN_RESOURCE_CATEGORY]->(c);
MATCH (r:Resource {resource_id: 'res_003'}), (c:ResourceCategory {slug: 'breathwork'})       MERGE (r)-[:IN_RESOURCE_CATEGORY]->(c);
MATCH (r:Resource {resource_id: 'res_004'}), (c:ResourceCategory {slug: 'cbt_education'})    MERGE (r)-[:IN_RESOURCE_CATEGORY]->(c);
MATCH (r:Resource {resource_id: 'res_005'}), (c:ResourceCategory {slug: 'body_scan'})        MERGE (r)-[:IN_RESOURCE_CATEGORY]->(c);

// Resource → Symptom (HELPS_WITH)
MATCH (r:Resource {resource_id: 'res_001'}), (s:Symptom {slug: 'excessive_worry'})    MERGE (r)-[:HELPS_WITH {evidence: 'clinical', strength: 0.80}]->(s);
MATCH (r:Resource {resource_id: 'res_001'}), (s:Symptom {slug: 'tension'})            MERGE (r)-[:HELPS_WITH {evidence: 'clinical', strength: 0.70}]->(s);
MATCH (r:Resource {resource_id: 'res_002'}), (s:Symptom {slug: 'insomnia'})           MERGE (r)-[:HELPS_WITH {evidence: 'clinical', strength: 0.85}]->(s);
MATCH (r:Resource {resource_id: 'res_003'}), (s:Symptom {slug: 'insomnia'})           MERGE (r)-[:HELPS_WITH {evidence: 'clinical', strength: 0.80}]->(s);
MATCH (r:Resource {resource_id: 'res_003'}), (s:Symptom {slug: 'tension'})            MERGE (r)-[:HELPS_WITH {evidence: 'clinical', strength: 0.75}]->(s);
MATCH (r:Resource {resource_id: 'res_003'}), (s:Symptom {slug: 'excessive_worry'})    MERGE (r)-[:HELPS_WITH {evidence: 'clinical', strength: 0.65}]->(s);
MATCH (r:Resource {resource_id: 'res_004'}), (s:Symptom {slug: 'guilt'})              MERGE (r)-[:HELPS_WITH {evidence: 'observed', strength: 0.70}]->(s);
MATCH (r:Resource {resource_id: 'res_004'}), (s:Symptom {slug: 'poor_concentration'}) MERGE (r)-[:HELPS_WITH {evidence: 'observed', strength: 0.65}]->(s);
MATCH (r:Resource {resource_id: 'res_005'}), (s:Symptom {slug: 'tension'})            MERGE (r)-[:HELPS_WITH {evidence: 'clinical', strength: 0.80}]->(s);
MATCH (r:Resource {resource_id: 'res_005'}), (s:Symptom {slug: 'insomnia'})           MERGE (r)-[:HELPS_WITH {evidence: 'clinical', strength: 0.65}]->(s);

// ---------- 6.2 CopingAction nodes + categorization + targets ----------

MERGE (ca1:CopingAction {action_id: 'breathing_478'})    SET ca1.name_vi = 'Thở 4-7-8',    ca1.is_adaptive = true;
MERGE (ca2:CopingAction {action_id: 'body_scan'})        SET ca2.name_vi = 'Quét cơ thể', ca2.is_adaptive = true;
MERGE (ca3:CopingAction {action_id: 'sleep_soundscape'}) SET ca3.name_vi = 'Âm thanh ngủ', ca3.is_adaptive = true;
MERGE (ca4:CopingAction {action_id: 'cbt_reading'})      SET ca4.name_vi = 'Đọc bài CBT', ca4.is_adaptive = true;
MERGE (ca5:CopingAction {action_id: 'journaling'})       SET ca5.name_vi = 'Viết nhật ký', ca5.is_adaptive = true;
MERGE (ca6:CopingAction {action_id: 'talk_to_someone'})  SET ca6.name_vi = 'Nói chuyện với người tin cậy', ca6.is_adaptive = true;

// CopingAction → CopingCategory
MATCH (a:CopingAction {action_id: 'breathing_478'}),    (c:CopingCategory {slug: 'somatic'})    MERGE (a)-[:IN_COPING_CATEGORY]->(c);
MATCH (a:CopingAction {action_id: 'body_scan'}),        (c:CopingCategory {slug: 'somatic'})    MERGE (a)-[:IN_COPING_CATEGORY]->(c);
MATCH (a:CopingAction {action_id: 'sleep_soundscape'}), (c:CopingCategory {slug: 'behavioral'}) MERGE (a)-[:IN_COPING_CATEGORY]->(c);
MATCH (a:CopingAction {action_id: 'cbt_reading'}),      (c:CopingCategory {slug: 'cognitive'})  MERGE (a)-[:IN_COPING_CATEGORY]->(c);
MATCH (a:CopingAction {action_id: 'journaling'}),       (c:CopingCategory {slug: 'cognitive'})  MERGE (a)-[:IN_COPING_CATEGORY]->(c);
MATCH (a:CopingAction {action_id: 'talk_to_someone'}),  (c:CopingCategory {slug: 'social'})     MERGE (a)-[:IN_COPING_CATEGORY]->(c);

// CopingAction → Resource (IS_RESOURCE — single source of truth)
MATCH (a:CopingAction {action_id: 'breathing_478'}),    (r:Resource {resource_id: 'res_003'}) MERGE (a)-[:IS_RESOURCE]->(r);
MATCH (a:CopingAction {action_id: 'body_scan'}),        (r:Resource {resource_id: 'res_005'}) MERGE (a)-[:IS_RESOURCE]->(r);
MATCH (a:CopingAction {action_id: 'sleep_soundscape'}), (r:Resource {resource_id: 'res_002'}) MERGE (a)-[:IS_RESOURCE]->(r);
MATCH (a:CopingAction {action_id: 'cbt_reading'}),      (r:Resource {resource_id: 'res_004'}) MERGE (a)-[:IS_RESOURCE]->(r);

// CopingAction → Symptom (TARGETS_SYMPTOM, direct clinical target)
MATCH (a:CopingAction {action_id: 'breathing_478'}), (s:Symptom {slug: 'tension'})            MERGE (a)-[:TARGETS_SYMPTOM {strength: 0.80}]->(s);
MATCH (a:CopingAction {action_id: 'breathing_478'}), (s:Symptom {slug: 'excessive_worry'})    MERGE (a)-[:TARGETS_SYMPTOM {strength: 0.70}]->(s);
MATCH (a:CopingAction {action_id: 'body_scan'}),     (s:Symptom {slug: 'tension'})            MERGE (a)-[:TARGETS_SYMPTOM {strength: 0.75}]->(s);
MATCH (a:CopingAction {action_id: 'body_scan'}),     (s:Symptom {slug: 'insomnia'})           MERGE (a)-[:TARGETS_SYMPTOM {strength: 0.60}]->(s);
MATCH (a:CopingAction {action_id: 'sleep_soundscape'}), (s:Symptom {slug: 'insomnia'})        MERGE (a)-[:TARGETS_SYMPTOM {strength: 0.85}]->(s);
MATCH (a:CopingAction {action_id: 'cbt_reading'}),   (s:Symptom {slug: 'guilt'})              MERGE (a)-[:TARGETS_SYMPTOM {strength: 0.70}]->(s);
MATCH (a:CopingAction {action_id: 'cbt_reading'}),   (s:Symptom {slug: 'low_mood'})           MERGE (a)-[:TARGETS_SYMPTOM {strength: 0.65}]->(s);
MATCH (a:CopingAction {action_id: 'journaling'}),    (s:Symptom {slug: 'excessive_worry'})    MERGE (a)-[:TARGETS_SYMPTOM {strength: 0.60}]->(s);
MATCH (a:CopingAction {action_id: 'journaling'}),    (s:Symptom {slug: 'low_mood'})           MERGE (a)-[:TARGETS_SYMPTOM {strength: 0.55}]->(s);
MATCH (a:CopingAction {action_id: 'talk_to_someone'}),(s:Symptom {slug: 'low_mood'})          MERGE (a)-[:TARGETS_SYMPTOM {strength: 0.70}]->(s);


// =============================================================================
// SECTION 7 — TIER 3: TRIGGER + EMOTION + BRIDGES
// =============================================================================

// ---------- 7.1 Trigger (external situational stressors, NOT symptoms/disorders) ----------

MERGE (tg1:Trigger {slug: 'deadline'})              SET tg1.name_vi  = 'Áp lực thời hạn', tg1.name_en = 'Deadline pressure';
// 'insomnia' renamed to 'sleep_deprivation' — insomnia is a Symptom node, not a trigger.
// The trigger is the external condition of insufficient/disrupted sleep.
MERGE (tg2:Trigger {slug: 'sleep_deprivation'})     SET tg2.name_vi  = 'Thiếu ngủ / mất ngủ', tg2.name_en = 'Sleep deprivation';
MERGE (tg3:Trigger {slug: 'loneliness'})            SET tg3.name_vi  = 'Cô đơn', tg3.name_en = 'Loneliness';
MERGE (tg4:Trigger {slug: 'academic_pressure'})     SET tg4.name_vi  = 'Áp lực học tập', tg4.name_en = 'Academic pressure';
MERGE (tg5:Trigger {slug: 'relationship_conflict'}) SET tg5.name_vi  = 'Xung đột trong mối quan hệ', tg5.name_en = 'Relationship conflict';
MERGE (tg6:Trigger {slug: 'financial_stress'})      SET tg6.name_vi  = 'Căng thẳng tài chính', tg6.name_en = 'Financial stress';
MERGE (tg7:Trigger {slug: 'family_issue'})          SET tg7.name_vi  = 'Vấn đề gia đình', tg7.name_en = 'Family issue';
MERGE (tg8:Trigger {slug: 'self_worth'})            SET tg8.name_vi  = 'Tự ti / giá trị bản thân', tg8.name_en = 'Self-worth concern';
// 'social_anxiety' renamed to 'social_situations' — Social Anxiety Disorder (F40.10) is a Disorder node.
// The trigger is facing social situations, not the disorder itself.
MERGE (tg9:Trigger {slug: 'social_situations'})     SET tg9.name_vi  = 'Tình huống xã hội', tg9.name_en = 'Social situations';
MERGE (tg10:Trigger {slug: 'future_uncertainty'})   SET tg10.name_vi = 'Bất định về tương lai', tg10.name_en = 'Future uncertainty';
MERGE (tg11:Trigger {slug: 'work_stress'})          SET tg11.name_vi = 'Áp lực công việc', tg11.name_en = 'Work stress';
MERGE (tg12:Trigger {slug: 'health_concern'})       SET tg12.name_vi = 'Lo lắng về sức khoẻ', tg12.name_en = 'Health concern';

// Trigger → Symptom (MANIFESTS_AS) — situational trigger leads to this symptom presentation
MATCH (t:Trigger {slug: 'sleep_deprivation'}), (s:Symptom {slug: 'fatigue'})           MERGE (t)-[:MANIFESTS_AS]->(s);
MATCH (t:Trigger {slug: 'sleep_deprivation'}), (s:Symptom {slug: 'poor_concentration'}) MERGE (t)-[:MANIFESTS_AS]->(s);
MATCH (t:Trigger {slug: 'loneliness'}),        (s:Symptom {slug: 'low_mood'})           MERGE (t)-[:MANIFESTS_AS]->(s);
MATCH (t:Trigger {slug: 'social_situations'}), (s:Symptom {slug: 'excessive_worry'})    MERGE (t)-[:MANIFESTS_AS]->(s);
MATCH (t:Trigger {slug: 'social_situations'}), (s:Symptom {slug: 'tension'})            MERGE (t)-[:MANIFESTS_AS]->(s);
MATCH (t:Trigger {slug: 'self_worth'}),        (s:Symptom {slug: 'guilt'})              MERGE (t)-[:MANIFESTS_AS]->(s);

// Extended Trigger → Symptom (MANIFESTS_AS) — broader seed coverage for routing / education
MATCH (t:Trigger {slug: 'deadline'}), (s:Symptom {slug: 'tension'}) MERGE (t)-[:MANIFESTS_AS]->(s);
MATCH (t:Trigger {slug: 'deadline'}), (s:Symptom {slug: 'poor_concentration'}) MERGE (t)-[:MANIFESTS_AS]->(s);
MATCH (t:Trigger {slug: 'work_stress'}), (s:Symptom {slug: 'fatigue'}) MERGE (t)-[:MANIFESTS_AS]->(s);
MATCH (t:Trigger {slug: 'work_stress'}), (s:Symptom {slug: 'tension'}) MERGE (t)-[:MANIFESTS_AS]->(s);
MATCH (t:Trigger {slug: 'financial_stress'}), (s:Symptom {slug: 'excessive_worry'}) MERGE (t)-[:MANIFESTS_AS]->(s);
MATCH (t:Trigger {slug: 'financial_stress'}), (s:Symptom {slug: 'insomnia'}) MERGE (t)-[:MANIFESTS_AS]->(s);
MATCH (t:Trigger {slug: 'academic_pressure'}), (s:Symptom {slug: 'excessive_worry'}) MERGE (t)-[:MANIFESTS_AS]->(s);
MATCH (t:Trigger {slug: 'academic_pressure'}), (s:Symptom {slug: 'poor_concentration'}) MERGE (t)-[:MANIFESTS_AS]->(s);
MATCH (t:Trigger {slug: 'family_issue'}), (s:Symptom {slug: 'low_mood'}) MERGE (t)-[:MANIFESTS_AS]->(s);
MATCH (t:Trigger {slug: 'family_issue'}), (s:Symptom {slug: 'excessive_worry'}) MERGE (t)-[:MANIFESTS_AS]->(s);
MATCH (t:Trigger {slug: 'health_concern'}), (s:Symptom {slug: 'excessive_worry'}) MERGE (t)-[:MANIFESTS_AS]->(s);
MATCH (t:Trigger {slug: 'health_concern'}), (s:Symptom {slug: 'tension'}) MERGE (t)-[:MANIFESTS_AS]->(s);
MATCH (t:Trigger {slug: 'future_uncertainty'}), (s:Symptom {slug: 'excessive_worry'}) MERGE (t)-[:MANIFESTS_AS]->(s);
MATCH (t:Trigger {slug: 'relationship_conflict'}), (s:Symptom {slug: 'irritability'}) MERGE (t)-[:MANIFESTS_AS]->(s);
MATCH (t:Trigger {slug: 'relationship_conflict'}), (s:Symptom {slug: 'low_mood'}) MERGE (t)-[:MANIFESTS_AS]->(s);
MATCH (t:Trigger {slug: 'loneliness'}), (s:Symptom {slug: 'excessive_worry'}) MERGE (t)-[:MANIFESTS_AS]->(s);

// Trigger → CognitiveDistortion (COMMONLY_TRIGGERS — CBT pathway)
MATCH (t:Trigger {slug: 'future_uncertainty'}), (d:CognitiveDistortion {slug: 'catastrophizing'}) MERGE (t)-[:COMMONLY_TRIGGERS {strength: 0.80}]->(d);
MATCH (t:Trigger {slug: 'future_uncertainty'}), (d:CognitiveDistortion {slug: 'fortune_telling'}) MERGE (t)-[:COMMONLY_TRIGGERS {strength: 0.85}]->(d);
MATCH (t:Trigger {slug: 'self_worth'}),         (d:CognitiveDistortion {slug: 'labeling'})        MERGE (t)-[:COMMONLY_TRIGGERS {strength: 0.75}]->(d);
MATCH (t:Trigger {slug: 'self_worth'}),         (d:CognitiveDistortion {slug: 'personalization'}) MERGE (t)-[:COMMONLY_TRIGGERS {strength: 0.70}]->(d);
MATCH (t:Trigger {slug: 'relationship_conflict'}),(d:CognitiveDistortion {slug: 'mind_reading'})  MERGE (t)-[:COMMONLY_TRIGGERS {strength: 0.75}]->(d);
MATCH (t:Trigger {slug: 'academic_pressure'}),  (d:CognitiveDistortion {slug: 'catastrophizing'}) MERGE (t)-[:COMMONLY_TRIGGERS {strength: 0.70}]->(d);
MATCH (t:Trigger {slug: 'deadline'}),           (d:CognitiveDistortion {slug: 'catastrophizing'}) MERGE (t)-[:COMMONLY_TRIGGERS {strength: 0.65}]->(d);

// ---------- 7.2 Emotion (key renamed label→slug, added valence) ----------

MERGE (em1:Emotion {slug: 'stressed'})    SET em1.name_vi = 'Căng thẳng',  em1.name_en = 'Stressed',    em1.valence = 'negative';
MERGE (em2:Emotion {slug: 'anxious'})     SET em2.name_vi = 'Lo lắng',     em2.name_en = 'Anxious',     em2.valence = 'negative';
MERGE (em3:Emotion {slug: 'sad'})         SET em3.name_vi = 'Buồn',        em3.name_en = 'Sad',         em3.valence = 'negative';
MERGE (em4:Emotion {slug: 'hopeful'})     SET em4.name_vi = 'Hy vọng',     em4.name_en = 'Hopeful',     em4.valence = 'positive';
MERGE (em5:Emotion {slug: 'neutral'})     SET em5.name_vi = 'Bình thản',   em5.name_en = 'Neutral',     em5.valence = 'neutral';
MERGE (em6:Emotion {slug: 'angry'})       SET em6.name_vi = 'Tức giận',    em6.name_en = 'Angry',       em6.valence = 'negative';
MERGE (em7:Emotion {slug: 'hopeless'})    SET em7.name_vi = 'Tuyệt vọng',  em7.name_en = 'Hopeless',    em7.valence = 'negative';
MERGE (em8:Emotion {slug: 'overwhelmed'}) SET em8.name_vi = 'Quá tải',     em8.name_en = 'Overwhelmed', em8.valence = 'negative';
MERGE (em9:Emotion {slug: 'lonely'})      SET em9.name_vi = 'Cô đơn',      em9.name_en = 'Lonely',      em9.valence = 'negative';
MERGE (em10:Emotion {slug: 'ashamed'})    SET em10.name_vi = 'Xấu hổ',     em10.name_en = 'Ashamed',    em10.valence = 'negative';


// =============================================================================
// SECTION 8 — SAFETY KEYWORDS
// =============================================================================

MERGE (k1:SafetyKeyword {phrase: 'muốn chết'})           SET k1.severity = 5,  k1.lang = 'vi';
MERGE (k2:SafetyKeyword {phrase: 'không muốn sống nữa'}) SET k2.severity = 5,  k2.lang = 'vi';
MERGE (k3:SafetyKeyword {phrase: 'tự làm hại bản thân'}) SET k3.severity = 5,  k3.lang = 'vi';
MERGE (k4:SafetyKeyword {phrase: 'tự tử'})               SET k4.severity = 5,  k4.lang = 'vi';
MERGE (k5:SafetyKeyword {phrase: 'kết thúc tất cả'})     SET k5.severity = 4,  k5.lang = 'vi';
MERGE (k6:SafetyKeyword {phrase: 'tự làm hại'})          SET k6.severity = 4,  k6.lang = 'vi';
MERGE (k7:SafetyKeyword {phrase: 'biến mất mãi mãi'})    SET k7.severity = 4,  k7.lang = 'vi';
MERGE (k8:SafetyKeyword {phrase: 'không muốn tồn tại'})  SET k8.severity = 4,  k8.lang = 'vi';
MERGE (k9:SafetyKeyword {phrase: 'chán sống'})           SET k9.severity = 3,  k9.lang = 'vi';
MERGE (k10:SafetyKeyword {phrase: 'biến mất'})           SET k10.severity = 3, k10.lang = 'vi';
MERGE (k11:SafetyKeyword {phrase: 'want to die'})        SET k11.severity = 5, k11.lang = 'en';
MERGE (k12:SafetyKeyword {phrase: 'end it all'})         SET k12.severity = 5, k12.lang = 'en';
MERGE (k13:SafetyKeyword {phrase: 'self harm'})          SET k13.severity = 4, k13.lang = 'en';

MATCH (k:SafetyKeyword), (s:Symptom {slug: 'suicidal_ideation'})
WHERE k.severity >= 4
MERGE (k)-[:INDICATES {confidence: 0.90}]->(s);

MATCH (k:SafetyKeyword {severity: 3}), (s:Symptom {slug: 'suicidal_ideation'})
MERGE (k)-[:INDICATES {confidence: 0.60}]->(s);

// Only high-severity keywords flag PHQ-9 item 9 (suicidal ideation probe) — avoids over-linking soft phrases.
MATCH (k:SafetyKeyword), (q:Item {code: 'PHQ9_Q9'})
WHERE k.severity >= 4
MERGE (k)-[:FLAGS_ITEM]->(q);


// =============================================================================
// SECTION 9 — RUNTIME CONTRACTS (User Memory Graph)
// These patterns are executed by outbox_worker.py, NOT by this script.
// =============================================================================

// ---------- 9.1 User ----------
// MERGE (u:User {user_id: $user_id})
// ON CREATE SET u.created_at = $now;

// ---------- 9.2 Session (NEW: dominant_emotion is an edge, not string) ----------
// MERGE (s:Session {session_id: $session_id})
// ON CREATE SET s.started_at        = $started_at,
//               s.ended_at          = $ended_at,
//               s.turn_count        = $turn_count,
//               s.crisis_level_peak = $crisis_level_peak,
//               s.sos_triggered     = $sos_triggered,
//               s.summary_hash      = $summary_hash;
// MERGE (u:User {user_id: $user_id})-[:HAS_SESSION]->(s);
//
// Dominant emotion → edge (replaces property):
// MATCH (s:Session {session_id: $session_id}), (e:Emotion {slug: $dominant_emotion})
// MERGE (s)-[:HAS_DOMINANT_EMOTION]->(e);
//
// For each trigger mentioned:
// MERGE (t:Trigger {slug: $trigger_slug})
// MERGE (s)-[:MENTIONS_TRIGGER]->(t);

// ---------- 9.3 EXPERIENCED (User → Trigger) ----------
// MERGE (u:User {user_id: $user_id})
// MERGE (t:Trigger {slug: $trigger_slug})
// MERGE (u)-[r:EXPERIENCED]->(t)
// ON CREATE SET r.count = 1, r.first_seen = $observed_at, r.last_seen = $observed_at
// ON MATCH  SET r.count = r.count + 1, r.last_seen = $observed_at;

// ---------- 9.4 FELT (User → Emotion) ----------
// MERGE (u:User {user_id: $user_id})
// MERGE (e:Emotion {slug: $emotion_slug})
// MERGE (u)-[r:FELT]->(e)
// ON CREATE SET r.count = 1, r.first_seen = $observed_at, r.last_seen = $observed_at
// ON MATCH  SET r.count = r.count + 1, r.last_seen = $observed_at;

// ---------- 9.5 USED_COPING (User → CopingAction) ----------
// MERGE (u:User {user_id: $user_id})
// MERGE (c:CopingAction {action_id: $action_id})
// MERGE (u)-[r:USED_COPING]->(c)
// ON CREATE SET r.effectiveness = $effective_score, r.count = 1,
//               r.first_used = $attempted_at, r.last_used = $attempted_at,
//               r.last_emotion = $emotion_slug
// ON MATCH  SET r.effectiveness = (r.effectiveness * r.count + $effective_score) / (r.count + 1),
//               r.count = r.count + 1, r.last_used = $attempted_at,
//               r.last_emotion = $emotion_slug;

// ---------- 9.6 MemoryNode ----------
// MERGE (m:MemoryNode {memory_id: $memory_id})
// ON CREATE SET m.memory_type = $memory_type, m.importance = $importance, m.created_at = $now;
// MERGE (s:Session {session_id: $session_id})-[:CONTAINS_MEMORY]->(m);


// =============================================================================
// SECTION 10 — GraphRAG (vector indexes) + Multi-Agent + assessment-related priors
// Embeddings: optional property `embedding` (LIST<FLOAT>) on indexed labels; populate via ETL/worker.
// =============================================================================

// ---------- 10.1 VECTOR INDEXES (GraphRAG semantic retrieval) ----------
// Requires: property `embedding` LIST<FLOAT> on each indexed label, fixed size = dimensions.

CREATE VECTOR INDEX idx_symptom_embedding IF NOT EXISTS
FOR (s:Symptom) ON (s.embedding)
OPTIONS { indexConfig: {
  `vector.dimensions`: 1536,
  `vector.similarity_function`: 'cosine'
}};

CREATE VECTOR INDEX idx_disorder_embedding IF NOT EXISTS
FOR (d:Disorder) ON (d.embedding)
OPTIONS { indexConfig: {
  `vector.dimensions`: 1536,
  `vector.similarity_function`: 'cosine'
}};

CREATE VECTOR INDEX idx_resource_embedding IF NOT EXISTS
FOR (r:Resource) ON (r.embedding)
OPTIONS { indexConfig: {
  `vector.dimensions`: 1536,
  `vector.similarity_function`: 'cosine'
}};

CREATE VECTOR INDEX idx_trigger_embedding IF NOT EXISTS
FOR (t:Trigger) ON (t.embedding)
OPTIONS { indexConfig: {
  `vector.dimensions`: 1536,
  `vector.similarity_function`: 'cosine'
}};

CREATE VECTOR INDEX idx_coping_action_embedding IF NOT EXISTS
FOR (c:CopingAction) ON (c.embedding)
OPTIONS { indexConfig: {
  `vector.dimensions`: 1536,
  `vector.similarity_function`: 'cosine'
}};

CREATE VECTOR INDEX idx_emotion_embedding IF NOT EXISTS
FOR (e:Emotion) ON (e.embedding)
OPTIONS { indexConfig: {
  `vector.dimensions`: 1536,
  `vector.similarity_function`: 'cosine'
}};


// ---------- 10.2 Multi-Agent orchestration (seed) ----------

MERGE (ag_clin:Agent {slug: 'clinical_assessor'})
    SET ag_clin.name_en = 'Clinical Assessment Agent',
        ag_clin.name_vi = 'Agent đánh giá lâm sàng',
        ag_clin.system_prompt_ref = 'prompt_v1_clin',
        ag_clin.tier = 'clinical';

MERGE (ag_int:Agent {slug: 'intervention_guide'})
    SET ag_int.name_en = 'Intervention & Coping Agent',
        ag_int.name_vi = 'Agent can thiệp & đối phó',
        ag_int.system_prompt_ref = 'prompt_v1_int',
        ag_int.tier = 'intervention';

MERGE (ag_safe:Agent {slug: 'safety_triage'})
    SET ag_safe.name_en = 'Safety Triage Agent',
        ag_safe.name_vi = 'Agent sàng lọc an toàn',
        ag_safe.system_prompt_ref = 'prompt_v1_safety',
        ag_safe.tier = 'safety';

MERGE (cap_dx:AgentCapability {slug: 'differential_diagnosis'})
    SET cap_dx.name_en = 'Differential diagnosis routing', cap_dx.name_vi = 'Phân luồng chẩn đoán phân biệt';
MERGE (cap_instr:AgentCapability {slug: 'instrument_scoring'})
    SET cap_instr.name_en = 'PHQ/GAD scoring & interpretation', cap_instr.name_vi = 'Chấm điểm & diễn giải PHQ/GAD';
MERGE (cap_res:AgentCapability {slug: 'resource_matching'})
    SET cap_res.name_en = 'Resource / coping matching', cap_res.name_vi = 'Ghép tài nguyên / coping';

MATCH (ag:Agent {slug: 'clinical_assessor'}), (cap:AgentCapability {slug: 'differential_diagnosis'})
MERGE (ag)-[:HAS_CAPABILITY]->(cap);
MATCH (ag:Agent {slug: 'clinical_assessor'}), (cap:AgentCapability {slug: 'instrument_scoring'})
MERGE (ag)-[:HAS_CAPABILITY]->(cap);
MATCH (ag:Agent {slug: 'intervention_guide'}), (cap:AgentCapability {slug: 'resource_matching'})
MERGE (ag)-[:HAS_CAPABILITY]->(cap);

// Agent → taxonomy roots they own (orchestration graph for the router)
MATCH (ag:Agent {slug: 'clinical_assessor'}), (c:DisorderCategory)
MERGE (ag)-[:HANDLES_DOMAIN]->(c);

MATCH (ag:Agent {slug: 'intervention_guide'}), (rc:ResourceCategory)
MERGE (ag)-[:HANDLES_DOMAIN]->(rc);

MATCH (ag:Agent {slug: 'safety_triage'}), (sc:SymptomCategory {slug: 'safety'})
MERGE (ag)-[:HANDLES_DOMAIN]->(sc);

MATCH (ag:Agent {slug: 'safety_triage'}), (dc:DisorderCategory)
WHERE dc.slug IN ['depressive_disorders', 'psychotic_disorders', 'trauma_stress_disorders', 'substance_disorders']
MERGE (ag)-[:HANDLES_DOMAIN]->(dc);


// ---------- 10.3 Trigger → Emotion (static priors for agents / GraphRAG) ----------

MATCH (t:Trigger {slug: 'deadline'}),       (e:Emotion {slug: 'stressed'})    MERGE (t)-[:EVOKES {weight: 0.75, model: 'prior_seed'}]->(e);
MATCH (t:Trigger {slug: 'loneliness'}),    (e:Emotion {slug: 'sad'})        MERGE (t)-[:EVOKES {weight: 0.70, model: 'prior_seed'}]->(e);
MATCH (t:Trigger {slug: 'loneliness'}),    (e:Emotion {slug: 'lonely'})     MERGE (t)-[:EVOKES {weight: 0.85, model: 'prior_seed'}]->(e);
MATCH (t:Trigger {slug: 'academic_pressure'}),(e:Emotion {slug: 'anxious'}) MERGE (t)-[:EVOKES {weight: 0.72, model: 'prior_seed'}]->(e);
MATCH (t:Trigger {slug: 'work_stress'}),   (e:Emotion {slug: 'overwhelmed'}) MERGE (t)-[:EVOKES {weight: 0.68, model: 'prior_seed'}]->(e);
MATCH (t:Trigger {slug: 'financial_stress'}),(e:Emotion {slug: 'anxious'}) MERGE (t)-[:EVOKES {weight: 0.65, model: 'prior_seed'}]->(e);
MATCH (t:Trigger {slug: 'relationship_conflict'}),(e:Emotion {slug: 'angry'}) MERGE (t)-[:EVOKES {weight: 0.60, model: 'prior_seed'}]->(e);


// ---------- 10.4 MedicalCondition → Symptom (simplified physiological priors) ----------
// NOT a substitute for full comorbidity modeling — seed for reasoning / education.

MATCH (mc:MedicalCondition {slug: 'hypothyroidism'}), (s:Symptom {slug: 'fatigue'})
MERGE (mc)-[:CAUSES_SYMPTOM {pathway: 'endocrine', confidence: 'seed_simplified'}]->(s);

MATCH (mc:MedicalCondition {slug: 'stroke'}), (s:Symptom {slug: 'poor_concentration'})
MERGE (mc)-[:CAUSES_SYMPTOM {pathway: 'neurologic', confidence: 'seed_simplified'}]->(s);

MATCH (mc:MedicalCondition {slug: 'parkinson'}), (s:Symptom {slug: 'psychomotor_disturbance'})
MERGE (mc)-[:CAUSES_SYMPTOM {pathway: 'neurologic', confidence: 'seed_simplified'}]->(s);

MATCH (mc:MedicalCondition {slug: 'traumatic_brain_injury'}), (s:Symptom {slug: 'poor_concentration'})
MERGE (mc)-[:CAUSES_SYMPTOM {pathway: 'neurologic', confidence: 'seed_simplified'}]->(s);

MATCH (mc:MedicalCondition {slug: 'traumatic_brain_injury'}), (s:Symptom {slug: 'fatigue'})
MERGE (mc)-[:CAUSES_SYMPTOM {pathway: 'neurologic', confidence: 'seed_simplified'}]->(s);


// ---------- 10.5 Coping: adaptive flag + maladaptive example linked to Substance ----------

MATCH (ca:CopingAction)
WHERE ca.action_id IN ['breathing_478', 'body_scan', 'sleep_soundscape', 'cbt_reading', 'journaling', 'talk_to_someone']
SET ca.is_adaptive = true;

MERGE (ca_bad:CopingAction {action_id: 'alcohol_self_medication'})
    SET ca_bad.name_vi = 'Tự an ủi bằng rượu (tiêu cực)',
        ca_bad.name_en = 'Self-medicating with alcohol (maladaptive)',
        ca_bad.is_adaptive = false;

MATCH (ca_bad:CopingAction {action_id: 'alcohol_self_medication'}), (c:CopingCategory {slug: 'behavioral'})
MERGE (ca_bad)-[:IN_COPING_CATEGORY]->(c);

MATCH (ca_bad:CopingAction {action_id: 'alcohol_self_medication'}), (sub:Substance {slug: 'alcohol'})
MERGE (ca_bad)-[:INVOLVES_SUBSTANCE {role: 'maladaptive_coping'}]->(sub);


// ---------- 10.6 Substance ↔ stressors & symptoms (seed priors; not clinical diagnosis) ----------
// AGGRAVATES_TRIGGER: substance context worsens situational triggers (routing / education).
MATCH (sub:Substance {slug: 'stimulant'}), (t:Trigger {slug: 'sleep_deprivation'})
MERGE (sub)-[:AGGRAVATES_TRIGGER {weight: 0.65, model: 'prior_seed'}]->(t);
MATCH (sub:Substance {slug: 'alcohol'}), (t:Trigger {slug: 'health_concern'})
MERGE (sub)-[:AGGRAVATES_TRIGGER {weight: 0.55, model: 'prior_seed'}]->(t);
MATCH (sub:Substance {slug: 'alcohol'}), (t:Trigger {slug: 'family_issue'})
MERGE (sub)-[:AGGRAVATES_TRIGGER {weight: 0.45, model: 'prior_seed'}]->(t);
MATCH (sub:Substance {slug: 'opioid'}), (t:Trigger {slug: 'health_concern'})
MERGE (sub)-[:AGGRAVATES_TRIGGER {weight: 0.50, model: 'prior_seed'}]->(t);

// MODULATES_SYMPTOM: direct substance–symptom modulation (distinct from Disorder-[:INDUCED_BY]->Substance).
MATCH (sub:Substance {slug: 'stimulant'}), (s:Symptom {slug: 'insomnia'})
MERGE (sub)-[:MODULATES_SYMPTOM {mechanism: 'use_or_withdrawal', model: 'prior_seed'}]->(s);
MATCH (sub:Substance {slug: 'alcohol'}), (s:Symptom {slug: 'fatigue'})
MERGE (sub)-[:MODULATES_SYMPTOM {mechanism: 'use_or_withdrawal', model: 'prior_seed'}]->(s);
MATCH (sub:Substance {slug: 'opioid'}), (s:Symptom {slug: 'fatigue'})
MERGE (sub)-[:MODULATES_SYMPTOM {mechanism: 'use_or_withdrawal', model: 'prior_seed'}]->(s);
MATCH (sub:Substance {slug: 'cannabis'}), (s:Symptom {slug: 'appetite_change'})
MERGE (sub)-[:MODULATES_SYMPTOM {mechanism: 'acute_use', model: 'prior_seed'}]->(s);


// ---------- 10.7 Runtime contract: Assessment history (implement in worker) ----------
// Pattern: one completed administration = one :Assessment node + link to user & instrument.
//
// MERGE (u:User {user_id: $user_id})
// MERGE (i:Instrument {code: $instrument_code})
// CREATE (a:Assessment {assessment_id: $assessment_id})
// SET a.completed_at = datetime($completed_at),
//     a.total_score = $total_score,
//     a.severity_label = $severity_label,
//     a.item_scores_json = $item_scores_json
// MERGE (u)-[:SUBMITTED_ASSESSMENT]->(a)
// MERGE (a)-[:USED_INSTRUMENT]->(i);
//
// Optional: link session MERGE (s:Session {session_id: $session_id}) MERGE (s)-[:INCLUDES_ASSESSMENT]->(a);


// =============================================================================
// SECTION 11 — Rel-type normalization (v3.2 → v3.3; idempotent on fresh graphs)
// Run after seed so upgraded databases drop legacy polymorphic :IN_CATEGORY and old rel names.
// =============================================================================

MATCH (d:Disorder)-[r:IN_CATEGORY]->(c:DisorderCategory)
MERGE (d)-[:IN_DISORDER_CATEGORY]->(c)
DELETE r;

MATCH (s:Symptom)-[r:IN_CATEGORY]->(sc:SymptomCategory)
MERGE (s)-[:IN_SYMPTOM_CATEGORY]->(sc)
DELETE r;

MATCH (res:Resource)-[r:IN_CATEGORY]->(rc:ResourceCategory)
MERGE (res)-[:IN_RESOURCE_CATEGORY]->(rc)
DELETE r;

MATCH (ca:CopingAction)-[r:IN_CATEGORY]->(cc:CopingCategory)
MERGE (ca)-[:IN_COPING_CATEGORY]->(cc)
DELETE r;

MATCH (d:Disorder)-[r:DIFFERENTIAL_DUE_TO]->(mc:MedicalCondition)
MERGE (d)-[nr:RULE_OUT_SCREEN]->(mc)
SET nr.intent = coalesce(r.intent, 'differential_screening')
DELETE r;

MATCH (p:PsychProcess)-[r:UNDERLIES]->(s:Symptom)
MERGE (p)-[:PSYCH_BASIS_FOR]->(s)
DELETE r;


// =============================================================================
// END OF BOOTSTRAP v3.3
// =============================================================================
