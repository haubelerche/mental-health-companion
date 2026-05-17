# Serene - Bao cao AI/worktree va truy vet thay doi

**Ngay cap nhat:** 17/05/2026  
**Nhanh:** `feat/greetings-screening-results`  
**HEAD hien tai:** `fe9e303 feat(evals+observability): expand eval datasets, wire observability, tune safety keywords`

## Context

Tai lieu nay tra loi cau hoi "AI da lam gi trong worktree/commit" bang cach tong hop commit gan nhat, cac commit lien quan, va cac thay doi chua commit dang co trong working tree. Muc tieu la giup team va nguoi cham phan biet ro: phan nao da nam trong Git history, phan nao moi nam trong worktree, phan nao la tai lieu nop bai, va phan nao can verify them truoc khi push.

## Problem Statement

Worktree hien tai khong phai trang thai sach: co nhieu file da sua, nhieu file moi chua track, va mot so file artifact/local database. Neu nop bai hoac tao PR ma khong co bao cao truy vet, nguoi review se kho xac dinh AI da thay doi luong chat, analyst pipeline, resource injection, dashboard UI, evaluation evidence hay tai lieu. Rui ro chinh la commit nham artifact local, bo sot migration, hoac trinh bay ket qua evaluation ma khong lien ket voi file bang chung.

## Technical Deep-Dive

### 1. Commit gan nhat da co trong Git history

| Commit | Noi dung | Tac dong |
|---|---|---|
| `fe9e303` | Mo rong eval datasets, wire observability, tune safety keywords | Tang golden cases len 88, adversarial len 50, cai thien RAGAS heuristic, them structured logging/Prometheus |
| `0dc44e5` | Langfuse traces cho `advisor_assisted` va streaming fast-path | Giam blind spot observability cho cac route khong qua full analyst path |
| `6a0a1f9` | Eval runners, analyst sanitizer, backend screening, expanded safety tests | Tang coverage safety/eval va backend-authoritative screening |
| `a9ae014` | P0/P1/P2 gap closure tu evaluation audit | Sua output guard, PII hashing, Neo4j sync va distress router tests |
| `830d1d8` | Frontend build job trong CI | Them gate TypeScript/lint/build truoc merge |

### 2. Thay doi dang nam trong worktree

Ket qua `git status --short` cho thay cac nhom thay doi sau:

| Nhom | File tieu bieu | AI da lam gi |
|---|---|---|
| Tai lieu nop bai | `README.md`, `report.md`, `JOURNAL.md`, `WORKLOG.md`, `README_SLIDE_DECK.md`, `docs/ARCHITECTURE.md`, `docs/EVALUATION_EVIDENCE.md` | Bo sung mo ta du an, huong dan chay, architecture, evidence, journal, worklog, pitch deck outline va bao cao tong hop |
| Analyst pipeline | `backend/app/services/analyst_agent.py`, `backend/app/services/analyst_context_loader.py`, `backend/alembic/versions/0040_analyst_evidence_refs.py`, `backend/app/services/db/models.py` | Them context loader doc lap, nap mood/screening/session summary, evidence refs, banding cho PHQ/GAD/DASS/MDQ/PCL, migration evidence refs |
| Chat/resource flow | `backend/app/api/v1/routers/chat.py`, `backend/app/services/langgraph_chat.py`, `backend/app/services/resource_candidates.py`, `backend/seed_resources.py` | Dua resource candidate vao chat context, cai thien tracing/output policy, them seed script cho Resource table |
| Persona/naturalness | `backend/app/personas/greetings.py`, `backend/app/services/friend_agent.py`, `backend/app/services/analyst_writer.py` | Dieu chinh greeting va friend/analyst copy de tu nhien hon, giam leak noi bo |
| Dashboard frontend | `DataQualityBadge.tsx`, `LifestyleRhythmPanel.tsx`, `MoodByPeriodChart.tsx`, `Home.tsx`, `Reflect.tsx` | Lam ro chat luong du lieu, redesign tab sinh hoat, chart theo buoi, doi nhan UI tieng Viet |
| Resource UI | `frontend/src/components/pages/resource/ResourceGrid.tsx` | Dieu chinh hien thi resource va YouTube/resource candidates |
| Evaluation reports | `evals/reports/latest_eval_report.md`, `evals/reports/2026-05-16_analyst_pipeline_validation.md`, `evals/reports/latest_ai_security_report.md`, `evals/security/`, `evals/run_ai_security.py` | Bo sung bang chung validation analyst pipeline va AI security offline |

### 3. File moi chua track can xem xet truoc khi commit

| File / thu muc | Nen commit? | Ly do |
|---|---|---|
| `HUONGDANNOPBAI_full.md` | Nen commit neu muon luu yeu cau nop bai | Day la nguon yeu cau nop bai, dang co encoding hien thi khong dep trong PowerShell nhung van huu ich |
| `README_SLIDE_DECK.md` | Nen commit | La noi dung pitch deck 5-10 trang |
| `docs/ARCHITECTURE.md` | Nen commit | Bat buoc theo yeu cau architecture |
| `docs/EVALUATION_EVIDENCE.md` | Nen commit | Bat buoc theo yeu cau evaluation evidence |
| `docs/AI_WORKTREE_CHANGE_REPORT.md` | Nen commit | Phu luc truy vet AI/worktree |
| `backend/app/services/analyst_context_loader.py` | Nen commit neu test pass | La dependency cua `analyst_agent.py` da sua |
| `backend/alembic/versions/0040_analyst_evidence_refs.py` | Nen commit neu migration chain hop le | Dong bo model/schema cho `evidence_refs` |
| `backend/app/services/resource_candidates.py` | Nen commit neu chat route dang import | Neu khong commit se gay import error |
| `backend/seed_resources.py` | Tuy chon | Script van hanh/seed resource, nen commit neu can demo Resource Hub |
| `evals/security/` va `evals/run_ai_security.py` | Nen commit | Bang chung AI security |
| `backend/_alembic_test.db`, `serene_local.db` | Khong nen commit | Local database artifact, co rui ro chua du lieu/tang kich thuoc repo |

