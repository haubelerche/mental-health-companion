// =============================================================================
// CBT WORKBOOK ENRICHMENT PATCH
// Source: docs/wellbeing-team-cbt-workshop-booklet-2016.pdf
// =============================================================================

// ---------- 1) CognitiveDistortion definitions + new distortions ----------
MERGE (d1:CognitiveDistortion {slug: 'catastrophizing'})
SET d1.name_vi = 'Thảm họa hoá', d1.name_en = 'Catastrophizing',
    d1.definition_vi = 'Phóng đại mức độ nguy hiểm và giả định kết cục tệ nhất.',
    d1.definition_en = 'Magnifying danger and assuming the worst possible outcome.';

MERGE (d2:CognitiveDistortion {slug: 'black_and_white'})
SET d2.name_vi = 'Suy nghĩ trắng đen', d2.name_en = 'Black-and-white thinking',
    d2.definition_vi = 'Nhìn sự việc theo hai cực tuyệt đối, thiếu các mức trung gian.',
    d2.definition_en = 'Viewing situations in absolute extremes with no middle ground.';

MERGE (d3:CognitiveDistortion {slug: 'mind_reading'})
SET d3.name_vi = 'Đọc suy nghĩ người khác', d3.name_en = 'Mind reading',
    d3.definition_vi = 'Tự suy đoán người khác nghĩ tiêu cực về mình mà không có bằng chứng.',
    d3.definition_en = 'Assuming others are judging you negatively without evidence.';

MERGE (d4:CognitiveDistortion {slug: 'overgeneralization'})
SET d4.name_vi = 'Khái quát hoá quá mức', d4.name_en = 'Overgeneralization',
    d4.definition_vi = 'Từ một sự kiện đơn lẻ rút ra kết luận bao trùm cho mọi tình huống.',
    d4.definition_en = 'Drawing broad negative conclusions from a single event.';

MERGE (d5:CognitiveDistortion {slug: 'personalization'})
SET d5.name_vi = 'Đổ lỗi bản thân', d5.name_en = 'Personalization',
    d5.definition_vi = 'Quy trách nhiệm quá mức cho bản thân với các sự kiện ngoài tầm kiểm soát.',
    d5.definition_en = 'Taking excessive personal blame for events outside your control.';

MERGE (d6:CognitiveDistortion {slug: 'should_statements'})
SET d6.name_vi = 'Suy nghĩ phải/nên cứng nhắc', d6.name_en = 'Should statements',
    d6.definition_vi = 'Đặt các quy tắc "phải/nên" cứng nhắc khiến tăng tự chỉ trích và tội lỗi.',
    d6.definition_en = 'Rigid should/must rules that fuel guilt and self-criticism.';

MERGE (d7:CognitiveDistortion {slug: 'emotional_reasoning'})
SET d7.name_vi = 'Suy luận cảm tính', d7.name_en = 'Emotional reasoning',
    d7.definition_vi = 'Tin rằng cảm xúc tiêu cực phản ánh sự thật khách quan.',
    d7.definition_en = 'Believing feelings are objective facts.';

MERGE (d8:CognitiveDistortion {slug: 'filtering'})
SET d8.name_vi = 'Chỉ thấy mặt tiêu cực', d8.name_en = 'Mental filtering',
    d8.definition_vi = 'Chỉ tập trung vào chi tiết tiêu cực và bỏ qua bằng chứng tích cực.',
    d8.definition_en = 'Focusing only on negative details while ignoring positives.';

MERGE (d9:CognitiveDistortion {slug: 'labeling'})
SET d9.name_vi = 'Dán nhãn bản thân', d9.name_en = 'Labeling',
    d9.definition_vi = 'Dùng nhãn tiêu cực, bao quát để mô tả bản thân hoặc người khác.',
    d9.definition_en = 'Using global negative labels for yourself or others.';

MERGE (d10:CognitiveDistortion {slug: 'fortune_telling'})
SET d10.name_vi = 'Tiên tri tiêu cực', d10.name_en = 'Fortune telling',
    d10.definition_vi = 'Dự đoán tương lai theo hướng tiêu cực như thể chắc chắn sẽ xảy ra.',
    d10.definition_en = 'Predicting negative future outcomes as if they were certain.';

