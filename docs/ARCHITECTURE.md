# Kiến trúc Hệ thống Multi-Agent Therapist
## Thông tin dự án
- **Tên cụ thể**: Multi-Agent Therapist Sàng Lọc và Hỗ Trợ Sức Khỏe Tinh Thần
- **Stack**: React.js + FastAPI + LangGraph + PostgreSQL + pgvector
- **Ngày**: 2026-04-12
- **Phiên bản**: 1.0

## I. Tổng quan 3 Agent + 1 Safety Guardrail

| **Agent** | **Vai trò Logic** | **Mô hình LLM (Temp)** | **Trách nhiệm** | **Output** |
| --- | --- | --- | --- | --- |
| **Supervisor** | Orchestrator | GPT-4o-mini (0.1) | Phân tích intent, đọc state, route sang agent phù hợp | `QuyetDinhDinhTuyen` |
| **Analyst** | Clinical Reasoning | Menta-4B / GPT-4o-mini (0.0) | Khảo sát PHQ-9/GAD-7 ngầm, phát hiện distortion, chấm điểm | `KetQuaLamSang` |
| **Friend** | Response Generation | GPT-4o (0.7) | Phản hồi thấu cảm Gen Z, gắn thẻ bài tập | `PhanHoiHoiThoai` |

**Safety Guardrail (SOS)** — không phải agent LLM mà là lớp rule-based chạy song song: Input Guardrails (NeMo) → Crisis Detector → Output Guardrails. Khi `muc_do_khung_hoang ≥ 4`, SOS override toàn bộ flow và render thẻ cứu hộ tĩnh.

**Nguyên tắc:** Analyst không bao giờ nói trực tiếp với user — mọi output lâm sàng đều đi qua Friend để giữ tone nhất quán. User chỉ thấy **một nhân vật Serene duy nhất**.

---

## II. Sơ đồ Luồng Hệ thống
![alt text](/docs/images/flowchart.png)

**Mô tả:**

1. Khởi tạo & Xác thực
- Sinh viên → JWT Auth: Người dùng đăng nhập qua JWT token
- → Streamlit UI: Giao diện web cho người dùng tương tác

2. Lớp Gateway & Bảo vệ
- FastAPI Gateway: Điểm vào cho tất cả request
- Input Guardrails: Kiểm soát đầu vào, phát hiện:
    - Prompt injection attacks
    - Từ khóa độc hại (toxic keywords)
    - Dấu hiệu khủng hoảng (crisis keywords)

3. Xử lý trung gian
- Middleware:
    - PII masking (che giấu thông tin cá nhân)
    - Load memory (tải lịch sử hội thoại)
- LangGraph Orchestrator: Quản lý luồng xử lý phức tạp

4. Bộ Supervisor (Cấp độ quyết định)
Sử dụng GPT-4o-mini để định tuyến dựa trên KetQuaLamSangv(tên tích hợp):

    | Loại | Model | Đặc điểm |
    | --- | --- | --- |
    | Distress| Analyst (GPT-4o-mini, PHQ-9, GAD-7) | Phân tích tâm lý chi tiết |
    | Normal chat| Friend (GPT-4o, Empathy Gen Z) | Trò chuyện thân thiện, thấu cảm |
    | Clinical hints| Friend + Output Guardrails | Gợi ý lâm sàng có giám sát |
    | Crisis ≥ 4| SOS Layer (Rule-based) | Kích hoạt quy tắc khẩn cấp |

5. Xử lý khủng hoảng
- SOS Layer: Phản hồi theo quy tắc cứng cho các trường hợp khủng hoảng
- Render static cards: Hiển thị:
    - Đường dây nóng tư vấn
    - Bản đồ phòng khám gần nhất

6. Kiểm soát đầu ra
- Output Guardrails: Kiểm tra:
    - Hallucination (bịa chuyện)
    - Vấn đề đạo đức (ethics)
- → Chat UI + Suggestion cards: Trả lời cho người dùng + gợi ý tiếp theo

7. Lưu trữ & Phân tích
`Chat messages → Crisis Log + Admin review
                      ↓
            PostgreSQL (encrypted)
                      ↓
            Event summary
                      ↓
    B2B Dashboard (Long-term storage)`

## III. Tuần tự Một Lượt Chat
![alt text](/docs/images/sequential_chart.png)

