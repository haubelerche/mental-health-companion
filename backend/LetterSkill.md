# 📘 FEATURE — Gửi Thư Ẩn Danh (Anonymous Letter)

---

## 1. 🎯 Khái Niệm (Concepts)

### 1.1. Letter (Thư)
- Thư là một tin nhắn **bất biến** được gửi từ một người dùng đến một người dùng khác một cách ngẫu nhiên
- Mỗi thư có:
  - `letter_id`: Mã định danh duy nhất
  - `sender_id`: Người gửi (được che giấu khỏi người nhận)
  - `content`: Nội dung thư
  - `forward_count`: Số lần được chuyển tiếp (0-3)
  - `has_reply`: Đã có phản hồi hay chưa
  - `is_reported`: Đã bị báo cáo hay chưa
  - `created_at`: Thời gian tạo

### 1.2. LetterFlow (Lịch Sử Thư)
- Là một **append-only log** ghi lại mọi hành động liên quan đến thư
- Mỗi flow bao gồm:
  - `flow_id`: Mã định danh duy nhất
  - `letter_id`: Thư liên quan
  - `from_user_id`: Người thực hiện hành động
  - `to_user_id`: Người nhận thư/thao tác
  - `action`: Loại hành động (`sent`, `forwarded`, `replied`)
  - `created_at`: Thời gian hành động

**Quy tắc quan trọng**: Flow **không bao giờ bị cập nhật**, chỉ có thể thêm mới. Người nhận hiện tại là `to_user_id` của flow mới nhất với action là `sent` hoặc `forwarded`.

### 1.3. LetterReply (Phản Hồi)
- Mỗi thư chỉ có thể nhận **một phản hồi** từ người nhận cuối cùng
- Phản hồi bao gồm:
  - `reply_id`: Mã định danh duy nhất
  - `letter_id`: Thư được phản hồi
  - `replier_id`: Người phản hồi
  - `anonymous_name`: Tên ẩn danh của người phản hồi (hiển thị cho người gửi)
  - `content`: Nội dung phản hồi
  - `created_at`: Thời gian phản hồi

### 1.4. LetterReaction (Phản Ứng)
- Chỉ **người gửi** thư mới có thể phản ứng với phản hồi
- Mỗi người chỉ có thể **phản ứng một lần** trên một phản hồi
- Bao gồm:
  - `reaction_id`: Mã định danh duy nhất
  - `reply_id`: Phản hồi được phản ứng
  - `user_id`: Người phản ứng (luôn là sender)
  - `reaction_type`: Loại phản ứng (ví dụ: `❤️`, `😊`, etc.)

### 1.5. Report (Báo Cáo)
- Cả người gửi và người nhận đều có thể báo cáo một thư
- Báo cáo bao gồm:
  - `report_id`: Mã định danh duy nhất
  - `reporter_id`: Người báo cáo
  - `letter_id`: Thư bị báo cáo
  - `reason`: Lý do báo cáo
  - `created_at`: Thời gian báo cáo

---

## 2. 🔄 Luồng Hoạt Động (Workflow)

### 2.1. Gửi Thư (Send)
1. Người dùng viết nội dung thư
2. Hệ thống chọn ngẫu nhiên một người nhận (không phải chính người gửi)
3. Thư được lưu với `forward_count = 0`, `has_reply = False`
4. Một flow với action `sent` được tạo để ghi lại sự kiện

**Giới hạn**: Mỗi người dùng có thể gửi tối đa **5 thư/ngày**

### 2.2. Nhận Thư (Inbox)
1. Người nhận thấy thư trong **Bến thư (Beach Inbox)**
2. Chỉ hiển thị thư từ flow mới nhất (nếu action là `sent` hoặc `forwarded`)
3. Thư sẽ **không** hiển thị nếu:
   - Người xem là người gửi
   - Người xem đã phản hồi thư (thư biến mất sau khi phản hồi)
   - Người xem không phải là receiver của flow mới nhất

**Giới hạn**: Mỗi người dùng có thể nhận tối đa **5 thư/ngày**

### 2.3. Chuyển Tiếp Thư (Forward)
1. Người nhận có thể chọn chuyển tiếp thư đến người khác
2. `forward_count` tăng lên 1
3. Một flow mới với action `forwarded` được tạo
4. Người nhận cũ **không** còn thấy thư trong inbox

**Giới hạn**: Thư chỉ có thể được chuyển tiếp tối đa **3 lần**

### 2.4. Phản Hồi Thư (Reply)
1. Chỉ **người nhận cuối cùng** (từ flow mới nhất) mới có thể phản hồi
2. Phản hồi chỉ có thể được tạo **một lần** trên một thư
3. Phản hồi được giữ **ẩn danh** (tên ẩn danh do người phản hồi cung cấp)
4. Người gửi gốc nhận được thông báo rằng thư đã được phản hồi
5. Người phản hồi thấy phản hồi của mình trong **Kho thư (Archive)** - mục "Thư bạn đã phản hồi"
6. Thư **biến mất** khỏi inbox của người phản hồi

