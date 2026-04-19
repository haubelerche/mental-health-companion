// Patch: Item → Symptom (:MEASURES) cho PHQ-9 / GAD-7 (trích §5.3 neo4j_bootstrap_v3.cypher).
// Chạy khi graph đã có Item + Symptom đúng slug nhưng thiếu cạnh MEASURES (pytest báo "hiện có 0").
// Neo4j Browser hoặc:
//   cypher-shell -u neo4j -p '<pass>' -d neo4j < backend/app/data/neo4j_patch_measures_phq_gad.cypher

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