Mô tả:
1. Sinh viên gửi tin nhắn (“Dạo này áp lực quá...”) đến Middleware.
2. Middleware thực hiện tiền xử lý:
    - Ẩn thông tin nhạy cảm (PII Masking)
    - Lấy 8 lượt hội thoại gần nhất từ Memory (DB)
    - Tạo state (message, memory, clinical profile)
    → gửi đến Supervisor.
3. Supervisor phân tích intent (distress) và quyết định gọi Analyst để đánh giá lâm sàng.
4. Supervisor gửi yêu cầu đến Analyst (trigger scoring).
5. Analyst thực hiện:
    - Ánh xạ nội dung vào thang đo PHQ-9
    - Phát hiện các tiêu chí liên quan (ví dụ: mệt mỏi, giảm hứng thú)
    - Tính toán độ phủ (coverage < 70% → chưa đủ dữ liệu)
6. Analyst trả kết quả về Supervisor:
    - mode = hỏi mở (follow-up)
    - gợi ý câu hỏi tiếp theo (ví dụ: giấc ngủ, năng lượng)
7. Supervisor gửi yêu cầu đến Friend, kèm:
    - nội dung người dùng
    - ngữ cảnh hội thoại
    - gợi ý lâm sàng từ Analyst
8. Friend tạo phản hồi:
    - Nội dung đồng cảm, tự nhiên
    - Đặt câu hỏi khai thác thêm
    - Đính kèm gợi ý (ví dụ: bài tập thở 4-7-8)
9. Friend trả kết quả về Supervisor (Phản hồi hội thoại + attachment).
10. Supervisor gửi phản hồi cuối cùng về Middleware.
11. Middleware lưu trữ:
- Lưu lượt hội thoại vào Database
- Cập nhật độ phủ (coverage) của bộ câu hỏi PHQ-9
1. Middleware trả phản hồi cho Sinh viên:
- Hiển thị nội dung hội thoại
- Hiển thị thẻ gợi ý (nếu có)

---

## IV. Sơ đồ Trạng thái
![alt text](/docs/images/state.png)

## Mô Tả 

1. Trạng Thái Khởi Đầu
    * Hệ thống bắt đầu tại trạng thái **Chờ Tin (ChoTin)**, sẵn sàng tiếp nhận tin nhắn từ người dùng.

2. Tiếp Nhận Và Xử Lý Đầu Vào
    * Khi người dùng gửi tin nhắn: **ChoTin** chuyển sang **DangNghe**, hệ thống chuyển sang trạng thái lắng nghe và tiếp nhận dữ liệu.
    * Sau khi Middleware xử lý xong (mask PII, load memory): **DangNghe** chuyển sang **DinhTuyen**, chuyển sang bước định tuyến.

3. Định Tuyến Theo Intent
Tại trạng thái **DinhTuyen**, hệ thống phân loại ý định người dùng và chuyển sang các nhánh xử lý:
    * DinhTuyen chuyển sang **NoiChuyen** nếu intent = greeting (chào hỏi).
    * DinhTuyen chuyển sang **TamSu** nếu intent = tâm sự nhẹ.
    * DinhTuyen chuyển sang **ChamDiem** nếu intent = distress (căng thẳng, tiêu cực).
    * DinhTuyen chuyển sang **SOSFlow** nếu: phát hiện từ khóa nguy hiểm hoặc mức độ khủng hoảng ≥ 4.

4. Xử Lý Hội Thoại Thông Thường
    * Trạng thái NoiChuyen (Chào hỏi):** Hệ thống chỉ sử dụng Friend để tạo phản hồi. **NoiChuyen** chuyển sang **TraLoi**.
    * Trạng thái TamSu (Tâm sự nhẹ):** Friend phản hồi với sự đồng cảm (validation) và duy trì hội thoại. **TamSu** chuyển sang **TraLoi**.

5. Xử Lý Sàng Lọc (Distress)
    * Trạng thái ChamDiem:** Analyst thực hiện đánh giá dựa trên PHQ-9.
    * Nhánh hỏi thêm dữ liệu:** **ChamDiem** chuyển sang **HoiThem** nếu coverage < 70%. Hệ thống cần hỏi tiếp, Friend lồng câu hỏi vào hội thoại thay vì dùng biểu mẫu. **HoiThem** chuyển sang **TraLoi**.
    * Nhánh đánh giá đủ dữ liệu:** **ChamDiem** chuyển sang **DanhGia** nếu coverage ≥ 70%. **DanhGia** chuyển sang **TraLoi** để đưa ra phản hồi đồng cảm, gợi ý hỗ trợ và thẻ tài nguyên.

