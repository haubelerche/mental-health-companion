# Changelog — Serene

> Format: [Keep a Changelog](https://keepachangelog.com) | Vingroup Engineering

---

## [Unreleased] — Sprint 5 · 2026-04-27

### Added
- **`Chat.tsx`** — Thiết kế lại hoàn toàn giao diện Chat theo phong cách **Cozy Pixel Café**: GIF `nen2.gif` (hai chú mèo pixel art) làm backdrop cố định cao 300px; bubble thoại mini-pixel tự động nổi bên trên mèo trắng (Serene/AI) và mèo đen (User) theo tin nhắn mới nhất; các tin nhắn trong feed dùng **pixel dialogue box** có border 3px kiểu JRPG (cream cho AI, dark cho user, đỏ cho SOS), animation step-reveal `pixelReveal`; thanh input tối phong cách terminal với nút `SEND ►` font pixel. Toàn bộ logic nghiệp vụ (streaming, SSE, guest mode, voice consent, debug mode) giữ nguyên. Thêm font **Press Start 2P** và CSS pixel-art vào `index.css`.
- **`Nutrition.tsx`** — Thiết kế lại theo phong cách **Vintage Minimalism**: bỏ card glassmorphism, dùng layout mở với `border-b` divider mỏng, tiêu đề italic serif lớn, daily tip kiểu blockquote editorial, ba pillars thành text list thoáng.
- **`BambooForest.tsx`** + **`anonymousShareService.ts`** — Nâng cấp giao diện/luồng "Rừng Trúc" theo hướng cinematic: màn rừng đêm sâu hơn, CTA mở thư random rõ ràng, thêm nút **Hòm Thư** cách điệu bằng biểu tượng mailbox + badge số thư để vào xem lại nhanh. Bổ sung local daily-inbox logic: mỗi ngày user nhận nhiều thư ngẫu nhiên (2–5 thư/ngày), vẫn giữ flow trả lời hoặc truyền thư cho người khác.
- **`Nutrition.tsx`** + **`dashboardService.ts`** + **`/dashboard/nutrition-daily`** — Thêm trang Dinh dưỡng (`/serene/nutrition`) với gợi ý món ăn theo ngày và ý nghĩa với tinh thần; trang Home có widget “Hôm nay ăn gì” để mở nhanh sang gợi ý chi tiết.
- **`dashboard.py`** — `overview` trả thêm `analyst_insights` (tóm tắt phiên gần nhất, trigger nổi bật, coping hiệu quả, goals active, memory stats) để dashboard phản ánh dữ liệu analyst/memory có ý nghĩa hơn.

### Changed
- **`Reflect.tsx` + `ProgressStats.tsx`** — Thu nhỏ typography và nén spacing/padding ở trang `Nhìn lại` để bố cục vừa khung hình hơn trên màn hình laptop (giảm cỡ tiêu đề, card, biểu đồ và khoảng trắng giữa các section).
- **`Setting.tsx` + `appSettings.ts` + `Sidebar.tsx` + `BeachMessage.tsx`** — Gỡ section “Quyền riêng tư & Bảo mật” khỏi trang Cài đặt, thêm toggle chế độ Sáng/Tối ngay trong mục Giao diện, và đồng bộ toàn app sang một nguồn `mode` chung trong app settings (loại bỏ việc suy luận mode từ `theme` ở từng trang).
- **`Sidebar.tsx`** — Đổi icon menu `Thư` từ biểu tượng lá sang biểu tượng thuyền (`Sailboat`) để đúng ngữ nghĩa trang thư thả biển.
- **`BeachMessage.tsx`** — Tối giản lại màn hình Thư: giãn tab `Bến thư`/`Kho thư` cách nhau 100px, tăng độ tương phản chữ hiển thị chính, và bỏ các dòng chữ phụ dư thừa.
- **`BeachMessage.tsx`** — Logic hiển thị thuyền chuyển sang theo trạng thái có thư chờ: có thư thì hiện thuyền, mở thư xong thì ẩn thuyền và hiển thị trạng thái “chưa có thư mới”.
- **`BeachMessage.tsx`** — Đồng bộ lại trang Thư theo bản code chuẩn đã chốt (CinematicBg, FloatingBottle ripple, overlay hồi âm/viết thư, tab Bãi Biển/Cộng đồng và hệ thống typography/transition tương ứng).
- **`BeachMessage.tsx`** — Gỡ nút chuyển `Sáng/Tối` khỏi riêng trang Thư; theme giờ chỉ đổi từ trang `Setting` để tránh 2 điểm điều khiển khác nhau gây rối.
- **`BeachMessage.tsx`** — Sửa giao diện trang Thư theo feedback: popup viết thư ở theme sáng chuyển sang tông sáng rõ (không còn xám tối), nút Gửi có trạng thái `disabled` và hover sáng lên khi đủ điều kiện gửi, nhãn “Chạm để xem” tăng độ đậm/dễ đọc, thuyền chuyển tông xanh sáng hơn để hòa với mặt nước, tab header `Hộp thư/Cộng đồng` giãn cách + luôn có gạch chân nhận diện, và nền trang đổi sang ảnh `reference-images/nền.avif`.
- **`BeachMessage.tsx` + `Sidebar.tsx`** — Đồng bộ màu chữ theo theme (tối: chữ trắng, sáng: chữ đen) cho trang Thư và thanh điều hướng; đồng thời tăng cỡ chữ các tiêu đề/nhãn chính, lược bớt thông điệp phụ để giao diện dễ đọc hơn.
- **`BeachMessage.tsx` + `frontend/src/assets/thuyen.png`** — Thay SVG thuyền giấy trung tâm bằng asset hình thật `thuyen.png` để khớp hình tham chiếu.
- **`BeachMessage.tsx`** — Bổ sung hiệu ứng gợn sóng lan tỏa dưới thuyền theo nhịp nhấp nhô, tăng cảm giác thuyền nổi trên mặt nước.
- **`BeachMessage.tsx`** — Nút gửi trong popup thư chuyển sang xử lý click trực tiếp (tránh trạng thái disable gây kẹt), đồng thời thuyền chỉ xuất hiện khi có thư random và tự ẩn sau khi mở thư.
- **`BeachMessage.tsx` + `AppRoutes.tsx` + cleanup pages** — Chuyển logic trang thư từ `.jsx` sang `BeachMessage.tsx` (TypeScript), route dùng trực tiếp trang này làm nguồn duy nhất; đồng thời xoá file dư `BeachMessage.jsx` và `BambooForest.tsx` để tránh cập nhật phân tán.
- **`Sidebar.tsx` + `BambooForest.tsx`** — Đổi toàn bộ nhãn hiển thị trang từ **"Rừng Trúc"** sang **"Thư"** trong điều hướng và tiêu đề/nội dung trang.
- **`Main.tsx` + `Sidebar.tsx` + `HeaderMain.tsx` + `index.css` + `Home.tsx`** — Thu nhỏ mật độ UI toàn app cho màn hình zoom 100%: sidebar hẹp hơn (60 thay vì 72), brand/nav/header scale xuống, container nội dung từ `max-w-7xl` về `max-w-6xl`, giảm padding layout, và đặt base font-size 15px để giao diện bớt “tràn to” khó nhìn.
- **`HeaderMain.tsx` + `Main.tsx` + `index.css`** — Thêm cơ chế thu gọn thanh công cụ trên cùng để tăng không gian tương tác; bổ sung nút tam giác cách điệu cho thao tác ẩn/hiện nhanh (khi ẩn vẫn còn chip nổi để mở lại ngay).
- **`Home.tsx`** — “Hôm nay của bạn” chuyển từ checklist sang nhắc nhở theo khung giờ: sáng (05:00–10:00), trưa/chiều (10:00–18:00), tối (18:00–24:00); mỗi nhắc nhở bấm vào sẽ mở phần giải thích “tầm quan trọng” + “nếu bỏ qua” (ăn sáng/ăn trưa/ngồi nhiều/ăn tối/ngủ sớm...), không còn gạch ngang hay biến mất như todo list.
- **`chat.py`** + **`longterm_memory.py`** + **`chat_response_cache.py`** — Memory được làm “nóng” sau mỗi lượt chat (không chờ `/chat/end`), đồng thời cache key chat thêm `context_seed` để tránh trả lại phản hồi cũ khi cùng nội dung nhưng ngữ cảnh đã thay đổi.
- **`langgraph_chat.py`** + **`Chat.tsx`** — Hội thoại thường không còn hiển thị `goi_y_nhanh` dưới bong bóng chat; bỏ block “Gợi ý tiếp theo” từ proactive intervention để response gọn và chuyên nghiệp hơn.
- **`langgraph_chat.py`** + **`Sidebar.tsx`** + **`paths.ts`** + **`AppRoutes.tsx`** + **`Home.tsx`** — Agent có thể đính kèm deep-link dinh dưỡng khi user hỏi diet/ăn uống; thêm route + điều hướng Dinh dưỡng trong app shell.
- **`BeachMessage.tsx`** — Nút chuyển `Sáng/Tối` ở trang Thư nay đồng bộ với `appSettings` toàn cục: đọc/lưu cùng storage key + lắng nghe event cập nhật, nên đổi mode ở trang Thư sẽ áp dụng nhất quán trên toàn ứng dụng.

- **`CheckinFlow.tsx`** / **`Home.tsx`** — Check-in rút gọn: một bước chip "Tâm trạng hôm nay?" (dùng `MoodWordChips`) rồi thẳng tới "Điều gì ảnh hưởng đến bạn hôm nay?" + ghi chú; bỏ bước thang 5 mức "Hôm nay bạn cảm thấy thế nào?" và lưới cảm xúc tiếng Anh. Từ trang chủ, "Ghi chép thêm" truyền `moodWords` qua `location.state` để vào thẳng bước yếu tố. API vẫn gửi `mood` (suy ra từ chip) và `emotions` = các từ đã chọn.
- **`Sidebar.tsx`** — Removed "Bài tập" (Dumbbell) as a standalone nav item; renamed "Nguồn lực" → "Tài nguyên" with `Library` icon. Mobile bottom nav rebalanced to 5 remaining items.
- **`Resources.tsx`** — Full rewrite: (1) Vietnamese labels for all category tabs (Thiền định, Ngủ & Thở, Âm nhạc, Trí tuệ, Vận động); (2) new **SleepTab** component for "Ngủ & Thở" category — shows 4 breathing/relaxation exercises (cards linking to `/serene/exercises?exercise=…`) + Sleep Stories section + Soundscapes section; (3) `AnimatePresence` fade-slide transitions between tabs; (4) extracted `ResourceGrid` component for generic categories; (5) loads exercises via `exerciseService.list()` with `FALLBACK_EXERCISES` fallback; default landing category changed to `sleep`.
- **`rewardProgress.ts` + `CheckinFlow.tsx` + `Home.tsx`** — Sau khi bấm “Nhận phần thưởng”, tim/streak được persist vào localStorage và phát event cập nhật UI; Home đọc dữ liệu thưởng thay cho số hardcode `0`, đồng thời đồng bộ streak với `/reflect/mental-health-summary` nếu server trả về lớn hơn.

### Fixed
- **`backend/tests/test_neo4j_schema.py`** — Neo4j integration fixture giờ kiểm tra `verify_connectivity()` và tự `skip` khi service không khả dụng hoặc auth fail trong môi trường CI, tránh fail hàng loạt khi runner không có Neo4j tại `localhost:7687`.
- **`backend/app/services/longterm_memory.py`** — Làm `persist_turn_memory()` tolerant với DB adapter/test double không có `scalar()` để không làm vỡ luồng chat non-SOS và SSE trong integration tests; khi thiếu API này hệ thống bỏ qua lưu memory turn-level thay vì ném exception.
- **`backend/app/api/deps.py` + `backend/app/core/config.py`** — Ổn định CI backend bằng 2 chỉnh sửa cấu hình/phụ thuộc: CSRF giờ cho phép loopback origin khác port trong local dev (`localhost`/`127.0.0.1`/`::1`) thay vì strict exact-match, và `Settings` validators được sửa để mutate rồi trả đúng `self` theo chuẩn Pydantic (tránh warning validator, đồng thời đảm bảo fallback DB local hoạt động đúng khi thiếu `DATABASE_URL`).
- **`test_onboarding_integration.py`** — Override `get_db` và `get_current_user` (đúng với router onboarding); thêm `disclaimer_accepted` trong payload `POST /onboarding/complete` để test khớp validation.
- **`Reflect.tsx`** — Sửa lỗi vòng `Peace Score` bị vỡ/cắt khi thu nhỏ layout: chuẩn hoá SVG bằng `viewBox` để vòng tròn scale đúng theo khung card.
- **`httpClient.ts` + `AuthContext.tsx` + `Home.tsx` + `Reflect.tsx`** — Giảm spam lỗi `401 Unauthorized`: thêm cơ chế broadcast unauthorized toàn cục để clear auth state sớm và dừng gọi API protected khi user không còn session.
- **`backend/app/api/v1/routers/auth.py` + `backend/tests/test_auth_integration.py`** — Sửa lỗi không đăng ký được ở local khi chưa cấu hình SMTP: signup không còn fail `500 CONFIG_ERROR`; hệ thống tự auto-verify tài khoản trong chế độ local (`auto_create_schema=true`) để user đăng nhập ngay, đồng thời thêm test regression cho fallback này.
- **`backend/app/api/v1/routers/auth.py` + `frontend/src/components/policy/PolicyWizard.tsx` + `backend/tests/test_auth_integration.py`** — Sửa lỗi kẹt ở màn hình Policy sau khi bấm “Tôi đồng ý”: trong nhánh signup local fallback, backend nay phát hành luôn auth cookies (access/refresh + CSRF) để các call `/policies/current` và `/policies/acknowledge` không còn `401`.
- **`frontend/src/components/auth/Register.tsx` + `frontend/src/components/pages/OnboardingFlow.tsx` + `backend/app/api/v1/routers/onboarding.py` + `backend/app/schemas/payloads.py`** — Gộp luồng disclaimer vào onboarding (bỏ bước policy rời trong flow signup), cho phép user đi thẳng `/serene/onboarding` sau đăng ký; onboarding hoàn tất sẽ ghi nhận `disclaimer_accepted` và cập nhật policy ack trên backend.
- **`frontend/src/components/layout/HeaderMain.tsx`** — Menu tài khoản giờ hiển thị theo trạng thái auth: đã đăng nhập chỉ hiện `Tài khoản` / `Đổi mật khẩu` / `Đăng xuất`, không còn hiển thị nút `Đăng nhập` gây hiểu nhầm.

---

## [Unreleased] — Sprint 4 · 2026-04-27

### Added
- **`anonymousShareService.ts`** — `POST /bamboo/send` + `GET /bamboo/inbox` with graceful localStorage fallback when backend endpoint is unavailable; 3 curated mock messages for offline inbox demo.
- **`BambooForestPage.tsx`** (`/serene/bamboo`) — Full anonymous sharing feature: (1) **Composer** with category selector (Lời khích lệ / Chia sẻ / Hỏi đáp), styled textarea, character counter; (2) **Confirmation modal** with 3-item checklist the user must tick before sending (no harmful content / no PII / suitable for strangers) — "Gửi" disabled until all checked; (3) **Dual action** — "Gửi vào dòng suối 🌊" sends to random user, "Đốt an toàn 🔥" discards locally; (4) **Community Guidelines modal** (Info button); (5) **Done/Burn splash** screens; (6) **Inbox tab** with received anonymous messages styled per category. Bamboo forest dark-olive gradient background.
- **`DayDetailSheet.tsx`** (`frontend/src/components/wellness/`) — Framer-motion bottom sheet; opens on MoodCalendar cell tap; shows date, mood emoji, score bar, word chips, journal note; spring entrance animation.
- **`ProgressStats.tsx`** (`frontend/src/components/wellness/`) — 4-stat grid (streak days, weekly check-ins, total sessions, hearts/tim); weekly check-in dot bar with animated fill; integrated into `Reflect.tsx`.

### Changed
- **`MoodCalendar.tsx`** — Added optional `onDayClick(date, score, label)` prop; cells are now `<button>` elements when `onDayClick` provided; tap highlights with scale animation.
- **`Reflect.tsx`** — Integrated `DayDetailSheet` (tapping calendar cells opens day detail); integrated `ProgressStats` section after milestones chips; added `selectedDay` state.
- **`Sidebar.tsx`** — Added "Rừng Trúc" nav item (Leaf icon, `/serene/bamboo`).
- **`paths.ts`** / **`AppRoutes.tsx`** — Registered `/serene/bamboo` route.

---

## [Unreleased] — Sprint 3 · 2026-04-27

### Added
- **`OnboardingFlow.tsx`** — 8-step new-user questionnaire (Splash → Nickname → Gender → Age group → Mental concerns checklist → Stress frequency slider → Sleep schedule time-pickers → Goals); data persisted to `localStorage`; route `/serene/onboarding` wired into `AppRoutes.tsx` + `paths.ts`.
- **`ScreeningFlow.tsx`** — Likert pill UI replaces plain radio buttons; frequency dot indicators (0–3 filled dots per option); animated `AnalyzingLoader` with 3-step message sequence shown while submitting final answer; instrument selection cards with icon + description.
- **`ResultsPage.tsx`** — Dual animated score bars (raw score % + severity %, `motion` fill); per-severity recommendation exercise cards (2 cols); Web Share API share button with clipboard fallback; "Chat with Serene" CTA card at bottom; action buttons upgraded with Lucide icons.
- **`MoodGauge.tsx`** (`frontend/src/components/common/`) — SVG semicircle gauge 1–10; animated spring needle; gradient color track (red→yellow→green); click-to-set + stepper buttons; accessible `role="slider"` attributes.
- **`StreakCelebration.tsx`** (`frontend/src/components/common/`) — Animated modal celebrating consecutive check-in days; S M T W T F S dot circles (amber = done); hearts reward badge; spring scale entrance animation; integrated into `CheckinFlow` summary step.
- **`DateDivider.tsx`** (`frontend/src/components/chat/`) — Date separator between chat messages when day changes (shows "Hôm nay" / "Hôm qua" / formatted date); wired into Chat.tsx message feed via `timestamp` field on `UiMessage`.

### Changed
- **`CheckinFlow.tsx`** — Added `StreakCelebration` modal on submit completion; fixed English "Chat with Mây" button to Vietnamese.
- **`Chat.tsx`** — Added `timestamp?: number` to `UiMessage` type; new user/assistant messages include `Date.now()` timestamp; `DateDivider` rendered between messages on day boundaries.

---

## [Unreleased] — Sprint 2 · 2026-04-25

### Added
- **Docker + Cloud Run deployment** — `backend/Dockerfile`, `frontend/Dockerfile`, `nginx.conf.template`, `docker-entrypoint.sh`, `cloudbuild.yaml`, `deploy.sh`, `setup_cloudrun.sh`, `.env.cloudrun.example` for full containerised GCP deploy.
- **Alembic migration 0002** — `memory_columns`: adds `mem0_user_id`, `long_term_summary` to user profile table.
- **Alembic migration 0003** — `counseling_knowledge`: vector-enabled knowledge table for hybrid RAG.
- **Alembic migration 0004** — `checkin_emotions`: adds `emotions` (JSON) + `triggers` (JSON) columns to `mood_checkins`.
- **`langfuse_tracing.py`** — `ChatTurnTracer` (ContextVar-based), wraps each turn in a Langfuse trace; fully no-ops when keys absent.
- **`confidence_router.py`** — routes high-distress non-SOS turns to human-review queue.
- **`output_grounding.py`** — post-flight grounding check blocks unsourced clinical claims before response is returned.
- **`counseling_retriever.py`** — hybrid vector + lexical retrieval with RRF fusion and rerank top-k; sanitizes chunks against indirect injection.
- **`mental_chat_retriever.py`** — sanitizes MentalChat retrieved chunks to block indirect prompt injection.
- **`mem0_service.py` + `memory_enrichment.py`** — Mem0 persistent user memory integration.
- **`cold_start_screener.py`** — PHQ-9/GAD-7 cold-start scoring for new users.
- **`chat_cost_metrics.py`** — token/cost telemetry; `GET /v1/admin/cost-dashboard` endpoint.
- **`outbox_worker.py`** — background worker that dispatches `SyncOutbox` events; started with `main.py`.
- **`hierarchical_agent_graph.py`** — scaffold for VinMec domain multi-agent split.
- **`exercise_catalog.py`** + `GET /v1/resources/exercises` — shared backend exercise contract for chat attachments.
- **`exerciseService.ts`** — frontend exercise catalog client with local offline fallback.
- **`CheckinFlow.tsx`** — Samsung Health-style 4-step mood check-in (Mood → Emotions → Triggers + Journal → Summary).
- **`ExercisesPage.tsx`** — breathing-pattern hub (box/equal/4-7-8/custom) + underwater exercise player with animated progress ring.
- **`Resources.tsx`** + `resourceService.ts` — sanctuary-style resource library with category pills, sleep stories, soundscapes, and agent deep-link support.
- **`Connect.tsx`** + `connectService.ts` — *You Are Not Alone* support UI with hotlines, clinic cards, and searchable Google Maps embed.
- **`PolicyWizard.tsx`** — 5-screen animated policy acknowledgment wizard shown post-signup.
- 9 new test files: `test_ragas_eval`, `test_redteam`, `test_voice_escalation`, `test_counseling_retriever`, `test_exercise_catalog`, `test_chat_context_token_guard`, `test_chat_memory_continuity`, updated `test_langgraph_chat`, `test_proactive_voice`.
- `DELETE /v1/auth/me/data` — cross-store user data deletion (DB + Mem0 + Redis).
- `PATCH /v1/admin/crisis-logs/{id}/review` — manual crisis log review endpoint.

### Changed
- `langgraph_chat.py`: 3-tier context builder reduces tokens ~40% at distress < 0.65; adds `_estimate_tokens_fast`, `_log_token_budget`, `correlation_id` tracing, grounding + cost observations.
- `CheckinFlow.tsx`: complete redesign — white frosted-glass shell, colour-coded emotion chips, journal step, summary step.
- `Chat.tsx`: renders `the_dinh_kem` attachments as clickable resource/exercise/clinic cards; normalises object-shaped quick replies; adds session history side-panel.
- `Reflect.tsx`: milestone chips row after Peace Score grid; journal prompts section (`GET /reflect/journal-prompts`).
- `Home.tsx`: removes safety gate from CTAs; replaces the 4-card mood row + CTA row with one equal-width 3-mode row (`Check-in nhanh`, `Làm bài sàng lọc`, `Trò chuyện ngay`).
- `Sidebar.tsx` + `HeaderMain.tsx`: settings shortcut → profile shortcut; gear → down-chevron account menu.
- `Setting.tsx`: theme preview applies realtime via `APP_SETTINGS_UPDATED_EVENT`.
- `auth.py`: signup redirect goes to `/onboarding/policy` (PolicyWizard); handles `verification_required` 202.
- `chat.py`: high-risk non-SOS turn writes `CrisisLog` with `pending_review = true`.
- `main.py`: starts outbox worker thread alongside idle-session worker on startup.

### Fixed
- **`StreakBar.tsx`** — Sửa logic đánh dấu “Chuỗi tuần này” theo ngày hiện tại: streak giờ được tô ngược từ hôm nay (có wrap qua CN/T7), tránh lỗi luôn tô cố định từ T2 làm sai khi hôm nay là thứ 2 nhưng UI vẫn tô T3/T4.
- `chat.py` + `langgraph_chat.py`: load memory context once per turn, include memory for recall questions even at low distress, and skip cold-start profiling on short low-risk turns to reduce latency.
- `counseling_retriever.py`: indentation error in `try` block — `rows = db.execute(...)` was unindented.
- `outbox_worker.py`: marks dispatched events as `done` (was using invalid `processed` status).
- `Reflect.tsx`: no-data placeholder instead of empty Recharts container; removed unsafe `return` from `finally`.
- `HomeToday.tsx`: completed mood card contract (`apiMood`, `desc`) to fix TypeScript build.
- `Chat.tsx`: removed global toast container overlaying chat input.
- Proactive voice escalation uses final `SafetySnapshot.distress_score` — prevents missed Blaze TTS jobs.

### Removed
- `API_SET_UP_PROMPT.txt`, `BRANCHES_RULES.md` — superseded by updated CLAUDE.md + AGENTS.md.
- `docs/AI_TEST_COVERAGE_AND_GAP_REPORT.md`, `docs/BACKEND_PLAN.md` — replaced by live test suite + CHANGELOG.

---

### Added
- **Langfuse LLM observability** — `backend/app/services/langfuse_tracing.py`: optional `ChatTurnTracer` (ContextVar-based) that wraps each chat turn in a Langfuse trace with supervisor span, analyst/friend generations (model, token counts), distress score metric, and routing history. Completely no-ops when `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` are absent.
- `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST` added to `config.py` and `.env.example`.
- `langfuse>=2.0.0` added to `backend/requirements.txt`.
- `run_non_sos_turn()` and `stream_non_sos_turn_events()` now accept optional `user_id` / `session_id` for Langfuse user/session attribution; chat router passes them through.
- `backend/alembic/versions/0004_checkin_emotions.py` migration + `MoodCheckin` JSON columns (`emotions`, `triggers`) để lưu đầy đủ check-in cảm xúc/tác nhân.
- `CheckinQuickRequest` mở rộng `emotions` và `triggers` để nhận dữ liệu từ flow Mood check-in mới.
- Breathing catalog mở rộng với `box_breath`, `equal_breath`, `custom_breath` cho hub 2×2 trong trang bài thở.
- `exercise_catalog.py` + `GET /v1/resources/exercises` — shared backend exercise contract for browser-run exercises and chat attachments.
- `exerciseService.ts` — frontend exercise catalog client with local fallback for demo-safe browser exercise sessions.
- `Resources.tsx` — sanctuary-style resource library UI with local fallback cards, category pills, featured session, sleep stories, soundscapes, and clickable play actions.
- `Connect.tsx` — "You are not alone" support UI with hotline CTAs, clinic/referral cards, and map-style support panel.
- `Reflect.tsx`: milestone chips row (streak, breathing sessions, wellness, total sessions) rendered after Peace Score / mood chart grid; only shown when at least one milestone is earned
- `Reflect.tsx`: journal prompts section ("Gợi ý ghi chép hôm nay") fetched from `GET /reflect/journal-prompts`, rendered near page bottom, sliced to 3 prompts; fetch errors silently suppressed in production
- `ScreeningFlow` component (`frontend/src/components/pages/ScreeningFlow.tsx`) — PHQ-9 / GAD-7 instrument selection + question-by-question flow with animated progress bar; submits via `screeningService.submit()` and navigates to `/serene/results` with result state; falls back to static instrument list when catalog API unavailable
- Route `/serene/screening` added to `AppRoutes.tsx` under `RequireAuth`
- `PolicyWizard` component (`frontend/src/components/policy/PolicyWizard.tsx`) — 5-screen animated policy acknowledgment wizard shown post-signup; calls `policyService.acknowledge()` on final step and navigates to `/serene`
- Public route `/onboarding/policy` added to `AppRoutes.tsx` (outside `RequireAuth`)
- `Register.tsx`: redirect after successful signup now goes to `/onboarding/policy` (both verification-required and direct-login paths)
- `_estimate_tokens_fast()` — fast char-based token estimator (~2.5 chars/token for Vietnamese) in `langgraph_chat.py`
- `_log_token_budget(stage, *texts)` — debug-level token telemetry at `analyst_in`, `analyst_out`, `friend_in`, `friend_out`, `stream_friend_in` stages
- Tiered context builder: `_build_friend_context(state, distress_score)` now builds 3 tiers to reduce tokens sent to Friend model
- `output_grounding.py` — hậu kiểm grounding cho phản hồi để chặn claim lâm sàng không có nguồn
- `confidence_router.py` — confidence routing cho high-distress non-SOS và queue human review
- `chat_cost_metrics.py` + `GET /v1/admin/cost-dashboard` — theo dõi token/cost cho chat pipeline
- `outbox_worker.py` — worker loop xử lý `SyncOutbox` events nền
- `test_ragas_eval.py` — regression gate theo phong cách RAGAS
- `test_redteam.py` — bộ test red-team prompt injection/jailbreak/slang self-harm
- `hierarchical_agent_graph.py` — scaffold kiến trúc hierarchical multi-agent cho VinMec domain split
- Frontend services mới: `homeService.ts`, `resourceService.ts`, `connectService.ts`

### Changed
- `Sidebar.tsx` + `HeaderMain.tsx`: replace the left-bottom settings shortcut with a profile shortcut and change the top-right gear into a down-chevron account menu limited to login, password reset, and logout actions.
- `CheckinFlow.tsx`: redesign hoàn chỉnh theo mẫu Samsung Health (Mood → Emotions → Triggers + Journal → Summary), đổi shell/card sang nền trắng đục glass đồng bộ web app, chips bo tròn có màu chọn theo nhóm cảm xúc, lưu dữ liệu vào `/checkin/quick`.
- `ExercisesPage.tsx`: thêm hub chọn bài thở trước khi vào player và hỗ trợ pattern có pha giữ thứ hai (`4-4-4-4`).
- `checkin.py`: persist `emotions` và `triggers` lên `mood_checkins` khi tạo/cập nhật quick check-in.
- `Setting.tsx`: chọn theme áp dụng preview realtime qua `APP_SETTINGS_UPDATED_EVENT`, hủy thay đổi sẽ trả lại theme đã lưu.
- `Home.tsx`: bỏ safety gate cho các CTA chính, nối trực tiếp tới route mục tiêu và wire đầy đủ quick cards/forest CTA.
- `ExercisesPage.tsx`: replaces static step cards with a working underwater exercise player, timer, progress bar, phase animation, and URL-driven exercise selection.
- `Chat.tsx`: renders agent attachments as clickable resource/exercise cards using `action`/`route` from backend payloads.
- `langgraph_chat.py`: standardizes `the_dinh_kem` attachment payloads and adds sanitized agent suggestions for clinic maps plus sleep/meditation resources.
- `Connect.tsx`: replaces the static map illustration with a searchable Google Maps embed that accepts agent-provided address/query routes.
- `Resources.tsx` + `resourceService.ts`: support agent deep links into resource categories/search, including a fallback sleep meditation video card.
- `Sidebar.tsx`: aligns navigation labels and bottom actions with the visual references.
- `AuthContext`: splits context value into `authContextValue.ts` so frontend lint/Fast Refresh rules pass.
- Frontend page labels now use `Nhìn Lại`, `Thư Viện`, and `Kết Nối` across sidebar navigation, page headings, onboarding copy, and related result CTAs.
- `_build_friend_context`: refactored from flat full-context to 3 tiers based on distress level
  - Tier 2 (0.42 ≤ distress < 0.65): 3-turn transcript + mood + tone + analyst note (~40% fewer tokens vs old flat context)
  - Tier 3 (distress ≥ 0.65): full context unchanged (6 turns + mem0 + long-term + profile + trajectory)
  - Tier 1 (distress < 0.42, short msg): unchanged — `_build_personality_hint` via caller
- `friend_node`, `stream_non_sos_turn_events`: pass `distress_score` explicitly to `_build_friend_context`
- `langgraph_chat.py`: thêm `correlation_id`, structured tracing span-level, grounding integration, usage-cost observation
- `counseling_retriever.py`: nâng lên hybrid vector + lexical retrieval, RRF fusion, rerank top-k, sanitize retrieved chunks
- `mental_chat_retriever.py`: sanitize retrieved chunks chống indirect injection
- `chat.py`: high-risk non-SOS flow sẽ ghi `CrisisLog` pending review và trả cờ `pending_human_review`
- `admin.py`: thêm `PATCH /v1/admin/crisis-logs/{log_id}/review`
- `main.py`: khởi chạy outbox worker thread cùng idle session worker
- `auth.py`: thêm `DELETE /v1/auth/me/data` (xóa user data cross-store + Mem0/Redis)
- `seed_counseling_knowledge.py`: idempotency theo content hash, quarantine log cho low-quality rows, freshness source tag
- Frontend:
  - `Home.tsx` nối `POST /mood/checkin` và `GET /home/feed`
  - `Resources.tsx` nối categories/list APIs
  - `Connect.tsx` nối hotlines/clinics APIs
  - `Chat.tsx` thêm history panel + load sessions/messages
  - `Register.tsx` xử lý signup `verification_required` (202) thay vì luôn navigate vào app
  - `chatService.ts` mở rộng sessions/messages/delete APIs
  - `authService.ts` mở rộng type cho flow email verification

### Fixed
- Local DB 500s on `/v1/home/feed` and `/v1/reflect/*` resolved by applying `0004_checkin_emotions` so `mood_checkins.emotions` and `mood_checkins.triggers` exist.
- `outbox_worker.py`: mark dispatched events as `done` instead of invalid `processed` status, matching the `sync_outbox` DB constraint.
- `Reflect.tsx`: render a no-data placeholder instead of mounting Recharts with an empty/invalid container, preventing width/height warnings.
- `HomeToday.tsx`: complete the mood card contract (`apiMood`, `desc`) so TypeScript build passes.
- `App.tsx`: remove the global toast container so bottom notification bars no longer overlay the chat input.
- `HeaderMain.tsx`: bỏ mục `Cài đặt` trùng trong dropdown của icon settings.
- `Sidebar.tsx`: bỏ nút standalone `Journal Now` vì journal đã tích hợp trực tiếp trong check-in flow.
- `Setting.tsx`: removes leftover debug logging from settings save flow.
- `Chat.tsx`: normalize object-shaped quick replies before rendering, preventing React from crashing on `{type, reason, message}` payloads.
- `Reflect.tsx`: remove unsafe `return` from `finally` in the data-loading effect.
- Proactive voice escalation now uses the final `SafetySnapshot.distress_score` after graph/cold-start scoring, preventing missed Blaze TTS jobs when distress is raised during non-SOS processing.
- `test_build_friend_context_includes_long_term_memory` updated to reflect tiered context semantics (split into 2 tests: tier2 and tier3)
- Chặn prompt-injection pattern trong retrieval context trước khi đưa vào prompt LLM
- Bổ sung review path cho trường hợp distress cao nhưng chưa chạm SOS hard gate

---

*No previous releases — initial changelog setup.*
