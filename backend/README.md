# Serene FastAPI Backend

## Tong Quan Nhanh

Day la backend FastAPI cho app ho tro suc khoe tinh than. Du an gom day du cac nhom API chinh:
- Auth: dang ky, dang nhap, refresh, logout, CSRF
- Chat: gui tin nhan, lich su phien chat, xoa phien
- Home/Mood: checkin tam trang, sua checkin, home feed
- Reflect: journal, mood trend, weekly note, prompts
- Resources: danh sach noi dung, chi tiet, play event, bookmark
- Connect: hotline, clinic
- Admin: crisis logs, dashboard, admin login

## Diem Noi Bat

- Xac thuc bang cookie httpOnly + CSRF, khong tra token trong body.
- Rate limit va lockout bang Redis.
- Database schema duoc quan ly bang Alembic migration.
- PostgreSQL/Supabase duoc ho tro qua `DATABASE_URL` trong `.env`.
- Tai lieu test chi tiet nam trong [docs/API_TESTS.md](../docs/API_TESTS.md).

Neu muon test nhanh, hay doc theo thu tu trong file API TEST va chay backend dung cac lenh o phan duoi.

## Sau Khi Clone Ve Can Bo Sung Gi?

1. Tao file `.env` o thu muc goc repository (copy tu `backend/.env.example`).
2. Dien toi thieu cac bien:
- `DATABASE_URL`
- `REDIS_URL`
- `ADMIN_ALLOWED_IPS`
3. Tuy chon dev: `JWT_PRIVATE_KEY`, `JWT_PUBLIC_KEY` co the de trong.

## Chay Backend (Dung Thu Tu)

1. Kich hoat venv (Windows):

```powershell
venv\Scripts\Activate.ps1
```

2. Cai thu vien:

```bash
pip install -r backend/requirements.txt
```

3. Chay migration DB:

```bash
alembic -c backend/alembic.ini upgrade head
```

4. Chay API:

```bash
uvicorn app.main:app --app-dir backend --reload
```

Base URL: `http://localhost:8000/v1`

Health check: `http://localhost:8000/health`

## Alembic La Gi? (Ngan Gon)

Alembic la cong cu dong bo schema database theo version code.

No giup:
- Tao/cap nhat bang va cot dung theo model.
- Tranh loi thieu bang, sai schema khi chay backend.
- Quan ly lich su thay doi DB de team cung theo mot chuan.

Lenh quan trong nhat:

```bash
alembic -c backend/alembic.ini upgrade head
```

Lenh nay phai chay truoc khi chay backend neu schema DB chua moi nhat.