6. Xử Lý Khủng Hoảng (Crisis Flow)
    * Kích hoạt SOS:** **DinhTuyen** chuyển sang **SOSFlow** khi phát hiện dấu hiệu nguy hiểm hoặc mức độ rủi ro cao.
    * Hiển thị hỗ trợ khẩn cấp:** **SOSFlow** chuyển sang **HienThiCuuHo** để hiển thị hotline hỗ trợ và địa điểm gần nhất.
    * Kết thúc phiên:** **HienThiCuuHo** chuyển sang **KetThucPhien**, sau đó kết thúc luồng.

7. Trả Lời Và Lưu Trữ
    * Trả lời người dùng:** Sau khi xử lý tại các nhánh, hệ thống chuyển về trạng thái TraLoi.
    * Lưu bộ nhớ:** **TraLoi** chuyển sang **LuuBoNho** để lưu trữ nội dung hội thoại và cập nhật trạng thái người dùng.
    * Quay lại trạng thái chờ:** **LuuBoNho** chuyển sang **ChoTin**, hệ thống sẵn sàng cho lượt hội thoại tiếp theo.

## V. Hành trình Sinh viên trong 1 ngày

![alt text](/docs/images/user_journey.png)

1. Giai đoạn buổi sáng – Home
- Sinh viên mở ứng dụng và chọn trạng thái cảm xúc (mood) hiện tại → hệ thống ghi nhận dữ liệu đầu ngày.
- Sinh viên đọc “quote of the day” → giúp tạo động lực và cải thiện tâm trạng.
- Sinh viên thực hiện bài thiền ngắn (5 phút) → hỗ trợ thư giãn và chuẩn bị cho ngày học tập.
→ Giai đoạn này tập trung vào: Khởi tạo trạng thái tinh thần, thu thập dữ liệu nhẹ (mood tracking)

2. Giai đoạn buổi trưa – Chat (trọng tâm hệ thống)
- Sinh viên vào chức năng chat do cảm thấy áp lực → kích hoạt luồng hội thoại hỗ trợ tâm lý.
- Sinh viên chia sẻ về vấn đề (deadline, học tập, stress) → cung cấp dữ liệu đầu vào cho hệ thống.
- Agent Friend phản hồi với giọng điệu thấu cảm
→ giúp sinh viên cảm thấy được lắng nghe và an toàn.
- Agent Analyst thực hiện đánh giá ngầm:
    - Phân tích nội dung hội thoại
    - Ánh xạ vào các tiêu chí củaPHQ-9
- Hệ thống gửi gợi ý hỗ trợ: Ví dụ: thẻ bài tập “thở 4-7-8”
- Sinh viên thực hiện bài tập thở (1 phút) → can thiệp tức thời, giúp giảm căng thẳng.

Giai đoạn này là **core journey**:
- Tương tác người – hệ thống
- Sàng lọc tâm lý
- Đưa ra hỗ trợ kịp thời

3. Giai đoạn buổi tối – Dashboard
- Sinh viên xem biểu đồ xu hướng cảm xúc trong 7 ngày → giúp nhận thức sự thay đổi tâm trạng theo thời gian.
- Sinh viên đọc “weekly note” do hệ thống tổng hợp → cung cấp insight và phản hồi cá nhân hóa.
- Sinh viên viết nhật ký (journal) → hỗ trợ tự phản ánh và giải tỏa cảm xúc.

Giai đoạn này tập trung vào:

- Nhận thức (awareness)
- Tự cải thiện (self-reflection)

4. Các tiến trình chạy ngầm (Background Processes)
- Agent Analyst: Tổng hợp và cập nhật điểm số từPHQ-9
- Hệ thống SOS:
    - Liên tục quét rủi ro (crisis detection)
    - Sẵn sàng kích hoạt luồng khẩn cấp
- Memory:
    - Tóm tắt hội thoại theo từng sự kiện (event-based memory)
    - Lưu trữ và phục vụ cá nhân hóa
- Dashboard hệ thống (B2B): Cập nhật dữ liệu tổng hợp cho quản trị/nhà trường (nếu có)
---

## VI. Schema State

