# Tổng Hợp Tính Năng Và Luồng Chạy Còn Lỗi

Ngày lập: 2026-05-07  
Phạm vi: `backend`, `frontend`, `AUDIT_REPORT.md`, `serene_sos_voice_intervention_plan.md`, kiểm chứng runtime Supabase/FastAPI gần nhất.

## 1. Tóm Tắt Điều Hành

| Nhóm | Trạng thái hiện tại | Rủi ro chính | Mức ưu tiên |
|---|---|---|---|
| Auth / Onboarding | Đã sửa lỗi 500 do `user_profiles.schema_version`; API smoke đã xanh | Cần giữ Alembic version table ở `app` và tránh quay lại `public` | Cao |
| Supabase schema ownership | Core tables chính đã ổn trong `app`; nhiều bảng feature mở rộng vẫn nằm ở `public` | Backend hiện dựa vào `search_path=app,public,extensions`; feature tables có thể lệch khi migration mới chạy | Rất cao |
| Frontend build | `npm --prefix frontend run build` đang fail khi load Tailwind native dependency | Không tạo được production build trong môi trường hiện tại | Rất cao |
| Memory router | Router memory đang được include hai lần | Có thể phát sinh route trùng, OpenAPI nhiễu, hành vi middleware/metrics khó đọc | Trung bình |
| Rewards / Persona / Nutrition / Notifications | API/ORM có tồn tại, nhưng bảng DB thật nằm ở `public`, không phải `app` | Contract DB chưa đóng băng; rủi ro production/staging lệch schema | Rất cao |
| Voice / SOS | Kế hoạch refactor đã có; backend tests trọng yếu xanh | Cần tiếp tục xác minh end-to-end TTS, dedup, crisis plan UI | Cao |
| Dashboard insight | Schema safe view đã tồn tại; backend tests dashboard xanh | Chưa chứng minh đầy đủ flow tạo insight thật sau nhiều phiên thực tế | Cao |

## 2. Bảng Lỗi Và Luồng Còn Rủi Ro

