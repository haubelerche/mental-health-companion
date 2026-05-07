"""
Chạy: DATABASE_URL=<supabase_url> python backend/scripts/verify_db_schema.py
Kiểm tra: kết nối, schema app tồn tại, các bảng core có đúng không.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import sqlalchemy as sa
from app.core.config import get_settings

REQUIRED_TABLES = [
    "users", "refresh_tokens", "conversations", "messages",
    "mood_checkins", "resources", "bookmarks", "play_events",
    "conversation_memories", "session_summaries_archive",
    "user_profiles", "user_profile_snapshots",
    "clinical_profiles", "risk_inference_log", "session_risk_snapshots",
    "crisis_logs", "analyst_signals", "insight_hypotheses",
    "sync_outbox", "admin_audit_log",
]

def main():
    settings = get_settings()
    db_url = settings.normalized_database_url()
    if "sqlite" in db_url:
        print("❌ DATABASE_URL chưa set — đang dùng SQLite local, không phải Supabase")
        sys.exit(1)

    engine = sa.create_engine(db_url, connect_args={"connect_timeout": 10})
    try:
        with engine.connect() as conn:
            conn.execute(sa.text("SET search_path TO app, public, extensions"))
            print(f"✅ Kết nối thành công: {db_url[:50]}...")

            result = conn.execute(sa.text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'app' ORDER BY table_name"
            ))
            existing = {row[0] for row in result}
            print(f"\n📋 Bảng tồn tại trong schema app ({len(existing)}):")
            for t in sorted(existing):
                marker = "✅" if t in REQUIRED_TABLES else "🆕"
                print(f"  {marker} {t}")

            missing = set(REQUIRED_TABLES) - existing
            if missing:
                print(f"\n❌ Bảng THIẾU trong Supabase ({len(missing)}):")
                for t in sorted(missing):
                    print(f"  ✗ {t}")
                sys.exit(1)
            else:
                print("\n✅ Tất cả required tables tồn tại!")

            # Kiểm tra columns của messages
            cols = conn.execute(sa.text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema='app' AND table_name='messages' ORDER BY column_name"
            ))
            msg_cols = {r[0] for r in cols}
            print(f"\n📋 messages columns: {sorted(msg_cols)}")
            if "assistant_tone" not in msg_cols:
                print("  ❌ assistant_tone THIẾU trong messages!")
            if "tone_cam_xuc" in msg_cols:
                print("  ⚠️  tone_cam_xuc vẫn tồn tại — cần đổi tên")

    except Exception as e:
        print(f"❌ Kết nối thất bại: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
