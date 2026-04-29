# Frontend Plan — Brief đầy đủ 

## Thông tin dự án

- **Stack**: React.js + FastAPI + LangGraph + PostgreSQL + pgvector.
- **Ngày cập nhật**: 2026-04-16.
- **Phiên bản tài liệu**: 2.0 — viết lại từ đầu theo luồng trải nghiệm và hệ “nhân vật” user-facing.

---

## 1. Mục đích tài liệu

Tài liệu này là **brief frontend** để đội UI/UX và dev web/app triển khai màn hình, copy, trạng thái luồng và ràng buộc an toàn. Nó bám **hành trình người dùng** (trial → chào → an toàn → nhu cầu → kết quả → bước tiếp theo → dashboard), không chỉ liệt kê tab.

---

## 2. Nguyên tắc đặt tên: backend vs user-facing

### 2.1 Backend / tài liệu kỹ thuật

Giữ **thuật ngữ kiến trúc** khi nói về hệ thống: Supervisor, Analyst, guardrail input/output, schema state, batch job, KPI, v.v. Các layer này **không** cần xuất hiện trong copy cho người dùng cuối.

### 2.2 User-facing — “nhân vật” đời thường (ví dụ đội agents)

Đề xuất map trải nghiệm sang tên gần gũi (có thể tinh chỉnh theo brand cuối cùng):

| Tên   | Vai trò trong app (user-facing) |
|-------|-----------------------------------|
| **An**   | Người chào đón và **check-in** (mood, năng lượng ngày, câu hỏi ngắn). |
| **Mây**  | Người **lắng nghe và trò chuyện** (chat hỗ trợ ngắn, tóm tắt nhẹ nhàng). |
| **Lửa**  | Người giúp **ổn định nhanh** bằng **bài tập ngắn** (thở, grounding, chuyển hướng cảm xúc). |
| **La Bàn** | Người **chỉ đường** tới counselor / nguồn hỗ trợ phù hợp (hotline, map, referral). |
| **Gương** | Người cho xem **tiến triển và dashboard cá nhân** (xu hướng mood, lịch sử, nhắc quay lại). |

**Ghi chú triển khai UI:** Một màn có thể “do An dẫn” nhưng vẫn gọi API nội bộ giống nhau; tên chỉ để **giảm cảm giác lâm sàn** và tăng tính đồng hành.

---

## 3. Luồng tổng thể web/app (khả thi, ưu tiên cảm giác “vào được ngay”)

### 3.1 Vào nhanh — dùng thử trước khi đăng ký

- Người dùng **mở app/web vào nhanh**, **không bắt đăng ký ngay**.
- **Dùng thử có giới hạn** (ví dụ ~1 phút hoặc N lượt hành động / một nhánh ngắn — chi tiết business rule do sản phẩm chốt): đủ để cảm nhận **An / Mây / Lửa** một lần.
- Sau trial: CTA rõ ràng **“Lưu lại hành trình” / “Tạo tài khoản”** để đồng bộ dashboard (**Gương**) và nhận nhắc nhở.

**Frontend cần:** trạng thái `guest_session`, banner đếm thời gian/lượt, không làm gián đoạn cảm xúc bằng form dài.

### 3.2 Màn chào đầu tiên (sau khi vào app)

**Headline gợi ý:** *“Hôm nay bạn muốn gì?”*

Ba lựa chọn chính (CTA lớn, ngôn ngữ đời thường):

1. **Check-in nhanh** (An dẫn).
2. **Làm bài sàng lọc** (bài ngắn — copy không cần nhắc mã thang đo; kết quả hiển thị dễ hiểu).
3. **Trò chuyện ngay** (Mây).

### 3.3 Bước bắt buộc sau mọi lựa chọn — kiểm tra an toàn ngắn

Ngay sau khi chọn (1)(2)(3), luôn qua **3 câu kiểu có/không** (UI đơn giản: Không / Có hoặc thang mức rất thấp):