### 2.5. Phản Ứng với Phản Hồi (React)
1. Chỉ **người gửi gốc** có thể phản ứng với phản hồi
2. Phản ứng được lưu với `reaction_type` (ví dụ: `❤️`)
3. Người phản hồi có thể thấy phản ứng của người gửi
4. Mỗi người chỉ có thể phản ứng **một lần** trên một phản hồi

### 2.6. Báo Cáo Thư (Report)
1. Cả người gửi và người nhận (receiver của flow mới nhất) đều có thể báo cáo
2. Khi báo cáo:
   - `letter.is_reported = True`
   - Người gửi gốc nhận được thông báo
   - Thư được đánh dấu để quản trị viên xem xét

### 2.7. Kho Thư (Archive)
Người dùng có thể xem **Kho thư** gồm hai phần:

**A. Thư bạn đã gửi (Sent Letters)**
- Danh sách tất cả thư mà người dùng đã gửi
- Hiển thị:
  - Nội dung thư
  - Số lần chuyển tiếp
  - Trạng thái: "Có hồi âm" + tên ẩn danh của người phản hồi (nếu có)
  - Phản ứng của người gửi với phản hồi (nếu có)
  - Trạng thái: "Đã bị báo cáo" (nếu có)

**B. Thư bạn đã phản hồi (Reply Archive)**
- Danh sách tất cả phản hồi mà người dùng đã tạo
- Hiển thị:
  - Tên ẩn danh của người dùng
  - Nội dung phản hồi
  - Nội dung thư gốc
  - Phản ứng của người gửi gốc (nếu có)

---

## 3. 🌐 API Endpoints

### 3.1. POST /v1/letters — Gửi Thư

**Mô tả**: Gửi một thư đến một người nhận ngẫu nhiên

**Request**:
```json
{
  "content": "Nội dung thư của bạn"
}
```

**Response (200 OK)**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "letter_id": "ltr_abc123",
    "sender_id": "usr_001",
    "receiver_id": "usr_002",
    "content": "Nội dung thư của bạn",
    "forward_count": 0,
    "has_reply": false,
    "is_reported": false,
    "created_at": "2026-05-01T10:30:00"
  }
}
```

**Lỗi có thể xảy ra**:
- `400 - DAILY_LIMIT_EXCEEDED`: Đã gửi tối đa 5 thư hôm nay
- `400 - NO_ELIGIBLE_RECEIVERS`: Không có người nhận hợp lệ

---

### 3.2. GET /v1/letters/inbox — Lấy Danh Sách Thư Trong Bến Thư

**Mô tả**: Lấy danh sách thư trong inbox (chỉ những thư chưa phản hồi)

**Request**: Không có body

**Response (200 OK)**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "inbox": [
      {
        "id": "ltr_abc123",
        "content": "Nội dung thư nhận được",
        "sender_id": null,
        "received_at": "2026-05-01T10:30:00",
        "forward_count": 1,
        "has_reply": false,
        "is_reported": false
      }
    ],
    "total": 1
  }
}
```

**Quy tắc**:
- Chỉ hiển thị thư từ flow mới nhất
- Không hiển thị nếu người xem là sender
- Không hiển thị nếu đã được phản hồi
- Không hiển thị nếu người xem đã chuyển tiếp

---

### 3.3. GET /v1/letters/sent — Lấy Kho Thư

**Mô tả**: Lấy danh sách thư đã gửi + danh sách phản hồi đã tạo

**Request**: Không có body

**Response (200 OK)**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "letters": [
      {
        "id": "ltr_abc123",
        "content": "Thư tôi đã gửi",
        "sent_at": "2026-05-01T09:00:00",
        "forward_count": 2,
        "has_reply": true,
        "is_reported": false,
        "reply": {
          "reply_id": "rep_xyz789",
          "content": "Phản hồi từ người nhận",
          "replier_id": null,
          "received_at": "2026-05-01T10:30:00",
          "anonymous_name": "Bạn lạ",
          "reaction_type": "❤️",
          "has_reaction": true
        }
      }
    ],
    "reply_letters": [
      {
        "reply_id": "rep_def456",
        "letter_id": "ltr_parent789",
        "content": "Phản hồi của tôi",
        "anonymous_name": "Tôi",
        "original_content": "Thư gốc từ người gửi",
        "sent_at": "2026-05-01T11:00:00",
        "reaction_type": "😊",
        "has_reaction": true
      }
    ],
    "total_sent": 1,
    "total_replied": 1
  }
}
```

---

### 3.4. POST /v1/letters/{id}/forward — Chuyển Tiếp Thư

**Mô tả**: Chuyển tiếp thư đến người nhận khác

**Request**: Không có body

**Response (200 OK)**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "letter_id": "ltr_abc123",
    "new_receiver_id": "usr_003",
    "forward_count": 1,
    "forwarded_at": "2026-05-01T11:30:00"
  }
}
```

