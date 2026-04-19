# Hướng dẫn cài đặt dự án (cho người mới)

Tài liệu này giúp bạn chạy được **backend (FastAPI)**, **frontend (React + Vite)** và **cơ sở dữ liệu (PostgreSQL + pgvector)** trên máy Windows (và tương tự trên macOS/Linux). Đọc theo thứ tự từ trên xuống.

---

## 1. Bạn sẽ cài những gì?

| Thành phần | Vai trò | Bắt buộc? |
|------------|---------|-----------|
| **Git** | Clone repo, hook (xem `AGENTS.md`) | Có |
| **Python 3.12+** | Chạy API | Có |
| **Node.js (LTS, khuyến nghị 20+)** | `npm` cho frontend | Có |
| **PostgreSQL** có extension **pgvector** | Lưu user, chat, bảng có embedding | Có |
| **Redis** | Cache, rate limit, guest session (tốt hơn khi có) | Khuyến nghị |
| **Neo4j** | Đồ thị tri thức (một số luồng / script nạp dữ liệu) | Tùy chọn khi mới bắt đầu |

Tài liệu schema chi tiết: [`docs/DB_SCHEMA.md`](./DB_SCHEMA.md).

---

## 2. Chuẩn bị trên Windows

### 2.1 Cài Git

- Tải và cài từ [https://git-scm.com](https://git-scm.com) (cài kèm **Git Bash** nếu được hỏi — hữu ích cho script `bash` trong repo).

### 2.2 Cài Python

- Tải Python 3.12 từ [https://www.python.org](https://www.python.org).
- Khi cài, **tick** “Add Python to PATH”.
- Mở **PowerShell** mới, kiểm tra:

```powershell
python --version
pip --version
```

### 2.3 Cài Node.js

- Tải bản **LTS** từ [https://nodejs.org](https://nodejs.org).
- Kiểm tra:

```powershell
node --version
npm --version
```

### 2.4 OpenSSL (để tạo khóa JWT)

- Nếu đã cài **Git for Windows**, thường đã có `openssl` trong Git Bash hoặc trong `C:\Program Files\Git\usr\bin`.
- Kiểm tra trong PowerShell:

```powershell
openssl version
```

Nếu chưa có, có thể dùng Git Bash chạy các lệnh openssl bên dưới.

---

## 3. Lấy mã nguồn về máy

```powershell
cd $env:USERPROFILE\Desktop
git clone <URL-repo-của-team>
cd <thư-mục-repo-vừa-clone>
```

(Thay `<thư-mục-repo-vừa-clone>` bằng tên thư mục thật, ví dụ `A20-App-039`.)

(Thay `<URL-repo-của-team>` bằng URL thật.)

### Hook AI (theo `AGENTS.md`)

Sau khi clone, **một lần**:

```bash
bash scripts/setup_hooks.sh
```

Nếu không có bash, dùng **Git Bash** từ menu Start, `cd` vào thư mục repo rồi chạy lệnh trên.

---

## 4. Database: PostgreSQL + pgvector

Backend dùng biến môi trường **`DATABASE_URL`** (chuỗi kết nối PostgreSQL). Ứng dụng cũng cần kiểu **`vector`** (pgvector) cho bảng có embedding — xem `docs/DB_SCHEMA.md`.

Bạn có thể chọn **một trong hai** hướng: cloud (Supabase) hoặc PostgreSQL local (Docker).

### Cách A — Supabase (dễ cho người mới, không cần cài Postgres trên máy)

1. Vào [https://supabase.com](https://supabase.com), tạo project mới (chọn region gần team).
2. Vào **Project Settings → Database**, copy **Connection string** dạng URI (thường có dạng `postgresql://postgres.[ref]:[PASSWORD]@...:5432/postgres`).
3. Trong Supabase: **Database → Extensions**, bật extension **`vector`** (pgvector).
4. Chuỗi này sẽ dùng cho `DATABASE_URL` ở bước 6.

**Lưu ý:** Trong code, URL chứa `supabase.com` sẽ được gắn `sslmode=require` khi cần — bạn chỉ cần dán đúng URI từ dashboard.

### Cách B — PostgreSQL trên Docker (local)

Yêu cầu: [Docker Desktop](https://www.docker.com/products/docker-desktop/) cho Windows.

Ví dụ chạy Postgres 15 kèm pgvector (một container):

```powershell
docker run -d --name serene-pg `
  -e POSTGRES_PASSWORD=postgres `
  -e POSTGRES_USER=postgres `
  -e POSTGRES_DB=serene `
  -p 5432:5432 `
  pgvector/pgvector:pg15
```

Sau khi container chạy, `DATABASE_URL` có thể là:

```text
postgresql://postgres:postgres@127.0.0.1:5432/serene
```

Vào database một lần để bật extension (nếu image chưa bật sẵn):

```powershell
docker exec -it serene-pg psql -U postgres -d serene -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

---

## 5. Tạo cặp khóa JWT (bắt buộc cho đăng nhập)

API dùng **RS256**: cần **`JWT_PRIVATE_KEY`** và **`JWT_PUBLIC_KEY`** (PEM). Không commit khóa lên git; chỉ để trong `.env` máy bạn.

Trong **Git Bash** hoặc nơi có `openssl`:

```bash
openssl genrsa -out jwt_private.pem 2048
openssl rsa -in jwt_private.pem -pubout -out jwt_public.pem
```

Mở hai file `.pem` bằng editor, **copy toàn bộ nội dung** (có dòng `BEGIN` / `END`).

Trong file `.env` (bước sau), nhiều môi trường hỗ trợ khóa nhiều dòng trong dấu nháy. Ví dụ (minh họa — dùng nội dung file thật của bạn):

```env
JWT_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----
...nhiều dòng...
-----END PRIVATE KEY-----"

JWT_PUBLIC_KEY="-----BEGIN PUBLIC KEY-----
...nhiều dòng...
-----END PUBLIC KEY-----"
```

Nếu parser `.env` của bạn không ăn khóa nhiều dòng, hỏi teammate hoặc gom một dòng với `\n` (ít gọn hơn). Quan trọng là backend đọc được đúng PEM.

---

## 6. File môi trường `.env`

Config được nạp từ:

1. **Thư mục gốc repo**: `.env` (ưu tiên)
2. Sau đó: `backend/.env` nếu có

**Cách làm:**

```powershell
cd <đường-dẫn-tới-thư-mục-gốc-repo>
copy .env.example .env
```

Mở `.env` và **bổ sung / chỉnh** các mục sau (tên biến đúng chữ hoa như bảng — Pydantic đọc từ env):

| Biến | Ý nghĩa |
|------|---------|
| `DATABASE_URL` | URI PostgreSQL (mục 4). **Bắt buộc** để API làm việc với DB. |
| `JWT_PRIVATE_KEY`, `JWT_PUBLIC_KEY` | PEM RS256 (mục 5). **Bắt buộc** cho auth. |
| `OPENAI_API_KEY` | **Khuyến nghị** cho chat/agent (xem `docs/DEMO_RUNBOOK_10M.md`). |
| `CSRF_TRUSTED_ORIGINS` | **Bắt buộc** khi gọi API từ trình duyệt: danh sách origin, cách nhau bởi dấu phẩy. Ví dụ dev Vite: `http://127.0.0.1:5173,http://localhost:5173` |
| `COOKIE_SECURE` | Trên HTTP local, đặt **`false`** để cookie auth/CSRF hoạt động (trình duyệt không gửi cookie `Secure` qua `http://`). |
| `AUTO_CREATE_SCHEMA` | Dev nhanh: đặt **`true`** để khi khởi động API, SQLAlchemy tạo bảng (xem `backend/app/main.py`). Hoặc giữ `false` và dùng Alembic (mục 7). |
| `REDIS_URL` | Mặc định trong code là `redis://localhost:6379/0`. Nếu không chạy Redis, một số phần vẫn chạy nhưng cache/rate limit có thể kém ổn định — nên cài Redis local hoặc bỏ qua khi chỉ test nhanh. |
| `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` | Để trống nếu chưa dùng Neo4j; driver sẽ không khởi tạo. |
| Các biến `SUPABASE_*` trong `.env.example` | Tuỳ tính năng; không thay thế `DATABASE_URL` trừ khi team có hướng dẫn riêng. |

**Ví dụ khối tối thiểu cho dev local (chỉnh lại cho đúng máy bạn):**

```env
DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:5432/serene

JWT_PRIVATE_KEY="...(PEM)..."
JWT_PUBLIC_KEY="...(PEM)..."

OPENAI_API_KEY=sk-...

CSRF_TRUSTED_ORIGINS=http://127.0.0.1:5173,http://localhost:5173
COOKIE_SECURE=false

AUTO_CREATE_SCHEMA=true
```

Giữ các dòng khác trong `.env.example` (logging, voice, v.v.) theo hướng dẫn team; không chia sẻ khóa bí mật ra ngoài repo.

---

## 7. Tạo bảng trong PostgreSQL

Hai cách (chọn một):

### Cách 1 — `AUTO_CREATE_SCHEMA=true`

Khởi động backend (mục 8). Ở lần chạy đầu, `init_db()` sẽ `create_all` các bảng.

### Cách 2 — Alembic (khuyến nghị khi làm việc nhóm lâu dài)

```powershell
cd <đường-dẫn-repo>\backend
..\venv\Scripts\activate
alembic upgrade head
```

(Giả sử venv đặt ở thư mục gốc repo — xem mục 8.)

**Trước khi tạo bảng có cột `vector`:** Postgres phải đã có extension `vector` (mục 4). Nếu lỗi kiểu `type "vector" does not exist`, chạy lại:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

---

## 8. Cài đặt và chạy backend

```powershell
cd <đường-dẫn-repo>
python -m venv venv
.\venv\Scripts\activate
pip install -r backend\requirements.txt
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Kiểm tra:

- Trình duyệt hoặc `curl`: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health) → JSON `{"status":"ok"}`.

API có tiền tố mặc định **`/v1`** (ví dụ CSRF: `GET /v1/auth/csrf-token`).

---

## 9. Redis (khuyến nghị)

Cách nhanh với Docker:

```powershell
docker run -d --name serene-redis -p 6379:6379 redis:7-alpine
```

Giữ `REDIS_URL=redis://localhost:6379/0` (mặc định trong code nếu không đổi).

---

## 10. Cài đặt và chạy frontend

```powershell
cd <đường-dẫn-repo>\frontend
npm install
npm run dev
```

- Vite thường mở **http://127.0.0.1:5173**.
- Trong `vite.config.ts` đã có **proxy** `/v1` và `/health` sang `http://127.0.0.1:8000`, nên frontend gọi API cùng origin (tránh lỗi CORS khi dev).

`frontend/src/lib/api.ts` mặc định dùng `http://127.0.0.1:8000` nếu không set `VITE_API_BASE_URL`. Khi dev với proxy, có thể để trống hoặc cấu hình theo team.

Thử: đăng ký / đăng nhập trên UI; nếu lỗi **CSRF** hoặc **403**, kiểm tra lại `CSRF_TRUSTED_ORIGINS` và `COOKIE_SECURE`.

---

## 11. Neo4j (tùy chọn)

- Neo4j **Aura** hoặc Docker image `neo4j` đều được.
- Sau khi có URI và mật khẩu, điền `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` vào `.env`.
- Với **Neo4j Aura**, user mặc định thường là `neo4j`, database mặc định `neo4j` (code có chỉnh hợp lý cho hostname Aura — xem `backend/app/core/config.py`).

Script nạp dữ liệu mẫu (nếu team dùng): xem `backend/app/data/load_data.py` và file cypher trong `backend/app/data/`.

---

## 12. Chạy test backend (tùy chọn)

```powershell
cd <đường-dẫn-repo>
.\venv\Scripts\activate
pip install pytest
pytest backend\tests -q
```

Một số test có thể mock DB; nếu fail vì thiếu biến môi trường, bổ sung `.env` như trên.

---

## 13. Sự cố thường gặp

| Hiện tượng | Hướng xử lý |
|------------|-------------|
| `DATABASE_URL is required` | Thiếu `DATABASE_URL` trong `.env` gốc hoặc sai tên biến. |
| Lỗi SSL khi nối Supabase | Dùng đúng connection string từ dashboard; với Supabase, code thêm `sslmode=require` khi cần. |
| `type "vector" does not exist` | Chưa bật extension pgvector — mục 4. |
| `JWT keys are missing` | Thiếu hoặc sai định dạng PEM — mục 5. |
| Login được nhưng POST bị 403 / CSRF | Thiếu `CSRF_TRUSTED_ORIGINS`; Origin trình duyệt phải khớp một giá trị trong danh sách. |
| Cookie không lưu | Đặt `COOKIE_SECURE=false` khi chỉ dùng `http://` local. |
| Frontend không nói chuyện được với API | Backend chưa chạy port 8000; hoặc sai `VITE_API_BASE_URL`. |

---

## 14. Tài liệu thêm trong repo

- [`README.md`](../README.md) — cấu trúc repo và journal/worklog.
- [`backend/README.md`](../backend/README.md) — lệnh chạy API ngắn gọn.
- [`docs/DB_SCHEMA.md`](./DB_SCHEMA.md) — mô tả bảng, RLS, lưu ý compliance.
- [`docs/DEMO_RUNBOOK_10M.md`](./DEMO_RUNBOOK_10M.md) — kịch bản demo 10 phút.
- [`AGENTS.md`](../AGENTS.md) — quy tắc hook AI và PR.

Chúc bạn setup thuận lợi; nếu kẹt bước nào, chụp **log lỗi đầy đủ** và hỏi teammate kèm OS (Windows/macOS) và cách bạn chọn Postgres (Supabase hay Docker).