```python
class TrangThaiSerene(BaseModel):
    # Input
    tin_nhan_hien_tai: str
    user_id: str                          # hashed

    # Memory
    bo_nho_lam_viec: list[LuotChat]       # 8 turns gần nhất
    ho_so_lam_sang: HoSoLamSang           # PHQ-9, GAD-7 tích lũy
    lich_su_tam_trang: list[BanGhiMood]

    # Runtime routing
    agent_tiep_theo: Literal["friend", "analyst", "sos", "end"]
    ket_qua_lam_sang: Optional[KetQuaLamSang]
    phan_hoi_friend: Optional[PhanHoiHoiThoai]

    # Control
    do_sau_de_quy: int = 0                # max 3
    muc_do_khung_hoang: int = 0           # 0–5
    the_dinh_kem: list[TheUI] = []
```

### Output schema của mỗi agent

```python
class QuyetDinhDinhTuyen(BaseModel):
    agent: Literal["supervisor"]
    agent_tiep_theo: Literal["friend", "analyst", "sos"]
    ly_do: str
    muc_do_uu_tien: int

class KetQuaLamSang(BaseModel):
    agent: Literal["analyst"]
    mode: Literal["cham_diem", "hoi_mo"]
    diem_phq9: Optional[int] = None       # 0–27
    diem_gad7: Optional[int] = None       # 0–21
    muc_do_khung_hoang: int               # 0–5, LUÔN có
    loi_tu_duy_phat_hien: list[str] = []
    do_bao_phu: dict[str, bool] = {}
    cau_hoi_mo_id: Optional[str] = None
    cau_hoi_mo_text: Optional[str] = None
    hanh_dong_de_xuat: Literal[
        "tiep_tuc_tro_chuyen",
        "hoi_them_cau_mo",
        "goi_y_tai_nguyen",
        "chuyen_sos"
    ]

class PhanHoiHoiThoai(BaseModel):
    agent: Literal["friend"]
    noi_dung_tra_loi: str
    tone_cam_xuc: Literal["ho_tro", "xac_nhan", "vui_tuoi", "lam_diu"]
    goi_y_nhanh: list[str]                # 3 quick replies
    the_dinh_kem: list[TheUI] = []

class HanhDongCuuHo(BaseModel):
    agent: Literal["sos"]
    muc_do: Literal["vua", "cao", "tuc_thoi"]
    hien_hotline: bool
    so_hotline: str = "1800-599-920"
    hien_cap_cuu: bool
    the_cuu_ho: dict
    bai_tap_grounding: Optional[str]
```


- `TrangThaiSerene` là trạng thái trung tâm của hệ thống → lưu toàn bộ thông tin phiên chat, bộ nhớ, dữ liệu lâm sàng và điều phối agent tiếp theo.
- Nhóm Memory (`bo_nho_lam_viec`, `ho_so_lam_sang`, `lich_su_tam_trang`) → giúp hệ thống duy trì ngữ cảnh hội thoại và tích lũy điểm từ các thang đo như PHQ-9 và GAD-7.
- Nhóm Runtime (`agent_tiep_theo`, `ket_qua_lam_sang`, `phan_hoi_friend`) → lưu kết quả xử lý tạm thời của các agent và quyết định luồng tiếp theo.
- `QuyetDinhDinhTuyen` là output của Supervisor → quyết định agent nào sẽ được gọi tiếp theo dựa trên intent và mức độ ưu tiên.
- `KetQuaLamSang` là output của Analyst → chứa điểm số, mức độ khủng hoảng, độ bao phủ câu hỏi và hành động đề xuất (tiếp tục hỏi, gợi ý, hoặc chuyển SOS).
- `PhanHoiHoiThoai` là output của Friend → tạo nội dung trả lời cuối cùng cho người dùng, kèm tone cảm xúc và gợi ý nhanh.
- `HanhDongCuuHo` là output của SOS → xử lý tình huống khẩn cấp (hiển thị hotline, hướng dẫn grounding, hoặc kích hoạt hỗ trợ ngay lập tức).
- Nhóm Control (`do_sau_de_quy`, `muc_do_khung_hoang`, `the_dinh_kem`) → kiểm soát luồng hệ thống, giới hạn vòng lặp và theo dõi mức độ rủi ro.
---

## VII. MVP Gantt

![alt text](/docs/images/gantt.png)


