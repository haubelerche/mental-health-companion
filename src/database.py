"""
database.py — Supabase client singleton cho toàn bộ project.

Dùng service role key (SUPABASE_SECRET) để bypass RLS khi cần thao tác
từ phía backend/server. Không dùng key này ở frontend.
"""

from supabase import create_client, Client
from scripts.config import DATABASE_URL, SUPABASE_URL, SUPABASE_SECRET

_client: Client | None = None


def get_client() -> Client:
    """Trả về Supabase client (singleton). Tạo mới nếu chưa tồn tại."""
    global _client
    if _client is None:
        if not SUPABASE_URL or not SUPABASE_SECRET:
            raise ValueError("SUPABASE_URL and SUPABASE_SECRET are required (set in .env).")
        # create_client(url, key) — không dùng project ref làm URL.
        _client = create_client(SUPABASE_URL, SUPABASE_SECRET)
    return _client


def test_connection() -> bool:
    """
    Xác nhận Postgres (Supabase) bằng wire protocol qua DATABASE_URL.
    PostgREST may return HTTP 503 while Postgres still accepts direct connections.
    """
    if not DATABASE_URL:
        raise ValueError(
            "Missing DATABASE_URL in .env. Copy the connection string from Supabase Dashboard "
            "-> Project Settings -> Database (transaction pooler or direct)."
        )
    import psycopg

    with psycopg.connect(DATABASE_URL, connect_timeout=15) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            row = cur.fetchone()
    return bool(row and row[0] == 1)