### 4. Thay doi ky thuat quan trong trong worktree

| Hang muc | Mo ta | Rui ro neu bo sot |
|---|---|---|
| Analyst evidence refs | `AnalystContextLoader` gom mood, screening, session summaries va tao `evidence_refs` de AnalystBundle co provenance | Neu chi commit `analyst_agent.py` ma bo loader/migration thi backend loi import hoac schema |
| Screening context | Them banding cho PHQ-9, GAD-7, DASS-21, MDQ, PCL-5 vao `safe_dashboard_candidates` | Can dam bao output khong user-facing nhu chan doan |
| Resource candidates | Map user message/distress sang category va lay Resource active tu DB | Can DB co seed data; neu khong co thi fallback rong/phai xu ly graceful |
| Langfuse/observability | Commit gan nhat da wire tracing/logging/Prometheus; worktree tiep tuc dieu chinh chat paths | Can chay tests de dam bao tracer khong lam thay doi response shape |
| Dashboard UI | Redesign LifestyleRhythmPanel va MoodByPeriodChart | Can chay frontend build/lint de bat TypeScript regression |

### 5. Bang chung evaluation hien co

| Bang chung | Vi tri | Ghi chu |
|---|---|---|
| Bao cao tong hop evaluation | `docs/EVALUATION_EVIDENCE.md` | Tong hop 901 pytest, golden, guardrails, judge, RAGAS |
| Bao cao eval moi nhat | `evals/reports/latest_eval_report.md` | Report generated tu eval suite |
| Bao cao AI security | `evals/reports/latest_ai_security_report.md` | Offline security report, co the co gap/xfail can doc ky |
| Analyst validation | `evals/reports/2026-05-16_analyst_pipeline_validation.md` | Bang chung rieng cho analyst pipeline |
| Changelog | `CHANGELOG.md` | Lich su thay doi theo phien va commit |

## Strategic Recommendations

### 1. Commit hygiene

Truoc khi commit, nen tach it nhat 3 nhom commit:

| Commit de xuat | Pham vi | Ly do |
|---|---|---|
| `docs(submission): add AI20K submission reports` | `report.md`, `README_SLIDE_DECK.md`, `docs/ARCHITECTURE.md`, `docs/EVALUATION_EVIDENCE.md`, journal/worklog | Giu tai lieu nop bai rieng voi code runtime |
| `feat(analyst): add evidence-backed context loader` | Analyst loader, model, migration, analyst agent tests/evidence | Day la thay doi backend co schema |
| `feat(resources+dashboard): improve resource recommendations and reflect UI` | Resource candidates, seed script, dashboard/resource frontend | De review UI/resource tach khoi analyst pipeline |

Khong nen commit local database artifact: `backend/_alembic_test.db` va `serene_local.db`.

### 2. Verification toi thieu truoc khi push

| Lenh | Muc dich |
|---|---|
| `bash scripts/setup_hooks.sh` | Dam bao AI prompt logging hook da cai truoc push/PR |
| `pytest backend/tests -q` | Xac minh backend va agent/safety regression |
| `npm --prefix frontend run lint` | Bat loi lint TypeScript/React |
| `npm --prefix frontend run build` | Xac minh frontend build cho dashboard/resource changes |
| `python evals/run_golden.py --mode offline` | Xac minh golden routing/eval khong regression |
| `python evals/run_guardrails.py --mode offline` | Xac minh guardrail offline |

### 3. Cach giai thich "AI lam gi" khi bao ve

Nen trinh bay AI nhu cong cu tang toc engineering, khong phai tac gia tu tri. Cu the:

| Vai tro cua AI | Vi du thuc te trong repo | Kiem soat cua team |
|---|---|---|
| Sinh va refactor code | Analyst context loader, eval runner, dashboard UI polish | Review diff, chay tests, tach commit |
| Mo rong test/eval | Golden/adversarial/RAGAS/AI security datasets | Dinh nghia invariants, doc report, chap nhan/loai bo case |
| Viet tai lieu | README, architecture, evaluation evidence, journal/worklog | Doi chieu voi yeu cau nop bai va trang thai code |
| Debug/observability | Langfuse traces, structured logging, Prometheus metrics | Xac minh bang logs, metrics va regression tests |

### 4. Ket luan

AI da dong gop dang ke vao ba lop: runtime safety/analyst/resource, evaluation-security infrastructure, va tai lieu nop bai. Trang thai hien tai du manh de nop ve mat minh chung ky thuat, nhung truoc khi push can loai local DB artifact, chay hook logging, cap nhat link deploy/video/slide, va chay lai verification toi thieu cho backend/frontend.