**Critical path:** LangGraph → Supervisor → Friend → Integration → UI → Deploy → Demo
1. Tuần 1 tập trung xây dựng nền tảng hệ thống (LangGraph, state schema, middleware, tích hợp API) để làm cơ sở cho toàn bộ các agent hoạt động.
2. Tuần 1–2 phát triển các agent chính (Supervisor, Friend, Analyst, SOS) và bắt đầu tích hợp orchestration để hình thành luồng xử lý hoàn chỉnh.
3. Tuần 2–3 xây dựng giao diện chat và các thành phần tương tác (quick replies, cards) giúp người dùng trải nghiệm hệ thống.
4. Tuần 3 hoàn thiện độ ổn định với guardrails, logging, lưu trữ dữ liệu và tối ưu hiệu năng.
5. Tuần 4 triển khai hệ thống, kiểm thử nội bộ và chuẩn bị tài liệu demo (kịch bản, video, pitch deck).
---

## VIII. Ánh xạ Tính năng ↔ Agent

| Tính năng UI | Agent tham gia | Cơ chế |
| --- | --- | --- |
| Chat "Always Listening" | Supervisor + Friend + Analyst | Friend trả lời, Analyst chấm điểm ngầm |
| Thẻ "Thở 4-7-8" | Analyst đề xuất → Friend gắn | `hanh_dong_de_xuat = goi_y_tai_nguyen` |
| Quick replies | Friend sinh | Dựa trên `tone_cam_xuc` |
| Mood picker (Home) | Middleware | Ghi thẳng `lich_su_tam_trang`, không gọi LLM |
| Thiền "Bắt đầu tập trung" | — | Static từ Self-help library |
| Biểu đồ xu hướng 7 ngày | Analyst (batch) | Aggregate từ long-term storage |
| "Lời nhắn tuần của Serene" | Analyst + Friend rewrite | Weekly summary, temp 0.4 |
| Gourmnal (journal) | Friend (prompt suggestion) | Lấy từ KB |
| Connect (Hotline + Map) | SOS hoặc user mở tự | Static referral + Folium map |
| Dashboard B2B | Batch job offline | Ẩn danh + aggregate |

---

## IX. Nguyên tắc An toàn Bất biến

1. **SOS không bao giờ bị override.** `muc_do_khung_hoang ≥ 4` → cắt mọi flow, hiện referral + hotline.
2. **PII masking trước khi ghi memory** — luôn luôn, kể cả working memory.
3. **Recursion guard = 3.** Analyst ↔ Friend gọi qua lại quá 3 lần → ép "lắng nghe đơn thuần" + flag admin.
4. **Schema compliance là hard constraint.** Sai schema → retry 1 lần → fallback safe reply.
5. **Analyst không nói trực tiếp với user.** Mọi output đi qua Friend.
6. **SOS = referral, không phải live handoff.** Chỉ hiển thị thông tin, không kết nối counselor online.
7. **Disclaimer bắt buộc khi signup.** User tick "Serene là AI, không thay thế chuyên gia".

---

## X. Chỉ số Giám sát

| Metric | Ngưỡng | Đo |
| --- | --- | --- |
| Latency P50 Friend | ≤ 2s | Log per turn |
| Latency P95 pipeline | ≤ 5s | E2E trace |
| Supervisor routing accuracy | ≥ 92% | 100 test cases |
| Schema compliance | ≥ 99.5% | Parse rate |
| Safety recall (crisis) | ≥ 99% | Red-team |
| Kappa Analyst vs chuyên gia | ≥ 0.85 | 100 samples |
| Session depth ≥ 10 turns | 40% users | Analytics |

---

## XI. Stack Công nghệ
```yaml
backend:
  language: Python 3.11
  framework: FastAPI
  orchestration: LangGraph 0.2+
  llm:
    friend: gpt-4o           # temp 0.7
    supervisor: gpt-4o-mini  # temp 0.1
    analyst: gpt-4o-mini + fewshot        # temp 0.0
  embeddings: text-embedding-3-small
  guardrails: NeMo-Guardrails
  vector_db: pgvector

data:
  db: PostgreSQL
  encryption:
    at_rest: AES-256
    in_transit: TLS 1.3
    pii: Fernet symmetric

frontend:
  ui: ReactJS
  libs: [NextAuth.js,lottie-react,
         react-leaflet,react-router-dom, react-plotly.js]

deploy:
  host: Railway
  services: [web-streamlit, api-fastapi, postgres, cron-batch]
```