- *“Bạn có đang thấy quá tải?”*
- *“Bạn có thấy không an toàn?”*
- *“Bạn có cần hỗ trợ ngay không?”*

**Nhánh A — Có dấu hiệu nguy cơ**

- Chuyển sang **Safety / crisis flow** (xem mục 6 — **không** ưu tiên “chặn full màn hình đỏ” như trải nghiệm duy nhất).
- Hiện **hướng dẫn khẩn cấp** + **hotline** + gợi ý **counselor / người tin cậy** (La Bàn).
- **Đánh dấu follow-up ưu tiên** (backend: cờ + lịch nhắc; Gương: thẻ “đang được quan tâm”).
- Kết thúc luồng khẩn: copy an toàn, không ép tiếp tục check-in thường.

**Nhánh B — Không có dấu hiệu nguy cơ**

- Đi tiếp **đúng luồng** theo nhu cầu ban đầu (mục 4).

---

## 4. Ba luồng nhu cầu (chi tiết UX)

### 4.1 [1] Check-in nhanh — An

1. Hỏi **mood hôm nay** (từ vựng phi lâm sàn, icon + mô tả nhẹ).
2. Hỏi nhanh **căng thẳng / ngủ / học tập** (slider hoặc 3–5 mức).
3. Cho **một dòng ghi chú** (optional).
4. **Tổng hợp ngắn** (1 khối text + 2–3 bullet “mình thấy gì” — không chẩn đoán).
5. Chuyển sang **gợi ý bước tiếp theo** (mục 5).

### 4.2 [2] Làm bài sàng lọc

1. Chọn **chủ đề** phù hợp: stress / lo âu / mood (nhãn thân thiện).
2. Làm **bài test ngắn** (UI tiến độ rõ, có nút “nghỉ một chút”).
3. Hệ thống **tính điểm + phân mức** (backend giữ logic thang đo; UI chỉ hiển thị **mức dễ hiểu**).
4. Màn **kết quả dễ hiểu** (mục 5) + luôn có **bước tiếp theo**.

### 4.3 [3] Trò chuyện ngay — Mây

1. Vào **chat hỗ trợ ngắn** (tone đồng hành).
2. **Nếu** trong chat xuất hiện dấu hiệu nguy cơ → **chuyển ngay** sang Safety / crisis flow (mục 6).
3. **Nếu không** nguy cơ:
   - **Tóm tắt vấn đề chính** (ngắn, do Mây “đọc lại cho bạn nghe”).
   - Gợi ý **check-in** hoặc **sàng lọc** nếu phù hợp (không áp đặt).
   - Chuyển sang **gợi ý bước tiếp theo** (mục 5).

---

## 5. Kết quả dễ hiểu & bước tiếp theo (theo mức)

### 5.1 Nguyên tắc copy

- Giải thích **ngắn gọn**, tránh ngôn ngữ **quá lâm sàn**.
- **Luôn** có khối **“Bước tiếp theo”** (1 hành động chính + 1 phụ).
- Mọi thứ quan trọng **lưu vào dashboard cá nhân** (**Gương**) khi user đã đăng nhập hoặc sau khi đồng ý lưu guest → account.

### 5.2 Gợi ý theo mức (ví dụ định hướng sản phẩm)

| Mức (user-facing) | Gợi ý UI / hành động |
|-------------------|----------------------|
| **Nhẹ** | Gợi ý **một bài tập ngắn** (Lửa) · nhắc **check-in ngày mai** (An) · lưu **Gương**. |
| **Trung bình** | Gợi ý **chat ngắn** (Mây) · **kế hoạch 24h** (checklist nhẹ, không “kế hoạch điều trị”) · hẹn **check-in lại** · lưu **Gương**. |
| **Cao hoặc kéo dài** | **Referral** qua La Bàn (counselor / chuyên gia / nguồn phù hợp) · **follow-up ưu tiên** · lưu **Gương**. |

---

## 6. Safety / crisis — thiết kế lại trải nghiệm (đặc biệt trong chat)

### 6.1 Mục tiêu

