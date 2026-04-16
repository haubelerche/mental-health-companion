"""
database.py — Supabase client singleton cho toàn bộ project.

Dùng service role key (SUPABASE_SECRET) để bypass RLS khi cần thao tác
từ phía backend/server. Không dùng key này ở frontend.
"""

from scripts.config import SUPABASE_PROJECT_ID
from supabase import create_client, Client
from scripts.config import SUPABASE_URL, SUPABASE_SECRET

_client: Client | None = None


def get_client() -> Client:
    """Trả về Supabase client (singleton). Tạo mới nếu chưa tồn tại."""
    global _client
    if _client is None:
        if not SUPABASE_URL or not SUPABASE_SECRET:
            raise ValueError(
            )
        _client = create_client(SUPABASE_PROJECT_ID, SUPABASE_SECRET)
    return _client


def test_connection() -> bool:
    """
    Kiểm tra kết nối Supabase bằng cách ping bảng pg_tables trên schema
    information_schema — không cần bảng custom nào cả.
    """
    client = get_client()
    # Query 1 row từ information_schema để xác nhận DB live
    response = client.table("information_schema.tables").select("table_name").limit(1).execute()
    return response is not None
