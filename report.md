# Serene - Bao cao tong hop nop bai AI20K Build Phase

**Ngay cap nhat:** 17/05/2026  
**Nhanh lam viec:** `feat/greetings-screening-results`  
**Trang thai:** San sang nop ve mat ma nguon, tai lieu, architecture, worklog va evaluation evidence; cac lien ket Live URL, Video Demo va Pitch Deck can duoc cap nhat bang link cong khai truoc khi dien form.

## Context

Tai lieu nay tong hop toan bo noi dung can nop theo `HUONGDANNOPBAI_full.md`: source code, README, kien truc, AI logs, weekly journal, worklog, evaluation evidence, demo assets va checklist truoc khi nop. Bao cao duoc viet dua tren trang thai repository hien tai, commit gan nhat, cac file tai lieu trong `docs/`, va cac thay doi dang nam trong worktree.

| Hang muc nop bai | Trang thai trong repository | Duong dan / bang chung |
|---|---|---|
| Source code day du | Da co frontend, backend, database migrations, AI/agent logic, API, eval runners va cau hinh deploy | `frontend/`, `backend/`, `evals/`, `scripts/`, `docker-compose.yml` |
| README goc | Da cap nhat mo ta, muc tieu, tinh nang, cong nghe, cai dat, chay va huong dan su dung | `README.md` |
| Architecture | Da co tai lieu kien truc va luong du lieu chinh | `docs/ARCHITECTURE.md` |
| AI logs / hook | Da co cau hinh hook theo yeu cau, khong can commit `.ai-log/*.jsonl` | `.codex/hooks.json`, `.claude/settings.json`, `.cursor/hooks.json`, `scripts/setup_hooks.sh` |
| Weekly journal | Da ghi qua trinh theo tuan, ket qua, kho khan, AI tool da dung va bai hoc | `JOURNAL.md` |
| Worklog | Da ghi ADR, phan cong, brainstorming va cac quyet dinh ky thuat | `WORKLOG.md` |
| Evaluation evidence | Da co bao cao test, eval, guardrail, RAGAS heuristic va AI security | `docs/EVALUATION_EVIDENCE.md`, `evals/reports/` |
| Pitch deck outline | Da co noi dung slide deck de tao slide 5-10 trang | `README_SLIDE_DECK.md` |
| AI/worktree report | Da bo sung phu luc truy vet AI lam gi trong commit/worktree | `docs/AI_WORKTREE_CHANGE_REPORT.md` |

## Problem Statement

Serene giai quyet khoang trong ho tro tam ly dau tien cho sinh vien va nguoi tre Viet Nam: nguoi dung co nhu cau noi ra ap luc, lo au, met moi, co don hoac dau hieu nguy co, nhung thuong tri hoan tim chuyen gia do stigma, chi phi, thoi gian, thieu kenh ho tro rieng tu va thieu san pham hieu ngu canh tieng Viet. Giai phap khong duoc dinh vi la bac si AI, khong chan doan va khong thay the chuyen gia; Serene la lop emotional first-aid co guardrail, co kha nang lang nghe, sang loc dau hieu ban dau, goi y hanh dong nho va chuyen den hotline/referral khi vuot nguong an toan.

Rui ro cot loi cua bai toan khong nam o viec tao them mot chatbot, ma nam o viec quan tri tam giac ky thuat sau:

| Yeu to | Yeu cau | Cach Serene xu ly |
|---|---|---|
| Scalability | Chi phi LLM va side effect phai duoc kiem soat khi so luong user tang | Fast path cho greeting/small talk, async outbox cho TTS/memory/Neo4j, eval heuristic co the chay CI |
| Reliability | Safety khong duoc phu thuoc vao LLM khong deterministic | SafetyGate rule-based truoc moi luot, SafetyFinalizer tach khoi FriendNode, test adversarial |
| Latency | Chat cam xuc can phan hoi nhanh, nhung khong duoc bo qua safety | Sync cho SafetyGate/Friend response, async cho scoring va side effects, tracing latency |