- Vẫn **ưu tiên an toàn tuyệt đối** (hotline, tài nguyên khẩn, referral).
- **Tránh** cảm giác “bị chặn màn hình bởi SOS guardrail” như trải nghiệm duy nhất khi AI phát hiện nguy cơ tự hại.

### 6.2 Hành vi đề xuất trong chat (khi có nguy cơ tự hại)

- **Mây** chuyển giọng **chậm lại, ngắn câu, khuyên nhỏ** (de-escalation), **không** tranh luận hay phủ nhận cảm xúc.
- **Đồng thời** hiển thị **khối hotline / nút gọi / chat hỗ trợ** luôn thấy trên màn hình (sticky bar hoặc card song song), không ẩn sau nhiều bước.
- Có thể **giảm nội dung gây kích thích** (ít animation, nền dịu) nhưng **không** cần “full screen đen” bắt buộc nếu đã có layer an toàn + La Bàn rõ ràng.
- Sau khi ổn định: đề xuất **La Bàn** (nguồn hỗ trợ) và **ghi nhận follow-up** (ưu tiên trong Gương cho nhân sự phù hợp nếu có mô hình B2B).

### 6.3 Crisis flow sau check-in / sàng lọc

- Giữ logic: **có nguy cơ → ưu tiên an toàn**, nhưng UI có thể là **wizard ngắn** + hotline + grounding (Lửa) tùy ngữ cảnh.

---

## 7. Dashboard cá nhân — Gương

**Mục đích:** nhìn lại mà không bị “bệnh án hóa”.

- **Mood trend** (đường/heatmap đơn giản).
- **Lịch sử check-in** (thẻ theo ngày, có thể mở rộng).
- **Nhắc quay lại** (tùy chỉnh trong Settings).
- **Tiến triển theo thời gian** (milestone phi ngôn ngữ lâm sàn: “ổn hơn tuần trước”, “hay dùng thở hơn”, v.v. — do backend tổng hợp, copy do persona thân thiện).

---

## 8. Auth, đăng ký và xác nhận chính sách (bắt buộc sau khi có tài khoản)

### 8.1 Đăng ký

- Form tối giản (email, mật khẩu, tên hiển thị) — tham chiếu mockup hiện có.

### 8.2 Sau đăng ký — luồng xác nhận policy (bắt buộc)

Người dùng **phải** đi qua bước xác nhận rằng:

- **An, Mây, Lửa, La Bàn, Gương** (và AI phía sau) chỉ **hỗ trợ / tham vấn thông tin**, **không** thay thế chuyên gia.
- Trong khủng hoảng: **ưu tiên đường dây nóng và dịch vụ thật**.
- Dữ liệu và quyền riêng tư (tóm tắt có link chi tiết).

**Frontend:** không skip; có thể nhiều bước swipe/card; nút xác nhận rõ ràng + timestamp lưu server.

---

## 9. Ánh xạ màn hình hiện có (mockup) sang luồng mới

Các ảnh trong `docs/frontend_pics/` vẫn là **tham chiếu visual**; copy và information architecture cần **cập nhật** theo mục 2–8.

| Mockup (gợi ý) | Vai trò trong plan 2.0 |
|------------------|------------------------|
| `01–04` Landing | Giới thiệu sản phẩm + CTA “Vào thử ngay” / Đăng nhập. |
| `06–08` Login / Signup | Auth; disclaimer signup có thể rút gọn nếu policy flow sau đăng ký đã đủ mạnh (tránh trùng lặp mệt mỏi — chốt với pháp lý). |
| `09` Onboarding disclaimer | Gộp hoặc đồng bộ với **mục 8.2** (sau đăng ký). |
| `10` Mood / Home | Một phần của **An** + cổng tới **Gương**. |
| `11` Reflect summary | **Gương** (dashboard cá nhân). |
| `12` Chat | **Mây** + vùng **La Bàn** (hotline) luôn sẵn khi cần. |
| `13` SOS | Tái định nghĩa: **tình huống khẩn** + song song **Mây/Lửa/La Bàn**, không chỉ một layout “chặn”. |
| `14–16, 20, 22` Resources | Thư viện nội dung; gắn **Lửa** và teaser **La Bàn**. |
| `17` Connect | **La Bàn**. |
| `05, 18` Breath | **Lửa**. |
| `15` Settings | Tùy chọn + nhắc nhở + quyền riêng tư. |
| `19` Admin B2B | Giữ **thuật ngữ kỹ thuật** (Supervisor, Analyst, SOS metrics…) — không đổi tên persona cho admin. |
| `21` Reflections CBT | Có thể thuộc **Gương** (nhìn lại insight) với ngôn ngữ đời thường. |