MERGE (d11:CognitiveDistortion {slug: 'jumping_to_conclusions'})
SET d11.name_vi = 'Nhảy đến kết luận', d11.name_en = 'Jumping to conclusions',
    d11.definition_vi = 'Kết luận vội vàng khi dữ kiện chưa đầy đủ hoặc mơ hồ.',
    d11.definition_en = 'Making quick negative conclusions with insufficient evidence.';

MERGE (d12:CognitiveDistortion {slug: 'magnification'})
SET d12.name_vi = 'Phóng đại / thu nhỏ', d12.name_en = 'Magnification and minimization',
    d12.definition_vi = 'Phóng đại rủi ro/lỗi lầm và xem nhẹ điểm mạnh hoặc thành quả.',
    d12.definition_en = 'Exaggerating threats/flaws while minimizing strengths or gains.';

// ---------- 2) New symptoms and categorization ----------
MERGE (s_sw:Symptom {slug: 'social_withdrawal'})
SET s_sw.name_vi = 'Thu mình xã hội', s_sw.name_en = 'Social withdrawal',
    s_sw.definition = 'Giảm giao tiếp và tránh tương tác xã hội do khí sắc thấp hoặc lo âu.';

MERGE (s_hv:Symptom {slug: 'hypervigilance'})
SET s_hv.name_vi = 'Tăng cảnh giác', s_hv.name_en = 'Hypervigilance',
    s_hv.definition = 'Liên tục dò quét tín hiệu nguy hiểm và triệu chứng cơ thể.';

MATCH (s:Symptom {slug: 'social_withdrawal'}), (c:SymptomCategory {slug: 'behavioral'})
MERGE (s)-[:IN_SYMPTOM_CATEGORY]->(c);
MATCH (s:Symptom {slug: 'hypervigilance'}), (c:SymptomCategory {slug: 'anxiety'})
MERGE (s)-[:IN_SYMPTOM_CATEGORY]->(c);

// ---------- 3) New CBT psych processes ----------
MERGE (p_ff:PsychProcess {slug: 'fight_flight_response'})
SET p_ff.name_vi = 'Phản ứng chiến đấu-bỏ chạy', p_ff.name_en = 'Fight-or-flight response',
    p_ff.definition_vi = 'Kích hoạt sinh lý khi cảm nhận đe doạ, làm tăng nhịp tim và căng cơ.';

MERGE (p_nat:PsychProcess {slug: 'negative_automatic_thought'})
SET p_nat.name_vi = 'Suy nghĩ tự động tiêu cực', p_nat.name_en = 'Negative automatic thought',
    p_nat.definition_vi = 'Ý nghĩ xuất hiện nhanh, thiên lệch tiêu cực, duy trì lo âu/trầm cảm.';

MERGE (p_avoid:PsychProcess {slug: 'avoidance_behaviour'})
SET p_avoid.name_vi = 'Hành vi né tránh', p_avoid.name_en = 'Avoidance behaviour',
    p_avoid.definition_vi = 'Tránh tình huống gây lo âu giúp giảm khó chịu ngắn hạn nhưng duy trì vấn đề.';

MERGE (p_rumi:PsychProcess {slug: 'rumination'})
SET p_rumi.name_vi = 'Suy ngẫm lặp lại tiêu cực', p_rumi.name_en = 'Rumination',
    p_rumi.definition_vi = 'Lặp đi lặp lại các suy nghĩ tiêu cực làm tăng và kéo dài khí sắc thấp.';

MATCH (p:PsychProcess {slug: 'negative_automatic_thought'}), (c:Construct {slug: 'cognition'})
MERGE (p)-[:UNDERLIES]->(c);
MATCH (p:PsychProcess {slug: 'fight_flight_response'}), (c:Construct {slug: 'emotion'})
MERGE (p)-[:UNDERLIES]->(c);
MATCH (p:PsychProcess {slug: 'avoidance_behaviour'}), (c:Construct {slug: 'activity'})
MERGE (p)-[:UNDERLIES]->(c);
MATCH (p:PsychProcess {slug: 'rumination'}), (c:Construct {slug: 'cognition'})
MERGE (p)-[:UNDERLIES]->(c);

