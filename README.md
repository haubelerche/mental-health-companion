# **Serene.AI** — Trợ lý AI hỗ trợ sàng lọc và Chăm sóc sức khỏe tinh thần cho người Việt.

> **Live URL:** [Serene.AI](https://a20-app-039.vercel.app/) <br>
> **Video Demo:** *(YouTube link — cập nhật trước khi nộp)* <br>
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

**Serene** là AI companion sức khỏe tâm thần đầu tiên được thiết kế riêng cho sinh viên và Gen Z Việt Nam. Serene trò chuyện như một người bạn đồng trang lứa — lắng nghe, đồng cảm, hỗ trợ đúng lúc — trong khi chạy ngầm một hệ thống phân tích lâm sàng và an toàn khủng hoảng mà người dùng không bao giờ thấy.

Serene giải quyết khoảng trống mà không app nào trên thị trường VN đang lấp: **AI tiếng Việt + trải nghiệm peer-to-peer + safety chuẩn lâm sàng**.

---

## Mục tiêu / Vấn đề giải quyết

**Bài toán:** 45% sinh viên VN có dấu hiệu lo âu/trầm cảm đáng kể (nguồn: WHO, 2023), nhưng tỷ lệ tiếp cận hỗ trợ tâm lý chuyên nghiệp dưới 10%. Rào cản chính: stigma xã hội, chi phí cao, thiếu cơ sở vật chất, ngại gặp trực tiếp.

**Giải pháp:** Một AI companion có thể:
1. Nói chuyện tự nhiên bằng tiếng Việt Gen Z — không nghe như chatbot hoặc bác sĩ
2. Phát hiện sớm dấu hiệu khủng hoảng qua phân tích ngầm (implicit PHQ-9/GAD-7)
3. Kích hoạt can thiệp khẩn cấp khi cần, cung cấp hotline VN uy tín
4. Không bao giờ chẩn đoán — luôn giữ ranh giới lâm sàng

---

## Tính năng chính

| Tính năng | Mô tả |
|---|---|
| **Chat AI tiếng Việt** | Hội thoại tự nhiên với persona Serene — empathetic, đồng trang lứa, không clinical |
| **Safety Gate** | Rule-based gate chạy trước mọi LLM call — phát hiện khủng hoảng trong < 100ms |
| **SOS Intervention** | Kích hoạt khi phát hiện nguy cơ cao: hotline VN, de-escalation script, CrisisLog |
| **Implicit Screening** | PHQ-9/GAD-7 ngầm qua hội thoại — không hỏi trực tiếp, không gây stigma |
| **Memory Cards** | Lưu ký ức hội thoại dưới dạng thẻ nhớ — Serene nhớ tên, sự kiện, cảm xúc quan trọng |
| **Personas** | 4 style mode: Default, Calm, Motivate, Crush — cùng 1 identity, khác tone |
| **Voice TTS** | Text-to-speech với ElevenLabs — SOS có `visible_text` và `voice_script` riêng |
| **Resource Hub** | Thư viện tài nguyên sức khỏe tâm thần: bài viết, video YouTube, hotline |
| **Screening** | PHQ-9/GAD-7 chính thức với kết quả lưu phía backend (không localStorage) |
| **Dashboard** | Biểu đồ tâm trạng, lifestyle rhythm, streak, memory summary |
| **Push Notifications** | Nhắc nhở chủ động, mood check-in, wellness tips qua SSE |

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
| Observability | Structured JSON logging (python-json-logger) + Prometheus metrics |
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

## Hướng dẫn sử dụng sản phẩm

### Luồng người dùng cơ bản

1. **Đăng ký / Đăng nhập** — Tạo tài khoản hoặc đăng nhập bằng Google OAuth
2. **Onboarding** — Làm bài screening PHQ-9/GAD-7 ban đầu (tùy chọn)
3. **Chat với Serene** — Nhắn tin tự do, Serene phản hồi như người bạn đồng cảm
4. **Chọn Persona** — Chuyển style mode (Default / Calm / Motivate / Crush)
5. **Xem Dashboard** — Theo dõi tâm trạng, streak, memory cards
6. **Resource Hub** — Khám phá tài nguyên sức khỏe tâm thần

### Tính năng Safety

- Serene **tự động phát hiện** dấu hiệu khủng hoảng trong mọi tin nhắn
- Khi phát hiện nguy cơ cao: hiển thị tin nhắn hỗ trợ khủng hoảng + hotline VN
- Serene **không bao giờ** chẩn đoán, không nói "bạn bị trầm cảm"
- Crush persona tự động vô hiệu hóa khi người dùng ở trạng thái nguy cơ cao

---

## Cấu trúc Repository

```
A20-App-039/
├── backend/
│   ├── app/
│   │   ├── api/v1/routers/      # FastAPI route handlers
│   │   ├── core/                # Config, safety gate, observability
│   │   ├── services/            # Business logic, DB, LangGraph nodes
│   │   └── main.py              # App entry point
│   ├── alembic/                 # DB migrations
│   ├── tests/                   # 901 pytest tests
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/          # React components
│   │   ├── hooks/               # Custom hooks
│   │   └── utils/               # Utilities
│   └── package.json
├── evals/
│   ├── datasets/                # Golden + adversarial JSONL datasets
│   ├── reports/                 # Eval results
│   ├── run_golden.py            # Golden dataset runner (88 cases)
│   ├── run_guardrails.py        # Adversarial safety runner (50 cases)
│   ├── run_ragas.py             # RAGAS quality runner (59 questions)
│   └── run_judge.py             # LLM-as-Judge runner
├── docs/
│   ├── product/                 # Product requirements and spec
│   ├── architecture/            # System architecture and flows
│   ├── api/                     # API documentation
│   └── submission/              # Evaluation and submission reports
├── .ai-log/                     # AI tool usage logs (auto-generated)
├── .github/workflows/           # CI/CD pipeline
├── JOURNAL.md                   # Weekly journal
├── WORKLOG.md                   # Tech decisions + sprint log
├── CHANGELOG.md                 # Change history
└── eval_report.md               # Latest evaluation report (98.5/100)
```

---

## Nhóm thực hiện

| Thành viên | Vai trò |
|---|---|
| Lương Thanh Hậu | Team Lead, Backend Architecture, AI/LangGraph, Safety System |
| Lê Hoàng Đạt | Backend Engineering, Database, API, Testing |
| Lương Tiến Dũng | Frontend Engineering, UX, Research |

**Khóa:** AI20K Build Phase
**Submission deadline:** 23:59 — 17/05/2026

AI prompt logging hooks are installed after running `setup_hooks.sh`.

See [AGENTS.md](./AGENTS.md) for details.
