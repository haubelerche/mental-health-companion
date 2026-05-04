# Hệ thống Thông báo (Notification System)

Hệ thống thông báo kết hợp giữa truyền tải thời gian thực (WebSocket) và lưu trữ lịch sử (Database).

## 1. Cơ chế hoạt động
1.  **Kích hoạt**: Khi một sự kiện xảy ra (nhận thư, thả tim, SOS...), hệ thống gọi hàm `enqueue_notification`.
2.  **Hàng đợi (Outbox)**: Sự kiện được lưu vào bảng `sync_outbox`.
3.  **Xử lý (Worker)**: `outbox_worker` quét bảng outbox, thực hiện:
    *   Lưu vĩnh viễn vào bảng `user_notifications` (để xem lại ở Tab Thông báo).
    *   Đẩy tín hiệu qua WebSocket cho Client đang kết nối.
4.  **Hiển thị (Frontend)**: 
    *   Nếu đang online: Hiện Toast thông báo.
    *   Mọi lúc: Xem được lịch sử trong trang Thông báo.

### 2. Phân loại Thông báo (Event Types)

Hệ thống hỗ trợ đa dạng các loại sự kiện. **Lưu ý:** Các ràng buộc cứng (Check Constraint) trong Database đã được loại bỏ để hỗ trợ mở rộng linh hoạt các loại thông báo mới mà không cần migration DB.

Các loại thông báo phổ biến:
- `letter.received`: Khi có thư mới gửi đến bạn.
- `letter.replied`: Khi ai đó phản hồi lá thư bạn đã gửi.
- `letter.reacted`: Khi người nhận phản hồi thả tim/cảm xúc cho câu trả lời của bạn.
- `letter.reported`: Khi thư của bạn bị báo cáo vi phạm.
- `system.alert`: Thông báo từ hệ thống.

| Event Type | Payload | Mô tả |
| :--- | :--- | :--- |
| `letter.received` | `{"letter_id": "...", "message": "..."}` | Nhận được thư ẩn danh mới |
| `letter.replied` | `{"letter_id": "...", "reply_id": "..."}` | Có người phản hồi thư của mình |
| `letter.reacted` | `{"reply_id": "...", "reaction_type": "..."}` | Có người thả tim vào phản hồi của mình |
| `heart.received` | `{"amount": 5, "reason": "..."}` | Nhận được Tim từ AI/Hệ thống |
| `memory.unlocked`| `{"memory_id": "...", "persona_name": "..."}` | Mở khóa một ký ức mới |
| `sos.triggered`  | `{"session_id": "...", "risk_level": 5}` | Cảnh báo an toàn (SOS) |

## 3. API Endpoints (`/v1/notifications`)

- `GET /notifications`: Lấy danh sách thông báo (hỗ trợ phân trang `limit`, `offset`).
- `POST /notifications/{id}/read`: Đánh dấu đã đọc một thông báo.
- `POST /notifications/read-all`: Đánh dấu đã đọc tất cả.

## 4. WebSocket Payload (Real-time)
Khi có thông báo mới, WS sẽ gửi một tin nhắn dạng:
```json
{
  "type": "notification",
  "data": {
    "notification_id": "...",
    "title": "...",
    "body": "...",
    "event_type": "...",
    "payload": { ... }
  }
}
```