// PsychProcess -> Symptom bridges
MATCH (p:PsychProcess {slug: 'fight_flight_response'}), (s:Symptom {slug: 'tension'})
MERGE (p)-[:PSYCH_BASIS_FOR]->(s);
MATCH (p:PsychProcess {slug: 'fight_flight_response'}), (s:Symptom {slug: 'psychomotor_disturbance'})
MERGE (p)-[:PSYCH_BASIS_FOR]->(s);
MATCH (p:PsychProcess {slug: 'negative_automatic_thought'}), (s:Symptom {slug: 'excessive_worry'})
MERGE (p)-[:PSYCH_BASIS_FOR]->(s);
MATCH (p:PsychProcess {slug: 'negative_automatic_thought'}), (s:Symptom {slug: 'low_mood'})
MERGE (p)-[:PSYCH_BASIS_FOR]->(s);
MATCH (p:PsychProcess {slug: 'avoidance_behaviour'}), (s:Symptom {slug: 'social_withdrawal'})
MERGE (p)-[:PSYCH_BASIS_FOR]->(s);
MATCH (p:PsychProcess {slug: 'rumination'}), (s:Symptom {slug: 'low_mood'})
MERGE (p)-[:PSYCH_BASIS_FOR]->(s);

// ---------- 4) New trigger nodes ----------
MERGE (t1:Trigger {slug: 'physical_symptom_awareness'})
SET t1.name_vi = 'Chú ý quá mức triệu chứng cơ thể', t1.name_en = 'Physical symptom awareness';

MERGE (t2:Trigger {slug: 'crowded_public_spaces'})
SET t2.name_vi = 'Không gian công cộng đông người', t2.name_en = 'Crowded public spaces';

MATCH (t:Trigger {slug: 'physical_symptom_awareness'}), (s:Symptom {slug: 'hypervigilance'})
MERGE (t)-[:MANIFESTS_AS]->(s);
MATCH (t:Trigger {slug: 'physical_symptom_awareness'}), (s:Symptom {slug: 'excessive_worry'})
MERGE (t)-[:MANIFESTS_AS]->(s);
MATCH (t:Trigger {slug: 'crowded_public_spaces'}), (s:Symptom {slug: 'tension'})
MERGE (t)-[:MANIFESTS_AS]->(s);
MATCH (t:Trigger {slug: 'crowded_public_spaces'}), (s:Symptom {slug: 'social_withdrawal'})
MERGE (t)-[:MANIFESTS_AS]->(s);

MATCH (t:Trigger {slug: 'physical_symptom_awareness'}), (d:CognitiveDistortion {slug: 'catastrophizing'})
MERGE (t)-[:COMMONLY_TRIGGERS {strength: 0.82}]->(d);
MATCH (t:Trigger {slug: 'crowded_public_spaces'}), (d:CognitiveDistortion {slug: 'jumping_to_conclusions'})
MERGE (t)-[:COMMONLY_TRIGGERS {strength: 0.68}]->(d);

// ---------- 5) New coping actions ----------
MERGE (ca1:CopingAction {action_id: 'behavioural_activation'})
SET ca1.name_vi = 'Kích hoạt hành vi', ca1.name_en = 'Behavioural Activation', ca1.is_adaptive = true;
MERGE (ca2:CopingAction {action_id: 'graded_exposure'})
SET ca2.name_vi = 'Phơi nhiễm phân bậc', ca2.name_en = 'Graded Exposure', ca2.is_adaptive = true;
MERGE (ca3:CopingAction {action_id: 'cognitive_restructuring'})
SET ca3.name_vi = 'Tái cấu trúc nhận thức', ca3.name_en = 'Cognitive Restructuring', ca3.is_adaptive = true;
MERGE (ca4:CopingAction {action_id: 'problem_solving'})
SET ca4.name_vi = 'Giải quyết vấn đề', ca4.name_en = 'Problem Solving', ca4.is_adaptive = true;
MERGE (ca5:CopingAction {action_id: 'worry_containment'})
SET ca5.name_vi = 'Khoanh vùng lo âu', ca5.name_en = 'Containing Worry', ca5.is_adaptive = true;
MERGE (ca6:CopingAction {action_id: 'smart_goal_setting'})
SET ca6.name_vi = 'Thiết lập mục tiêu SMART', ca6.name_en = 'SMART Goal Setting', ca6.is_adaptive = true;
MERGE (ca7:CopingAction {action_id: 'sleep_hygiene_practice'})
SET ca7.name_vi = 'Vệ sinh giấc ngủ', ca7.name_en = 'Sleep Hygiene', ca7.is_adaptive = true;
MERGE (ca8:CopingAction {action_id: 'physical_exercise'})
SET ca8.name_vi = 'Vận động thể chất', ca8.name_en = 'Physical Exercise', ca8.is_adaptive = true;
MERGE (ca9:CopingAction {action_id: 'abc_model_mapping'})
SET ca9.name_vi = 'Lập bản đồ ABC', ca9.name_en = 'ABC Model Mapping', ca9.is_adaptive = true;