| ID | Khu vực | Luồng / tính năng | Hiện tượng / lỗi còn lại | Bằng chứng hiện tại | Ảnh hưởng | Hành động đề xuất |
|---|---|---|---|---|---|---|
| DB-01 | Database / Migration | Feature tables mở rộng | Các bảng `heart_wallets`, `heart_reward_events`, `heart_spend_events`, `streak_states`, `nutrition_meal_checkins`, `persona_unlock_states`, `reward_store_items`, `user_inventory_items`, `memory_cards`, `user_notifications`, `user_notification_preferences` đang tồn tại ở `public`, chưa thấy ở `app` | Truy vấn `information_schema.tables` trả về các bảng này dưới `public` | Runtime hiện vẫn có thể chạy nhờ `search_path`, nhưng ownership sai; migration sau có thể tạo bảng trùng ở `app` hoặc đọc nhầm schema | Tạo migration idempotent chuyển/đồng bộ các bảng feature sang `app`; sau đó cập nhật schema tests bắt buộc |
| DB-02 | Alembic | Version metadata | Trước khi stamp, `public.alembic_version` vẫn ở `0011`; đã stamp `app` lên `0014`, nhưng cần chuẩn hóa lâu dài | `python -m alembic current -v` hiện báo `0014_auth_auxiliary_tables (head)` | Nếu CI/CD dùng config cũ hoặc version table public, migration có thể chạy sai schema | Giữ `version_table_schema="app"` trong `env.py`; thêm CI check `alembic current` và `select * from app.alembic_version` |
| DB-03 | Database / Mood | Multi check-in | `time_bucket` đã được vá vào `app.mood_checkins`, nhưng cần test API thực tế nhiều khung giờ/ngày | `test_db_integration.py` xanh; chưa có browser smoke theo 3 slot | Có thể dashboard/history chưa thể hiện đúng mọi slot nếu frontend không gửi/hiển thị đầy đủ | Thêm API test tạo morning/afternoon/evening; thêm Playwright check history reload |
| BE-01 | API routing | Memory cards API | `memory_router` được include hai lần trong `backend/app/api/v1/api.py` | File có hai dòng `api_router.include_router(memory_router)` | Route duplicate có thể làm OpenAPI nhiễu và gây khó trace metrics/logging | Xóa một dòng include trùng; thêm smoke test route memory chỉ xuất hiện một lần trong OpenAPI |
| BE-02 | Rewards / Hearts | Reward store và heart economy | Bảng reward/heart thật đang ở `public`, trong khi core contract ưu tiên `app` | Kiểm tra DB thật: `heart_wallets`, `heart_reward_events`, `heart_spend_events`, `streak_states` dưới `public` | Purchase, balance, check-in reward có thể chạy theo `public`; khi migrate sang `app` cần tránh mất dữ liệu | Viết migration copy/attach ownership rõ ràng sang `app`; khóa test schema cho các bảng rewards |
| BE-03 | Persona Unlock | Persona unlock state | `persona_unlock_states` ở `public`, không phải `app`; logic route hiện đã gọi `route_persona()` và `is_persona_unlocked()` | Code hiện có call site trong `chat.py` và `auth.py`; DB table lại nằm ở `public` | Logic đúng nhưng storage contract chưa đúng; staging mới có thể thiếu bảng | Chuyển bảng sang `app` hoặc cấu hình ORM schema rõ ràng; thêm real DB test cho persona unlock read/write |
| BE-04 | Nutrition | Meal check-in | `nutrition_meal_checkins` tồn tại ở `public`, chưa ở `app`; chưa smoke test từ frontend | DB kiểm tra bảng nằm ở `public`; frontend có `MealCheckInCard.tsx` | Meal flow có nguy cơ 500 khi search_path hoặc migration thay đổi | Tạo migration app-scoped; chạy API smoke meal check-in và reload |
| BE-05 | Notifications | Notification persistence | `user_notifications`, `user_notification_preferences` đang ở `public`, không phải `app` | DB kiểm tra bảng nằm ở `public` | WebSocket/toast có thể hoạt động nhưng lịch sử notification không thuộc schema app chuẩn | Migration sang `app`; test mark-read/list notification |
| BE-06 | Dashboard | Insight pipeline thật | Schema và tests dashboard backend xanh, nhưng chưa chứng minh đầy đủ flow chat/check-in -> analyst_signals -> insight_hypotheses -> dashboard_safe_insights bằng dữ liệu thực | Backend tests liên quan đã xanh; chưa có e2e multi-session | Có thể dashboard vẫn rơi về trạng thái chưa đủ dữ liệu hoặc chỉ dùng fallback | Thêm integration test end-to-end đủ dữ liệu; kiểm tra không expose `clinical_note_internal` và `risk_indicators` |
| BE-07 | Voice / TTS | Crisis voice intervention | Kế hoạch yêu cầu tách `visible_text` và `voice_script`, dedup TTS, safety validator; cần xác minh implementation cuối cùng bằng e2e | `serene_sos_voice_intervention_plan.md` mô tả acceptance; tests voice chưa được chạy trong batch cuối | Trùng TTS, voice đọc lại nguyên văn hoặc chưa có action-stepper nếu implementation chưa đủ | Chạy `test_voice_*`, `test_safety_escalate_integration.py`; thêm browser smoke SOS UI |
| BE-08 | Text encoding | Chuỗi tiếng Việt mojibake | Nhiều file frontend/backend đang hiển thị chuỗi bị mã hóa sai như `Äang lÆ°u`, `Ráº¥t tá»‘t`, `KhÃ´ng thá»ƒ...` | Quan sát trong `CheckinFlow.tsx`, một số output console và tài liệu cũ | UI tiếng Việt có thể hiển thị lỗi ký tự, ảnh hưởng nghiêm trọng tới trải nghiệm | Chạy audit encoding toàn repo; sửa file về UTF-8 chuẩn; thêm snapshot test text quan trọng |
| FE-01 | Frontend build | Production build | `npm --prefix frontend run build` fail tại load config vì Tailwind native dependency `@tailwindcss/oxide-win32-x64-msvc` không load được và `spawn EPERM` | Lệnh build ngày 2026-05-07 fail trước bước Vite build | Không thể tạo artifact production từ môi trường hiện tại | Cài lại dependency native (`npm ci`), kiểm tra antivirus/permission Windows, xóa `node_modules` và lock nếu cần |
| FE-02 | Onboarding | Local storage sau complete | `OnboardingFlow.tsx` còn ghi `localStorage` sau complete | `rg` thấy `localStorage.setItem` trong onboarding | Có thể là cache UX hợp lệ, nhưng cần đảm bảo backend vẫn là nguồn sự thật | Document đây là cache phụ; khi reload phải gọi `/onboarding/state` và ưu tiên backend |
| FE-03 | App settings | Client-only settings | `appSettings.ts` dùng `localStorage` | `frontend/src/utils/appSettings.ts` | Không phải lỗi nếu chỉ là UI preference; rủi ro nếu chứa state nghiệp vụ | Xác nhận chỉ lưu theme/settings không nghiệp vụ; không lưu clinical/reward/profile |
| QA-01 | Frontend smoke | Tab persistence | Chưa có Playwright smoke đầy đủ cho mọi tab: chat, mood, dashboard, memory, resources, rewards, persona, nutrition, voice | Yêu cầu trong prompt; hiện mới có API/backend smoke | Có thể còn save action local-only hoặc reload mất dữ liệu | Tạo Playwright suite: thao tác save -> reload -> verify data |
| QA-02 | Pool soak | Connection pool | Chưa chạy soak 50-100 request sau khi fix search_path/pool | Trước đó từng gặp `EMAXCONNSESSION`; batch cuối chưa stress test | Lỗi pool có thể tái phát khi nhiều tab/worker chạy | Script gọi lặp `/auth/me`, `/onboarding/state`, dashboard, chat; đo `pg_stat_activity` |