**Lỗi có thể xảy ra**:
- `404 - LETTER_NOT_FOUND`: Thư không tồn tại
- `403 - NOT_RECEIVER`: Người dùng không phải là receiver hiện tại
- `400 - FORWARD_LIMIT_REACHED`: Thư đã được chuyển tiếp 3 lần
- `400 - NO_ELIGIBLE_RECEIVERS`: Không có người nhận hợp lệ

---

### 3.5. POST /v1/letters/{id}/reply — Phản Hồi Thư

**Mô tả**: Tạo phản hồi cho một thư

**Request**:
```json
{
  "content": "Nội dung phản hồi của tôi"
}
```

**Response (200 OK)**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "reply_id": "rep_xyz789",
    "letter_id": "ltr_abc123",
    "replier_id": "usr_002",
    "content": "Nội dung phản hồi của tôi",
    "anonymous_name": "Bạn lạ",
    "created_at": "2026-05-01T12:00:00"
  }
}
```

**Lỗi có thể xảy ra**:
- `404 - LETTER_NOT_FOUND`: Thư không tồn tại
- `403 - NOT_RECEIVER`: Người dùng không phải là receiver hiện tại
- `400 - ALREADY_REPLIED`: Thư đã có phản hồi

---

### 3.6. POST /v1/replies/{id}/react — Phản Ứng với Phản Hồi

**Mô tả**: Người gửi phản ứng với một phản hồi

**Request**:
```json
{
  "reaction_type": "❤️"
}
```

**Response (200 OK)**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "reaction_id": "rxn_abc123",
    "reply_id": "rep_xyz789",
    "user_id": "usr_001",
    "reaction_type": "❤️",
    "created_at": "2026-05-01T12:30:00"
  }
}
```

**Lỗi có thể xảy ra**:
- `404 - REPLY_NOT_FOUND`: Phản hồi không tồn tại
- `403 - NOT_SENDER`: Chỉ người gửi mới có thể phản ứng
- `400 - ALREADY_REACTED`: Đã phản ứng trước đó (có thể cập nhật)

---

### 3.7. POST /v1/reports — Báo Cáo Thư

**Mô tả**: Báo cáo một thư vi phạm

**Request**:
```json
{
  "letter_id": "ltr_abc123",
  "reason": "Nội dung gây chói tai"
}
```

