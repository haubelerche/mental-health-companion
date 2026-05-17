# **Serene.AI** — Trợ lý AI hỗ trợ sàng lọc và Chăm sóc sức khỏe tinh thần cho người Việt.

> **Live URL:** [Serene.AI](https://a20-app-039.vercel.app/) <br>
> **Video Demo:** *[Serene.AI video demo](https://www.youtube.com/watch?v=6u_o8iUVvik)* <br>
> **Pitch Deck:** [Google Slides link](https://docs.google.com/presentation/d/1AyPRQK7WMZfvQPd2KT_a3YjDnyy2imBvwopUUpfLaIo/edit?usp=sharing) <br>
> **Architecture:** [`docs/architecture/ARCHITECTURE.md`](docs/architecture/ARCHITECTURE.md) <br>
> **Evaluation Evidence:** [`docs/submission/EVALUATION_EVIDENCE.md`](docs/submission/EVALUATION_EVIDENCE.md) <br>
> **Submission Report:** [`report.md`](report.md) <br>
> **Full Submission Report:** [`docs/submission/SUBMISSION_REPORT.md`](docs/submission/SUBMISSION_REPORT.md) <br>
> **Submission Package Index:** [`docs/submission/SUBMISSION_PACKAGE.md`](docs/submission/SUBMISSION_PACKAGE.md) <br>
> **Form Preparation:** [`docs/submission/FORM_SUBMISSION_PREP.md`](docs/submission/FORM_SUBMISSION_PREP.md) <br>
> **Final Checklist:** [`docs/submission/FINAL_SUBMISSION_CHECKLIST.md`](docs/submission/FINAL_SUBMISSION_CHECKLIST.md) <br>
> **AI Worktree Report:** [`docs/submission/AI_WORKTREE_CHANGE_REPORT.md`](docs/submission/AI_WORKTREE_CHANGE_REPORT.md) <br>
> **AI Logs and Hooks:** [`docs/submission/AI_LOGS_AND_HOOKS.md`](docs/submission/AI_LOGS_AND_HOOKS.md)

---

## Mô tả dự án

Trong kỷ nguyên số, nhiều người trẻ Việt Nam đang sống giữa một nghịch lý rất thật: "Cô đơn trong chốn đông người" — vây quanh bởi kết nối nhưng khó tìm được nơi để giãi bày, được lắng nghe và đồng cảm thực sự. Serene.AI ra đời hưởng ứng công nghệ AI Emotional Intelligence: nơi công nghệ và cảm xúc giao thoa để tạo nên một không gian đồng hành nhân văn, gần gũi và thực sự hữu ích với từng cá nhân.

Serene.AI **không** hướng đến việc thay thế chuyên gia hay đưa ra chẩn đoán y khoa. Sản phẩm được định vị như một **mental-health companion**: lắng nghe, sàng lọc ban đầu, hỗ trợ phản tư, đề xuất coping/resource phù hợp và kích hoạt luồng an toàn khi cần. Thông qua hội thoại tự nhiên bằng tiếng Việt cùng dữ liệu sinh hoạt hằng ngày (cảm xúc, giấc ngủ, dinh dưỡng, sàng lọc tâm lý), Serene.AI giúp người dùng chuyển hóa những trải nghiệm rời rạc thành insight trực quan, cá nhân hóa và có bằng chứng.

---

## Bài toán và Giải pháp

**Bài toán:** 45% sinh viên Việt Nam có dấu hiệu lo âu/trầm cảm đáng kể (WHO, 2023), nhưng tỷ lệ tiếp cận hỗ trợ tâm lý chuyên nghiệp dưới 10%. Rào cản chính: stigma xã hội, chi phí cao, thiếu cơ sở vật chất, ngại gặp trực tiếp.

**Giải pháp:** Một AI companion có thể:
1. Nói chuyện tự nhiên bằng tiếng Việt Gen Z — không nghe như chatbot hoặc bác sĩ
2. Phát hiện sớm dấu hiệu khủng hoảng qua phân tích ngầm (PHQ-9 / GAD-7 / DASS-21 / MDQ / PCL-5)
3. Kích hoạt can thiệp khẩn cấp khi cần, cung cấp hotline VN uy tín
4. Không bao giờ chẩn đoán — luôn giữ ranh giới lâm sàng

---

## Tính năng chính

| Tính năng | Mô tả |
|---|---|
| **Chat AI tiếng Việt** | Hội thoại tự nhiên với Serene — empathetic, đồng trang lứa, không clinical |
| **Safety Gate** | Rule-based gate chạy trước mọi LLM call — phát hiện khủng hoảng trong < 100ms |
| **SOS Intervention** | Kích hoạt khi phát hiện nguy cơ cao: de-escalation script, hotline VN, CrisisLog |
| **Screening cơ bản** | PHQ-9 và GAD-7 — theo dõi dấu hiệu lo âu và trầm cảm |
| **Kiểm tra sâu** | DASS-21 (stress/lo âu/trầm cảm), MDQ (dao động khí sắc), PCL-5 (sang chấn) — không chẩn đoán |
| **Analyst Pipeline** | Analyst Agent + advisor chuyên biệt tạo insight có bằng chứng từ nhiều nguồn dữ liệu |
| **Memory Cards** | Lưu ký ức hội thoại dưới dạng thẻ ngắn — Serene nhớ tên, sự kiện, cảm xúc quan trọng |
| **Personas** | 3 style mode: Dũng (`dung_luong`), Đạt (`dat_le`), Hậu (`hau_luong`) — cùng 1 identity, khác tone |
| **Voice TTS** | Text-to-speech với ElevenLabs — SOS có `visible_text` và `voice_script` riêng, không block chat |
| **Resource Hub** | Thư viện tài nguyên sức khỏe tâm thần: bài tập, bài viết, hotline, coping recommendation |
| **Dashboard** | Insight cards có evidence/confidence/action, biểu đồ tâm trạng, lifestyle rhythm, streak |
| **Push Notifications** | Nhắc nhở chủ động, mood check-in, wellness tips qua SSE |

---

## Kiến trúc Agent Runtime

Serene sử dụng kiến trúc **backend-centered, safety-first** với ba vai trò agent chính:

```
User
  → Frontend (display layer)
  → Backend API
  → Input Normalization + PII Masking
  → Safety Gate  ←── chạy trước mọi LLM call
       ├── Crisis/SOS → Safety Agent → controlled crisis payload
       └── Non-crisis → Risk Router
               ├── Simple support → Friend Agent
               └── Needs insight  → Analyst Agent → Friend Agent
  → Output Validator
  → Response
  → Async workers: memory extraction, TTS, dashboard rollup, notification
```

| Vai trò | User-facing | Trách nhiệm |
|---|:---:|---|
| **Friend Agent** | ✓ | Trò chuyện, phản hồi cảm xúc, áp dụng persona/style, tạo câu trả lời cuối cùng cho normal flow |
| **Analyst Agent** | ✗ | Phân tích dữ liệu hội thoại, mood, screening, meal, memory; tạo structured insight bundle |
| **Safety Agent** | ✓ qua payload | Xử lý high-risk/SOS, de-escalation, voice grounding, hotline/referral, audit và crisis log |

Advisor chuyên biệt hỗ trợ Analyst (không user-facing, không viết final response): Screening Advisor, Deep Screening Advisor (DASS-21/MDQ/PCL-5), Mood Advisor, Lifestyle Advisor, Memory Advisor, Resource Advisor, Safety Context Advisor.

---

## Persona Registry

| Persona | Canonical ID | Trạng thái | Mô tả |
|---|---|---|---|
| **Dũng** | `dung_luong` | Core — khả dụng mặc định | Vui vẻ, bắt mood tốt, biết lắng nghe; có thể dùng meme nhẹ ở low-risk turn |
| **Đạt** | `dat_le` | Core — khả dụng mặc định | Trầm tính, có chiều sâu; giúp người dùng nhìn vấn đề rõ ràng qua phản tư |
| **Hậu** | `hau_luong` | Unlockable — 500 Tim | Hướng nội, nhẹ nhàng; ưu tiên voice-message vibe, phù hợp khi overthinking |

> Safety override thắng mọi persona. High-risk/SOS luôn ép về style an toàn.

---

## Công nghệ sử dụng

### Backend

| Layer | Công nghệ |
|---|---|
| Language / Runtime | Python 3.11 |
| Web Framework | FastAPI (async) |
| AI Orchestration | LangGraph (StateGraph, conditional edges, checkpointing) |
| LLM | OpenAI GPT-4o / GPT-4o-mini (OpenAI-compatible API) |
| Database chính | PostgreSQL 15 + pgvector (vector similarity search) |
| Cache / Queue | Redis |
| Derived Graph | Neo4j AuraDB (pattern graph, không lưu PII) |
| TTS | ElevenLabs API |
| Auth | JWT (PyJWT) + OAuth2 (Google) |
| Migrations | Alembic |
| Observability | Langfuse traces + Structured JSON logging (python-json-logger) + Prometheus metrics |
| Testing | pytest (901 tests, 0 failed) |

### Frontend

| Layer | Công nghệ |
|---|---|
| Framework | React 19 + TypeScript |
| Build Tool | Vite |
| State | React Context + custom hooks |
| Styling | Tailwind CSS |
| Charts | Recharts |
| Realtime | Server-Sent Events (SSE) |

### Infrastructure

| Layer | Công nghệ |
|---|---|
| Deploy | Railway (backend + DB) |
| CI | GitHub Actions (pytest + frontend lint/build) |
| VCS | Git / GitHub |

---

## Evaluation Summary

| Hạng mục | Kết quả |
|---|---:|
| Backend test suite | 901 pass, 0 fail |
| Safety tests | 84 pass, 0 fail |
| Golden dataset | 88 pass, 0 fail |
| Adversarial guardrails | 44 pass, 6 skip (live-backend), 0 fail |
| Heuristic LLM-as-Judge | 50 pass |
| RAGAS heuristic review set | 59 questions, 0 hard fail |
| **Blueprint score** | **98.5 / 100** |
| P0 guardrail failure rate | 0% |

---

## Hướng dẫn cài đặt

### Yêu cầu hệ thống

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+ (hoặc dùng Railway)
- Redis (local hoặc Railway)

### 1. Clone repository

```bash
git clone <repo-url>
cd A20-App-039
```

### 2. Cài AI-log hook (bắt buộc, chạy 1 lần)

```bash
bash scripts/setup_hooks.sh
```

### 3. Setup Backend

```bash
cd backend

# Tạo virtual environment
python -m venv venv
source venv/bin/activate        # Linux/Mac
# venv\Scripts\activate         # Windows

# Cài dependencies
pip install -r requirements.txt

# Cấu hình environment
cp ../.env.example .env
# Mở .env và điền các biến sau:
# - DATABASE_URL (PostgreSQL connection string)
# - OPENAI_API_KEY
# - SECRET_KEY (JWT)
# - REDIS_URL
# - ELEVENLABS_API_KEY (nếu dùng TTS)
# - NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD (nếu dùng graph)

# Chạy migrations
alembic upgrade head
```

### 4. Setup Frontend

```bash
cd frontend

# Cài dependencies
npm install

# Cấu hình
cp .env.example .env.local
# Điền VITE_API_URL=http://localhost:8000
```

---

## Hướng dẫn chạy

### Backend (Development)

```bash
cd backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Backend sẽ khởi động tại `http://localhost:8000`.  
API docs: `http://localhost:8000/docs`  
Health check: `http://localhost:8000/health`  
Metrics: `http://localhost:8000/metrics`

### Frontend (Development)

```bash
cd frontend
npm run dev
```

Frontend sẽ chạy tại `http://localhost:5173`.

### Chạy Tests

```bash
# Backend tests (901 tests)
pytest backend/tests -q

# Frontend lint
npm --prefix frontend run lint

# Frontend build (TypeScript check included)
npm --prefix frontend run build
```

### Chạy Eval Suite

```bash
# Golden dataset (88 cases)
python evals/run_golden.py --dataset evals/datasets/serene_golden_conversation_v1.jsonl

# Adversarial guardrails (50 cases)
python evals/run_guardrails.py --dataset evals/datasets/serene_adversarial_safety_v1.jsonl

# RAGAS quality metrics (59 questions)
python evals/run_ragas.py

# LLM-as-Judge (heuristic mode)
python evals/run_judge.py --mode heuristic
```

---

## Luồng người dùng cơ bản

1. **Đăng ký / Đăng nhập** — Tạo tài khoản hoặc đăng nhập bằng Google OAuth
2. **Onboarding** — Làm bài screening PHQ-9/GAD-7/... ban đầu (tùy chọn)
3. **Chat với Serene** — Nhắn tin tự do; Serene phản hồi như người bạn đồng cảm
4. **Chọn Persona** — Chuyển style mode: Dũng (mặc định), Đạt hoặc Hậu (mở khóa)
5. **Kiểm tra sâu** — DASS-21 / MDQ / PCL-5 khi muốn phân tích đa chiều hơn
6. **Xem Dashboard** — Insight có bằng chứng, biểu đồ tâm trạng, streak, memory cards
7. **Resource Hub** — Khám phá tài nguyên sức khỏe tâm thần và bài tập coping

### Tính năng Safety

- Serene **tự động phát hiện** dấu hiệu khủng hoảng trong mọi tin nhắn qua Safety Gate
- Khi phát hiện nguy cơ cao: hiển thị tin nhắn hỗ trợ khủng hoảng + hotline VN
- Serene **không bao giờ** chẩn đoán ("bạn bị trầm cảm / rối loạn lưỡng cực / PTSD")
- Kết quả DASS-21 / MDQ / PCL-5 chỉ được trình bày như **tín hiệu sàng lọc**, kèm khuyến nghị gặp chuyên gia khi cần
- Crush persona / voice vui / meme **tự động vô hiệu hóa** khi người dùng ở trạng thái nguy cơ cao

---

## Cấu trúc Repository

```
A20-App-039/
├── backend/
│   ├── app/
│   │   ├── api/v1/routers/          # FastAPI route handlers
│   │   ├── core/                    # Config, safety gate, observability
│   │   ├── services/                # Business logic, DB, LangGraph nodes
│   │   │   └── dashboard_insights/  # Evidence-based insight pipeline
│   │   └── main.py                  # App entry point
│   ├── alembic/                     # DB migrations
│   ├── tests/                       # 901 pytest tests
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/              # React components
│   │   ├── hooks/                   # Custom hooks
│   │   └── utils/                   # Utilities
│   └── package.json
├── evals/
│   ├── datasets/                    # Golden + adversarial JSONL datasets
│   ├── reports/                     # Eval results
│   ├── run_golden.py                # Golden dataset runner (88 cases)
│   ├── run_guardrails.py            # Adversarial safety runner (50 cases)
│   ├── run_ragas.py                 # RAGAS quality runner (59 questions)
│   └── run_judge.py                 # LLM-as-Judge runner
├── docs/
│   ├── product/                     # PRD và product spec
│   ├── architecture/                # System architecture và flows
│   ├── api/                         # API documentation
│   └── submission/                  # Evaluation và submission reports
├── .ai-log/                         # AI tool usage logs (auto-generated)
├── .github/workflows/               # CI/CD pipeline
├── JOURNAL.md                       # Weekly journal
├── WORKLOG.md                       # Tech decisions + sprint log
├── CHANGELOG.md                     # Change history
└── eval_report.md                   # Latest evaluation report (98.5/100)
```

---

## Nhóm thực hiện

| Thành viên | Vai trò |
|---|---|
| Lương Thanh Hậu | Team Lead, Backend Architecture, Product|
| Lê Hoàng Đạt | Frontend, Database, QA|
| Lương Tiến Dũng | DevOps, QA|

**Khóa:** AI20K Build Phase  
**Submission deadline:** 23:59 — 17/05/2026

AI prompt logging hooks are installed after running `setup_hooks.sh`.

See [AGENTS.md](./AGENTS.md) for details.