## Technical Deep-Dive

### 1. Kien truc san pham va runtime

Serene dung kien truc lightweight multi-agent tren FastAPI va LangGraph. Luong chat chinh la:

```text
User -> React Frontend -> FastAPI Router -> SafetyGate
     -> Normal: DistressRouter -> AnalystNode neu can -> FriendNode -> Response
     -> SOS: SafetyFinalizer -> CrisisInterventionPlanner -> Hotline/Referral -> Response
     -> Async: Memory, TTS, Analyst batch, Neo4j sync, Dashboard insight
```

| Thanh phan | Vai tro | File / module tieu bieu |
|---|---|---|
| Frontend | Chat, dashboard, reflect, resource hub, screening, rewards, admin | `frontend/src/components/pages/`, `frontend/src/components/dashboard/` |
| Backend API | Auth, chat, safety, dashboard, resources, notifications, admin | `backend/app/api/v1/routers/` |
| SafetyGate | Quy dinh route an toan truoc LLM | `backend/app/safety/`, `backend/app/services/langgraph_chat.py` |
| Analyst | Phan tich noi bo, evidence refs, context loader, khong user-facing | `backend/app/services/analyst_agent.py`, `backend/app/services/analyst_context_loader.py` |
| Friend | Phan hoi nguoi dung theo tone Serene, ap dung output policy | `backend/app/services/friend_agent.py` |
| Database | PostgreSQL/Alembic la source of truth; Neo4j chi la derived graph | `backend/app/services/db/models.py`, `backend/alembic/versions/` |
| Evaluation | Golden, guardrail, RAGAS, judge, AI security | `evals/`, `backend/tests/` |

### 2. Tinh nang chinh da co

| Nhom tinh nang | Noi dung |
|---|---|
| Chat AI tieng Viet | Hoi thoai tu nhien voi persona Serene, co fast path cho greeting/small talk va advisor-assisted path khi can |
| Safety/SOS | Phat hien nguy co, block persona khong phu hop, sinh crisis payload, hotline/referral, crisis/audit log |
| Screening | PHQ-9/GAD-7 va cac truong mo rong trong `ClinicalProfile`; frontend co sync voi backend |
| Dashboard | Mood trend, mood by period, lifestyle rhythm, data quality badge, insight cards |
| Memory | Memory card, mem0 repository, session summary, context recall |
| Resource Hub | Tai nguyen wellness, YouTube/resource candidate injection, seed script |
| Voice/TTS | Voice policy, TTS worker, dedup va tach `visible_text` voi `voice_script` |
| Admin/Observability | Admin routes, audit log, Langfuse tracing, structured logging, Prometheus metrics |

### 3. Evidence va ket qua danh gia

| Bo danh gia | Quy mo | Ket qua hien tai |
|---|---:|---|
| Backend pytest | 901 tests | 901 passed, 0 failed theo `docs/EVALUATION_EVIDENCE.md` |
| Golden conversation eval | 88 cases | 88 pass, 0 fail |
| Adversarial guardrails | 50 cases | 44 pass, 6 skip can live backend, 0 fail |
| LLM-as-Judge heuristic | 50 cases | 50 pass |
| RAGAS heuristic | 59 questions | 59 review, 0 hard fail |
| AI security offline | 130 adversarial cases | Bao cao sinh tai `evals/reports/latest_ai_security_report.md` |

Ket qua tren cho thay repository da co evaluation evidence dung yeu cau nop bai: bao cao danh gia, bo cau hoi/case kiem thu, metrics, feedback ky thuat va runner co the lap lai. Tuy nhien, cac so lieu heuristic khong nen duoc trinh bay nhu ket qua clinical validation; chung la bang chung regression engineering va guardrail coverage.

### 4. AI logs va qua trinh phat trien

