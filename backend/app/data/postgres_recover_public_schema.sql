-- =============================================================================
-- Khôi phục schema `public` khi PostgREST / log Supabase báo:
--   schema "public" does not exist  (SQLSTATE 3F000)
--
-- Trên project Supabase mới, schema `public` luôn tồn tại; nếu bạn gặp lỗi
-- này, thường là DB trống / lệch cấu hình / restore lỗi — chạy file này
-- trong SQL Editor (role có quyền tạo schema), rồi tạo bảng ứng dụng.
--
-- Sau khi `public` ổn định:
--   - Bật tạm AUTO_CREATE_SCHEMA=true (hoặc dùng migrate SQL của team) để
--     có bảng `users`, `refresh_tokens`, … trước khi chạy postgres_additions.sql
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS public;

GRANT USAGE ON SCHEMA public TO PUBLIC;
GRANT CREATE ON SCHEMA public TO PUBLIC;

-- Supabase thường có các role sau (bỏ qua nếu báo role không tồn tại).
GRANT USAGE ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO postgres;

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
    EXECUTE 'GRANT USAGE ON SCHEMA public TO anon';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    EXECUTE 'GRANT USAGE ON SCHEMA public TO authenticated';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
    EXECUTE 'GRANT USAGE ON SCHEMA public TO service_role';
  END IF;
END
$$;