// Categorization
MATCH (a:CopingAction {action_id: 'behavioural_activation'}), (c:CopingCategory {slug: 'behavioral'}) MERGE (a)-[:IN_COPING_CATEGORY]->(c);
MATCH (a:CopingAction {action_id: 'graded_exposure'}), (c:CopingCategory {slug: 'behavioral'}) MERGE (a)-[:IN_COPING_CATEGORY]->(c);
MATCH (a:CopingAction {action_id: 'cognitive_restructuring'}), (c:CopingCategory {slug: 'cognitive'}) MERGE (a)-[:IN_COPING_CATEGORY]->(c);
MATCH (a:CopingAction {action_id: 'problem_solving'}), (c:CopingCategory {slug: 'cognitive'}) MERGE (a)-[:IN_COPING_CATEGORY]->(c);
MATCH (a:CopingAction {action_id: 'worry_containment'}), (c:CopingCategory {slug: 'cognitive'}) MERGE (a)-[:IN_COPING_CATEGORY]->(c);
MATCH (a:CopingAction {action_id: 'smart_goal_setting'}), (c:CopingCategory {slug: 'cognitive'}) MERGE (a)-[:IN_COPING_CATEGORY]->(c);
MATCH (a:CopingAction {action_id: 'sleep_hygiene_practice'}), (c:CopingCategory {slug: 'behavioral'}) MERGE (a)-[:IN_COPING_CATEGORY]->(c);
MATCH (a:CopingAction {action_id: 'physical_exercise'}), (c:CopingCategory {slug: 'somatic'}) MERGE (a)-[:IN_COPING_CATEGORY]->(c);
MATCH (a:CopingAction {action_id: 'abc_model_mapping'}), (c:CopingCategory {slug: 'cognitive'}) MERGE (a)-[:IN_COPING_CATEGORY]->(c);

// Clinical targets
MATCH (a:CopingAction {action_id: 'behavioural_activation'}), (s:Symptom {slug: 'anhedonia'}) MERGE (a)-[:TARGETS_SYMPTOM {strength: 0.85}]->(s);
MATCH (a:CopingAction {action_id: 'behavioural_activation'}), (s:Symptom {slug: 'social_withdrawal'}) MERGE (a)-[:TARGETS_SYMPTOM {strength: 0.80}]->(s);
MATCH (a:CopingAction {action_id: 'graded_exposure'}), (s:Symptom {slug: 'excessive_worry'}) MERGE (a)-[:TARGETS_SYMPTOM {strength: 0.78}]->(s);
MATCH (a:CopingAction {action_id: 'graded_exposure'}), (s:Symptom {slug: 'hypervigilance'}) MERGE (a)-[:TARGETS_SYMPTOM {strength: 0.72}]->(s);
MATCH (a:CopingAction {action_id: 'cognitive_restructuring'}), (s:Symptom {slug: 'low_mood'}) MERGE (a)-[:TARGETS_SYMPTOM {strength: 0.75}]->(s);
MATCH (a:CopingAction {action_id: 'cognitive_restructuring'}), (s:Symptom {slug: 'guilt'}) MERGE (a)-[:TARGETS_SYMPTOM {strength: 0.72}]->(s);
MATCH (a:CopingAction {action_id: 'problem_solving'}), (s:Symptom {slug: 'excessive_worry'}) MERGE (a)-[:TARGETS_SYMPTOM {strength: 0.70}]->(s);
MATCH (a:CopingAction {action_id: 'worry_containment'}), (s:Symptom {slug: 'excessive_worry'}) MERGE (a)-[:TARGETS_SYMPTOM {strength: 0.82}]->(s);
MATCH (a:CopingAction {action_id: 'smart_goal_setting'}), (s:Symptom {slug: 'poor_concentration'}) MERGE (a)-[:TARGETS_SYMPTOM {strength: 0.58}]->(s);
MATCH (a:CopingAction {action_id: 'sleep_hygiene_practice'}), (s:Symptom {slug: 'insomnia'}) MERGE (a)-[:TARGETS_SYMPTOM {strength: 0.88}]->(s);
MATCH (a:CopingAction {action_id: 'physical_exercise'}), (s:Symptom {slug: 'fatigue'}) MERGE (a)-[:TARGETS_SYMPTOM {strength: 0.68}]->(s);
MATCH (a:CopingAction {action_id: 'abc_model_mapping'}), (s:Symptom {slug: 'excessive_worry'}) MERGE (a)-[:TARGETS_SYMPTOM {strength: 0.60}]->(s);