Repository da co co che logging prompt tu dong qua hooks cho Claude Code, Cursor, Codex, Gemini CLI va GitHub Copilot. Theo guideline du an, agent khong can va khong nen commit `.ai-log/*.jsonl`; cac file nay duoc gitignore va submit tu dong khi `git push` neu hook da cai.

| Thanh phan | Muc dich |
|---|---|
| `scripts/setup_hooks.sh` | Cai pre-push hook mot lan truoc khi PR/push |
| `scripts/log_hook.py` | Ghi prompt/session vao `.ai-log/session.jsonl` |
| `scripts/submit_log.py` | Gui log tu dong khi push |
| `.codex/hooks.json` | Cau hinh OpenAI Codex hook |
| `.claude/settings.json`, `.cursor/hooks.json` | Cau hinh cac AI tool khac |

### 5. Noi dung form can chuan bi

| Truong tren form | Trang thai | Hanh dong truoc khi nop |
|---|---|---|
| Live URL | Chua dien trong README | Cap nhat URL deploy cong khai theo dinh dang `https://a20-app-039...` hoac domain hop le |
| Video demo 3-5 phut | Chua dien trong README | Quay demo: problem, main features, AI agent flow, safety path |
| Pitch deck 5-10 trang | Co outline noi dung | Tao slide tu `README_SLIDE_DECK.md`, mo quyen xem cong khai |
| GitHub repo | Da co source va tai lieu | Push ban moi nhat sau khi chay hook |
| Link tai lieu | Da co | Dan link README, architecture, evaluation evidence, journal, worklog |

## Strategic Recommendations

### Uu tien truoc khi nop form

| Uu tien | Viec can lam | Ly do |
|---:|---|---|
| 1 | Cap nhat `Live URL`, `Video Demo`, `Pitch Deck` o dau `README.md` | Day la diem dau tien nguoi cham va form nop bai can |
| 2 | Chay `bash scripts/setup_hooks.sh` truoc khi push/PR | Day la yeu cau bat buoc trong `AGENTS.md` va quy dinh AI log cua du an |
| 3 | Chay lai test/eval toi thieu neu co thoi gian | Xac minh worktree chua commit khong pha regression |
| 4 | Khong commit `.ai-log/*.jsonl`, DB local, artifact tam | Giu repository sach va dung chinh sach du lieu |
| 5 | Ghi ro cac case `SKIP` can live backend trong demo/evidence | Tranh bien ket qua offline thanh ket qua runtime chua verify |

### Checklist nop bai

| Muc | Trang thai | Ghi chu |
|---|---|---|
| README co mo ta, muc tieu, tinh nang, cong nghe, cai dat, chay, su dung | Da co | Can thay placeholder link |
| Architecture co User, Frontend, Backend/API, Database, AI/LLM, External Services | Da co | `docs/ARCHITECTURE.md` |
| Journal theo tuan | Da co | `JOURNAL.md` |
| Worklog co phan cong, cong viec, thoi gian, trang thai | Da co | `WORKLOG.md` |
| Evaluation evidence co test, datasets, metrics, reports | Da co | `docs/EVALUATION_EVIDENCE.md`, `evals/reports/` |
| AI logs/hook config | Da co | Can chay setup hook truoc push |
| Video demo | Can tao | 3-5 phut |
| Pitch deck | Co noi dung nguon, can xuat slide | 5-10 trang |
| Public access cho link Drive/YouTube/Slide | Can kiem tra | Bat buoc truoc khi submit |

## Ket luan

Serene hien co day du cac lop can thiet cho mot bai nop AI20K Build Phase nghiem tuc: san pham frontend, backend agentic runtime, database migrations, safety-first architecture, evaluation suite, AI security evidence, worklog/journal va tai lieu architecture. Diem can hoan thien cuoi cung khong phai logic code chinh, ma la hygiene nop bai: cap nhat link cong khai, chay hook logging, push ban moi nhat, va ghi ro ranh gioi giua ket qua offline heuristic voi ket qua live demo.