## 3. Luồng Đã Sửa Và Đã Kiểm Chứng

| Luồng | Trạng thái | Bằng chứng kiểm chứng |
|---|---|---|
| Signup -> session cookie | Đã chạy được | API smoke `POST /v1/auth/signup` trả `202` |
| Auth session | Đã chạy được | API smoke `GET /v1/auth/me` trả `200` |
| Onboarding state | Đã chạy được | API smoke `GET /v1/onboarding/state` trả `200` |
| Onboarding skip | Đã chạy được | API smoke `POST /v1/onboarding/skip` trả `200` |
| Onboarding complete + reload | Đã chạy được | API smoke `POST /v1/onboarding/complete`, sau đó reload state trả profile persisted |
| DB schema core | Đã kiểm chứng | `python backend/scripts/verify_db_schema.py` pass |
| DB integration | Đã kiểm chứng | `python -m pytest backend/tests/test_db_integration.py -q` -> `17 passed` |
| Backend feature regression batch | Đã kiểm chứng | `python -m pytest backend/tests/test_chat_router_integration.py backend/tests/test_dashboard_reflect.py backend/tests/test_heart_economy.py backend/tests/test_persona_router_integration.py backend/tests/test_memory_cards.py -q` -> `63 passed` |

## 4. Ma Trận Ưu Tiên Sửa

| Ưu tiên | Việc cần làm | Lý do | Tiêu chí hoàn thành |
|---|---|---|---|
| P0 | Sửa frontend build environment | Không có build production thì không thể release đáng tin cậy | `npm --prefix frontend run build` pass |
| P0 | Đồng bộ feature tables từ `public` sang `app` hoặc schema-map rõ ràng | Đây là nguồn rủi ro lớn nhất còn lại về DB contract | Real DB tests xác nhận mọi bảng ORM nghiệp vụ nằm trong `app` hoặc được document schema rõ |
| P1 | Xóa mount trùng `memory_router` | Giảm nhiễu route/OpenAPI và rủi ro observability | OpenAPI chỉ có một set memory routes |
| P1 | Chạy soak test pool | Xác minh lỗi `EMAXCONNSESSION` không tái diễn | 50-100 request không tăng connection đơn điệu, không có 500 |
| P1 | Chạy Playwright persistence smoke | Bắt lỗi frontend local-only và reload mất dữ liệu | Mọi tab save được và reload còn dữ liệu |
| P2 | Sửa mojibake tiếng Việt | Cần cho demo và trải nghiệm người dùng | UI text chính hiển thị tiếng Việt chuẩn |
| P2 | E2E SOS voice | Đảm bảo safety-critical flow đúng contract | SOS tạo visible text, voice script, action cards, TTS dedup đúng |

## 5. Lệnh Kiểm Tra Nên Chạy Sau Khi Sửa

| Mục tiêu | Lệnh |
|---|---|
| Schema Supabase | `python backend/scripts/verify_db_schema.py` |
| Alembic head | `cd backend; python -m alembic current -v` |
| DB integration | `python -m pytest backend/tests/test_db_integration.py -q` |
| Backend regression trọng yếu | `python -m pytest backend/tests/test_chat_router_integration.py backend/tests/test_dashboard_reflect.py backend/tests/test_heart_economy.py backend/tests/test_persona_router_integration.py backend/tests/test_memory_cards.py -q` |
| Frontend build | `npm --prefix frontend run build` |
| Full backend suite | `python -m pytest backend/tests -q` |
| Frontend E2E | `npx playwright test` nếu project đã cấu hình Playwright |

## 6. Ghi Chú Phân Loại

| Nhãn | Ý nghĩa |
|---|---|
| Lỗi xác nhận | Đã tái hiện bằng command/test hoặc truy vấn DB thật |
| Rủi ro contract | Code có thể chạy hiện tại nhưng schema/source-of-truth chưa rõ hoặc phụ thuộc `search_path` |
| Chưa kiểm chứng | Chưa có smoke/e2e đủ mạnh để kết luận an toàn |