---

## 10. Điều hướng app (IA đề xuất)

Sau khi user đã qua policy:

- **Hôm nay** (màn chào + 3 lựa chọn — có thể là home mặc định).
- **Mây** (chat).
- **Lửa** (bài tập ngắn).
- **La Bàn** (kết nối hỗ trợ).
- **Gương** (tiến triển).
- **Cài đặt**

Sidebar hoặc bottom nav tùy breakpoint; **guest** thấy subset + CTA đăng ký.

---

## 11. Ràng buộc kỹ thuật & KPI (giữ liên hệ hệ thống)

- **Latency chat:** phản hồi cảm nhận được (< ~3s) khi có thể.
- **Safety recall:** khi phát hiện nguy cơ, **chuyển luồng + hiển thị hotline** không được trễ hoặc bị che.
- **Trial:** giới hạn rõ ràng phía server; client hiển thị trung thực.
- **Lưu dữ liệu nhạy cảm:** tuân schema/backend; PII và B2B aggregate theo policy dự án.

---

## 12. Kết luận

Bản plan 2.0 đặt **luồng cảm xúc và an toàn** ở trung tâm: vào nhanh → chọn nhu cầu → **kiểm tra an toàn** → nhánh phù hợp → **kết quả dễ hiểu** + **bước tiếp theo** → **Gương**. Người dùng thấy **An, Mây, Lửa, La Bàn, Gương**; dev và admin vẫn làm việc với **agent/graph/schema** như tài liệu kỹ thuật.

*Tài liệu này thay thế cấu trúc “chỉ mô tả từng tab” của phiên bản 1.0; phần mockup chi tiết từng ảnh có thể bổ sung lại dưới dạng subsection khi copy UI được cập nhật theo persona mới.*

## 13. MVP triển khai Thư ẩn danh

### 13.1 Mục tiêu

- Giữ cảm giác “thả thư ra biển” như hiện tại, nhưng chuyển phần gửi/nhận sang backend thật.
- Không làm mất chất chill: user vẫn có thể viết nhanh, nhận thư ngẫu nhiên, đọc lại và hồi âm.
- Ẩn danh ở mức sản phẩm, nhưng vẫn phải có khả năng kiểm duyệt, rate limit và chống spam.

### 13.2 Phạm vi MVP

MVP chỉ cần 4 hành vi:

1. Viết và gửi thư ẩn danh.
2. Nhận một lá thư từ cộng đồng/inbox.
3. Đọc thư và hồi âm ẩn danh.
4. Lưu lịch sử thư đã gửi của chính user.

Không làm trong MVP:

- Follow/friend graph.
- Chat realtime giữa hai user.
- Hộp thư theo chủ đề quá sâu.
- Rich media, file đính kèm, voice note.

Phạm vi truy cập:

- Chỉ user đã đăng nhập mới được dùng Thư.
- Guest không được gửi, nhận, hay lưu kho thư để tránh abuse và giữ dữ liệu đồng bộ.

### 13.3 User flow đề xuất

1. User vào tab Thư.
2. Màn bến thư cho thấy một lá thư đang chờ hoặc trạng thái trống.
3. User bấm “Viết lá thư của bạn”.
4. User nhập nội dung, chọn tâm trạng hoặc chủ đề nhẹ nếu cần.
5. User bấm gửi.
6. Backend nhận thư, lưu trạng thái, và có thể đưa vào pool nhận thư sau khi qua kiểm duyệt.
7. Khi user mở thư cộng đồng, hệ thống trả về một lá thư phù hợp để đọc.
8. User có thể hồi âm, và hồi âm này cũng đi vào hàng chờ moderation như một thư mới.

