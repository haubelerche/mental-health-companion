# Hệ thống Thư từ (Letter System V2) - Unified Model

Hệ thống đã được tái cấu trúc từ 5 bảng riêng lẻ thành một bảng duy nhất **`TherapyLetter`** (Super Letter Model) để tối ưu hiệu suất và đơn giản hóa việc quản lý.

## 1. Cấu trúc Database (TherapyLetter)

| Trường | Kiểu dữ liệu | Chú thích |
| :--- | :--- | :--- |
| `letter_id` | String(50) | Khóa chính (Prefix: `let_` cho thư, `lrep_` cho phản hồi) |
| `user_id` | String(50) | Người tạo/Người gửi lá thư |
| `receiver_id` | String(50) | Người đang giữ lá thư (chỉ dùng cho `letter_type='public'`) |
| `reply_to_id` | String(50) | ID lá thư gốc (dùng cho luồng Phản hồi) |
| `letter_type` | String(30) | `therapeutic` (cá nhân), `public` (cộng đồng), `reply` (phản hồi) |
| `content` | Text | Nội dung lá thư |
| `anonymous_name`| String(100) | Tên ẩn danh (dành cho người phản hồi) |
| `forward_count` | Integer | Số lần thư được chuyển tiếp (Max: 3) |
| `reaction_type` | String(20) | Cảm xúc (mặc định: `heart`) |
| `status` | String(30) | `active`, `reported`, `deleted`, `pending_review` |
| `report_data` | JSON | Lưu chi tiết báo cáo (người báo cáo, lý do, thời gian) |

## 2. Luồng nghiệp vụ (Business Logic)

### Gửi thư ẩn danh (Social Letter)
- Thư được tạo với `letter_type='public'`.
- Hệ thống tự động tìm một người nhận ngẫu nhiên (`receiver_id`) thỏa mãn điều kiện (Active, đã đồng ý Policy).
- Người nhận sẽ nhận được thông báo thời gian thực qua WebSocket.

### Phản hồi thư (Reply)
- Khi User A phản hồi thư của User B:
  1. Tạo record mới với `letter_type='reply'` và `reply_to_id = let_id`.
  2. Lá thư gốc sẽ được xóa `receiver_id` (để ẩn khỏi Inbox người nhận).
  3. Người gửi gốc (User B) nhận được thông báo có phản hồi mới.

### Chuyển tiếp (Forward/Pass it on)
- Nếu User không muốn trả lời, họ có thể chuyển tiếp.
- `forward_count` tăng lên 1, `receiver_id` được cập nhật sang một người mới ngẫu nhiên.

## 3. Danh sách API endpoints (`/v1/letters`)

### [POST] `/letters`
- **Mô tả**: Gửi một lá thư ẩn danh mới vào cộng đồng.
- **Payload**: `{"content": "..."}`
- **Giới hạn**: 5 thư/ngày.

### [GET] `/letters/inbox`
- **Mô tả**: Lấy danh sách thư người khác gửi đến cho mình (chưa phản hồi).
- **Logic**: Lọc `receiver_id = current_user` và `letter_type = 'public'`.

### [GET] `/letters/sent`
- **Mô tả**: Lấy kho thư cá nhân. Trả về 2 danh sách:
  1. `letters`: Những thư mình đã viết gửi đi (kèm thông tin phản hồi nếu có).
  2. `reply_letters`: Những thư mình đã đi phản hồi cho người khác.

### [POST] `/letters/{id}/reply`
- **Mô tả**: Gửi phản hồi cho một lá thư trong Inbox.

### [POST] `/replies/{id}/react`
- **Mô tả**: Thả cảm xúc (Tim) vào một phản hồi mình nhận được.

### [POST] `/reports`
- **Mô tả**: Báo cáo thư vi phạm (Spam, Abuse, ...). Thông tin báo cáo được gộp vào trường `report_data` dạng JSON.