**Response (200 OK)**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "report_id": "rpt_abc123",
    "letter_id": "ltr_abc123",
    "reporter_id": "usr_002",
    "reason": "Nội dung gây chói tai",
    "created_at": "2026-05-01T13:00:00"
  }
}
```

**Lỗi có thể xảy ra**:
- `404 - LETTER_NOT_FOUND`: Thư không tồn tại
- `403 - NOT_AUTHORIZED`: Không phải sender hoặc receiver
- `400 - ALREADY_REPORTED`: Đã báo cáo trước đó

---

## 4. 📋 Quy Tắc Kinh Doanh (Business Rules)

### 4.1. Giới Hạn Hàng Ngày
| Hành động | Giới hạn |
|-----------|----------|
| Gửi thư | 5 thư/ngày |
| Nhận thư | 5 thư/ngày |
| Chuyển tiếp | 3 lần tối đa trên mỗi thư |
| Phản hồi | 1 lần trên mỗi thư |
| Phản ứng | 1 lần trên mỗi phản hồi |

### 4.2. Quy Tắc Hiển Thị
- **Bến thư (Inbox)**: Chỉ hiển thị thư từ flow mới nhất, không hiển thị thư của chính người dùng
- **Kho thư (Archive)**: Hiển thị cả thư đã gửi và phản hồi đã tạo
- **Phản hồi**: Luôn ẩn danh, chỉ hiển thị tên ẩn danh do người phản hồi cung cấp

### 4.3. Quy Tắc Chuyển Tiếp
- Chỉ người nhận cuối cùng mới có thể chuyển tiếp
- Sau khi chuyển tiếp, người nhận cũ không thấy thư trong inbox
- Thư không thể được chuyển tiếp nếu đã bị phản hồi

### 4.4. Quy Tắc Phản Hồi
- Chỉ người nhận cuối cùng mới có thể phản hồi
- Mỗi thư chỉ có một phản hồi
- Phản hồi không thể bị xóa hoặc chỉnh sửa

### 4.5. Quy Tắc Phản Ứng
- Chỉ người gửi gốc mới có thể phản ứng
- Mỗi người chỉ phản ứng một lần trên một phản hồi
- Có thể cập nhật phản ứng đã tạo

### 4.6. Quy Tắc Báo Cáo
- Cả người gửi và người nhận (flow mới nhất) đều có thể báo cáo
- Báo cáo đánh dấu thư với flag `is_reported = True`
- Người gửi gốc nhận được thông báo

---

## 5. 📊 Mô Hình Dữ Liệu (Data Model)

### 5.1. Bảng `letters`
```sql
CREATE TABLE letters (
  letter_id VARCHAR(50) PRIMARY KEY,
  sender_id VARCHAR(50) NOT NULL REFERENCES users(user_id),
  content TEXT NOT NULL,
  forward_count INTEGER DEFAULT 0,
  has_reply BOOLEAN DEFAULT FALSE,
  is_reported BOOLEAN DEFAULT FALSE,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 5.2. Bảng `letter_flows`
```sql
CREATE TABLE letter_flows (
  flow_id VARCHAR(50) PRIMARY KEY,
  letter_id VARCHAR(50) NOT NULL REFERENCES letters(letter_id),
  from_user_id VARCHAR(50) REFERENCES users(user_id),
  to_user_id VARCHAR(50) NOT NULL REFERENCES users(user_id),
  action VARCHAR(20) NOT NULL, -- 'sent', 'forwarded', 'replied'
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_letter_flow_letter (letter_id)
);
```

### 5.3. Bảng `letter_replies`
```sql
CREATE TABLE letter_replies (
  reply_id VARCHAR(50) PRIMARY KEY,
  letter_id VARCHAR(50) NOT NULL UNIQUE REFERENCES letters(letter_id),
  replier_id VARCHAR(50) NOT NULL REFERENCES users(user_id),
  anonymous_name VARCHAR(100),
  content TEXT NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 5.4. Bảng `letter_reactions`
```sql
CREATE TABLE letter_reactions (
  reaction_id VARCHAR(50) PRIMARY KEY,
  reply_id VARCHAR(50) NOT NULL REFERENCES letter_replies(reply_id),
  user_id VARCHAR(50) NOT NULL REFERENCES users(user_id),
  reaction_type VARCHAR(20),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (reply_id, user_id)
);
```

### 5.5. Bảng `reports`
```sql
CREATE TABLE reports (
  report_id VARCHAR(50) PRIMARY KEY,
  reporter_id VARCHAR(50) NOT NULL REFERENCES users(user_id),
  letter_id VARCHAR(50) NOT NULL REFERENCES letters(letter_id),
  reason TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## 6. 🔔 Thông Báo (Notifications)

Khi một sự kiện xảy ra, một entry được tạo trong bảng `sync_outbox` để thông báo cho người dùng:

| Sự kiện | Người nhận | Loại sự kiện | Dữ liệu |
|--------|-----------|--------------|---------|
| Nhận thư | Receiver | `letter.received` | `letter_id`, `sender_id` |
| Phản hồi | Sender | `letter.replied` | `letter_id`, `reply_id`, `replier_id` |
| Báo cáo | Sender | `letter.reported` | `letter_id`, `report_id`, `reporter_id` |

---

## 7. 🛠️ Lưu Ý Kỹ Thuật

### 7.1. Append-Only Pattern
- `LetterFlow` luôn được **thêm mới**, không bao giờ bị cập nhật
- Để biết người nhận hiện tại, truy vấn flow mới nhất với action `sent` hoặc `forwarded`
- Điều này đảm bảo tính toàn vẹn của dữ liệu và tạo ra một audit trail hoàn chỉnh

### 7.2. Chọn Receiver
- Chọn ngẫu nhiên từ danh sách người dùng **chưa** nhận thư này
- Loại trừ: người gửi gốc, những người đã nhận thư, những người vượt quá giới hạn nhận 5 thư/ngày
- Sử dụng `random.choice()` để đảm bảo phân phối đều đặn

### 7.3. Latest Flow Query
- Để kiểm tra quyền hạn và hiển thị, luôn sử dụng flow mới nhất:
```python
latest_flow = db.query(LetterFlow).filter(
    LetterFlow.letter_id == letter_id
).order_by(LetterFlow.created_at.desc(), LetterFlow.flow_id.desc()).first()
```

### 7.4. Lọc Inbox
- Inbox chỉ hiển thị thư mà người xem là `to_user_id` của flow mới nhất
- Loại trừ thư có `has_reply = True` (đã phản hồi, thư biến mất)
- Loại trừ thư mà `sender_id` là chính người xem (người gửi không thấy thư của mình)

---

## 8. ✅ Tình Trạng Triển Khai

- ✅ Backend API đầy đủ (7 endpoints)
- ✅ Frontend UI (Bến thư + Kho thư)
- ✅ Production Postgres schema đã được kiểm tra
- ✅ Integration tests: 5 tests, tất cả passing
- ✅ Notification queuing (SyncOutbox)