### 13.4 API tối thiểu

Nên thiết kế một nhóm endpoint riêng cho bến thư, thay vì nhét chung vào chat:

- `POST /v1/bamboo/send`.
- `GET /v1/bamboo/inbox`.
- `POST /v1/bamboo/reply`.
- `POST /v1/bamboo/pass`.
- `GET /v1/bamboo/storage`.

### 13.5 Data model tối thiểu

Một lá thư nên có các trường cơ bản sau:

- `message_id`.
- `user_id` hoặc `guest_id` nội bộ.
- `content`.
- `category` hoặc `tone`.
- `direction` là `sent`, `received`, hoặc `reply`.
- `status` là `pending`, `approved`, `rejected`, `archived`.
- `created_at`, `updated_at`.
- `moderation_reason` nếu bị từ chối.
- `pass_count` nếu thư được chuyền tiếp.

### 13.6 Quy tắc sản phẩm

- Ẩn danh với người dùng khác, nhưng backend vẫn giữ trace nội bộ để chống abuse.
- Không hiển thị định danh thật trong UI.
- Nội dung bị kiểm duyệt cần bị loại khỏi inbox công cộng, nhưng vẫn giữ log nội bộ.
- Có giới hạn tần suất gửi theo user/IP.
- Có giới hạn độ dài nội dung và bộ lọc từ khóa nhạy cảm.
- Chủ đề/tone nên là metadata nhẹ, tùy chọn khi gửi, không bắt user điền form dài.
- Dùng chủ đề để gợi ý inbox, lọc moderation và tránh feed quá ngẫu nhiên.

### 13.7 UI state cần có trên FE

- `empty`: chưa có thư.
- `bottle_waiting`: có thư đang chờ mở.
- `writing`: đang nhập thư.
- `sending`: đang gửi.
- `sent`: đã thả thư ra biển.
- `reading`: đang đọc thư cộng đồng.
- `replying`: đang hồi âm.
- `error`: gửi thất bại, có thể thử lại.

### 13.8 Mapping từ code hiện tại

- [BeachMessage.tsx](../frontend/src/components/pages/BeachMessage.tsx) đã có shell UI và animation tốt, nên giữ lại layout này.
- [anonymousShareService.ts](../frontend/src/services/anonymousShareService.ts) hiện là lớp mock/fallback, có thể thay bằng adapter gọi API thật.
- [ROUTE_PATHS.bamboo](../frontend/src/routes/paths.ts) và route trong [AppRoutes.tsx](../frontend/src/routes/AppRoutes.tsx) giữ nguyên.
- [Main.tsx](../frontend/src/components/layout/Main.tsx) đang special-case full bleed cho trang Thư, nên tiếp tục giữ.

### 13.9 Kế hoạch triển khai theo phase

Phase 1:

- Giữ UI hiện tại.
- Đổi service sang API thật.
- Lưu thư đã gửi và thư nhận được.

Phase 2:

- Thêm moderation queue.
- Thêm pass-on và reply chuẩn hóa.
- Thêm thống kê nhẹ như số thư đã gửi, số thư đã nhận.

Phase 3:

- Gợi ý thư theo mood.
- Ghép với nội dung từ chat/reflect nếu sản phẩm muốn đồng bộ hành trình.
- Tinh chỉnh feed để thư cộng đồng không bị lặp và không quá “random”.

### 13.10 Quyết định mở còn treo

Trước khi code, team cần chốt 3 câu:

1. Thư ẩn danh: chỉ user đã đăng nhập.
2. Chủ đề/tone: có, nhưng là metadata nhẹ và optional, không phải form bắt buộc.
3. Moderation: hybrid, nghĩa là sync filter nhẹ ở lúc gửi và async queue cho kiểm duyệt chính.