// Disorder support links
MATCH (a:CopingAction {action_id: 'behavioural_activation'}), (d:Disorder {slug: 'mdd'}) MERGE (a)-[:HELPS_WITH]->(d);
MATCH (a:CopingAction {action_id: 'behavioural_activation'}), (d:Disorder {slug: 'pdd'}) MERGE (a)-[:HELPS_WITH]->(d);
MATCH (a:CopingAction {action_id: 'graded_exposure'}), (d:Disorder {slug: 'panic_disorder'}) MERGE (a)-[:HELPS_WITH]->(d);
MATCH (a:CopingAction {action_id: 'graded_exposure'}), (d:Disorder {slug: 'social_anxiety_disorder'}) MERGE (a)-[:HELPS_WITH]->(d);
MATCH (a:CopingAction {action_id: 'graded_exposure'}), (d:Disorder {slug: 'agoraphobia'}) MERGE (a)-[:HELPS_WITH]->(d);
MATCH (a:CopingAction {action_id: 'cognitive_restructuring'}), (d:Disorder {slug: 'gad'}) MERGE (a)-[:HELPS_WITH]->(d);
MATCH (a:CopingAction {action_id: 'cognitive_restructuring'}), (d:Disorder {slug: 'mdd'}) MERGE (a)-[:HELPS_WITH]->(d);
MATCH (a:CopingAction {action_id: 'problem_solving'}), (d:Disorder {slug: 'gad'}) MERGE (a)-[:HELPS_WITH]->(d);
MATCH (a:CopingAction {action_id: 'worry_containment'}), (d:Disorder {slug: 'gad'}) MERGE (a)-[:HELPS_WITH]->(d);
MATCH (a:CopingAction {action_id: 'sleep_hygiene_practice'}), (d:Disorder {slug: 'insomnia_disorder'}) MERGE (a)-[:HELPS_WITH]->(d);
MATCH (a:CopingAction {action_id: 'physical_exercise'}), (d:Disorder {slug: 'mdd'}) MERGE (a)-[:HELPS_WITH]->(d);
MATCH (a:CopingAction {action_id: 'abc_model_mapping'}), (d:Disorder {slug: 'gad'}) MERGE (a)-[:HELPS_WITH]->(d);

// ---------- 6) Distortion -> Symptom gap fill ----------
MATCH (d:CognitiveDistortion {slug: 'jumping_to_conclusions'}), (s:Symptom {slug: 'excessive_worry'})
MERGE (d)-[:AMPLIFIES {strength: 0.77}]->(s);
MATCH (d:CognitiveDistortion {slug: 'jumping_to_conclusions'}), (s:Symptom {slug: 'hypervigilance'})
MERGE (d)-[:AMPLIFIES {strength: 0.66}]->(s);
MATCH (d:CognitiveDistortion {slug: 'magnification'}), (s:Symptom {slug: 'tension'})
MERGE (d)-[:AMPLIFIES {strength: 0.74}]->(s);
MATCH (d:CognitiveDistortion {slug: 'magnification'}), (s:Symptom {slug: 'excessive_worry'})
MERGE (d)-[:AMPLIFIES {strength: 0.79}]->(s);
