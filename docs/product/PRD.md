# PRD.md — Serene.AI Mental-Health Companion

**Document type:** Product Requirements Document + Runtime Architecture Specification  
**Version:** 7.2 — Persona Registry + Deep Screening Refresh  
**Updated:** 2026-05-17  
**Status:** MVP / Build Phase canonical spec  
**Default user-facing language:** Tiếng Việt có dấu  
**Target stack:** React 19, TypeScript, Vite, FastAPI, LangGraph-style orchestration, PostgreSQL/Supabase, pgvector, Redis, Outbox/worker queue, Langfuse, OpenAI-compatible LLMs  
**Product positioning:** AI companion for private mental-health screening, emotional first-aid, guided reflection, and safe support escalation.

## Mục lục

- [PRD.md — Serene.AI Mental-Health Companion](#prdmd--sereneai-mental-health-companion)
  - [Mục lục](#mục-lục)
  - [0. Mục đích tài liệu](#0-mục-đích-tài-liệu)
  - [1. Executive Summary](#1-executive-summary)
  - [2. Product Thesis](#2-product-thesis)
  - [3. Người dùng mục tiêu](#3-người-dùng-mục-tiêu)
    - [3.1 Primary users](#31-primary-users)
    - [3.2 Secondary users](#32-secondary-users)
  - [4. Nguyên tắc bất biến](#4-nguyên-tắc-bất-biến)
  - [5. Phạm vi sản phẩm MVP](#5-phạm-vi-sản-phẩm-mvp)
    - [5.1 Chat cảm xúc an toàn](#51-chat-cảm-xúc-an-toàn)
    - [5.2 Guided screening: cơ bản và kiểm tra sâu](#52-guided-screening-cơ-bản-và-kiểm-tra-sâu)
      - [5.2.1 Screening cơ bản: PHQ-9 và GAD-7](#521-screening-cơ-bản-phq-9-và-gad-7)
      - [5.2.2 Kiểm tra sâu: DASS-21, MDQ và PCL-5](#522-kiểm-tra-sâu-dass-21-mdq-và-pcl-5)
    - [5.3 Mood, meal, sleep và lifestyle check-in](#53-mood-meal-sleep-và-lifestyle-check-in)
    - [5.4 Personal Insight Dashboard](#54-personal-insight-dashboard)
    - [5.5 Memory Cards](#55-memory-cards)
    - [5.6 Persona, reward và progression](#56-persona-reward-và-progression)
    - [5.7 Voice, TTS và meme](#57-voice-tts-và-meme)
    - [5.8 Resource Hub và coping recommendation](#58-resource-hub-và-coping-recommendation)
    - [5.9 SOS và crisis support](#59-sos-và-crisis-support)
  - [6. Kiến trúc hệ thống](#6-kiến-trúc-hệ-thống)
    - [6.1 Tổng quan](#61-tổng-quan)
    - [6.2 Stack dữ liệu và runtime](#62-stack-dữ-liệu-và-runtime)
    - [6.3 Mô hình agent runtime](#63-mô-hình-agent-runtime)
    - [6.4 Advisor-assisted Analyst Pipeline](#64-advisor-assisted-analyst-pipeline)
    - [6.5 Model strategy](#65-model-strategy)
  - [7. Luồng nghiệp vụ chính](#7-luồng-nghiệp-vụ-chính)
    - [7.1 Normal chat flow](#71-normal-chat-flow)
    - [7.2 Analyst-assisted insight flow](#72-analyst-assisted-insight-flow)
    - [7.3 Crisis/SOS flow](#73-crisissos-flow)
    - [7.4 Dashboard rollup flow](#74-dashboard-rollup-flow)
  - [8. Data Architecture](#8-data-architecture)
    - [8.1 Source of truth](#81-source-of-truth)
    - [8.2 Data domains](#82-data-domains)
    - [8.3 Data privacy rules](#83-data-privacy-rules)
  - [9. API/Product Contract cấp cao](#9-apiproduct-contract-cấp-cao)
  - [10. Observability và Debuggability](#10-observability-và-debuggability)
    - [10.1 Langfuse trace bắt buộc](#101-langfuse-trace-bắt-buộc)
    - [10.2 Metrics tối thiểu](#102-metrics-tối-thiểu)
    - [10.3 Degradation policy](#103-degradation-policy)
  - [11. Safety, Security và Abuse Prevention](#11-safety-security-và-abuse-prevention)
    - [11.1 Mental-health safety](#111-mental-health-safety)
    - [11.2 AI security](#112-ai-security)
    - [11.3 Output sanitizer](#113-output-sanitizer)
  - [12. Evaluation và Quality Gates](#12-evaluation-và-quality-gates)
    - [12.1 Baseline hiện tại](#121-baseline-hiện-tại)
    - [12.2 Required evaluation layers](#122-required-evaluation-layers)
    - [12.3 Release blockers](#123-release-blockers)
  - [13. MVP Scope và Non-goals](#13-mvp-scope-và-non-goals)
    - [13.1 In scope](#131-in-scope)
    - [13.2 Out of scope for MVP](#132-out-of-scope-for-mvp)
  - [14. Roadmap triển khai](#14-roadmap-triển-khai)
    - [Phase 0 — Stabilize core safety and chat](#phase-0--stabilize-core-safety-and-chat)
    - [Phase 1 — Analyst and dashboard insight](#phase-1--analyst-and-dashboard-insight)
    - [Phase 2 — Memory and personalization](#phase-2--memory-and-personalization)
    - [Phase 3 — Voice, meme and UX polish](#phase-3--voice-meme-and-ux-polish)
    - [Phase 4 — Reward/persona progression](#phase-4--rewardpersona-progression)
    - [Phase 5 — Security and production readiness](#phase-5--security-and-production-readiness)
  - [15. Success Metrics](#15-success-metrics)
    - [Product metrics](#product-metrics)
    - [Safety metrics](#safety-metrics)
    - [Engineering metrics](#engineering-metrics)
  - [16. Acceptance Criteria](#16-acceptance-criteria)
  - [17. Final Product Principle](#17-final-product-principle)

---

## 0. Mục đích tài liệu

Tài liệu này là PRD nguồn sự thật cho Serene.AI ở giai đoạn MVP. PRD mô tả định vị sản phẩm, phạm vi tính năng, kiến trúc tác nhân, luồng dữ liệu, yêu cầu an toàn, tiêu chuẩn đánh giá và tiêu chí nghiệm thu. Tài liệu cố ý không mô tả chi tiết code, file triển khai hoặc tên hàm nội bộ.

Bản cập nhật này phản ánh các thay đổi kiến trúc mới nhất:

- Hệ thống giữ mô hình **lightweight multi-agent**, không tạo nhiều bot độc lập.
- Trục dữ liệu chuyển về **PostgreSQL/Supabase làm source of truth**, kết hợp pgvector, Redis, outbox worker và Langfuse trace.
- Safety chạy trước mọi LLM call và có quyền chặn toàn bộ normal flow.
- Analyst Agent có thể sử dụng các advisor chuyên biệt, dữ liệu nội bộ, RAG và external search có kiểm soát để tạo insight.
- Dashboard phải hiển thị insight có bằng chứng, không chỉ hiển thị chữ giới thiệu hoặc số liệu rời rạc.
- Persona, meme, voice/TTS, reward và memory là lớp trải nghiệm; không được sở hữu logic an toàn hoặc chẩn đoán.
- Persona registry hiện hành chỉ gồm **Dũng** (`dung_luong`), **Đạt** (`dat_le`) và **Hậu** (`hau_luong`); loại bỏ toàn bộ persona cũ khỏi PRD runtime.
- Bổ sung nhóm **Kiểm tra sâu** gồm DASS-21, MDQ và PCL-5 để mở rộng phân tích stress, dao động khí sắc và sang chấn theo hướng sàng lọc an toàn, không chẩn đoán.

---

## 1. Executive Summary

Serene.AI là ứng dụng đồng hành sức khỏe tinh thần cho người trẻ Việt Nam, tập trung vào bốn việc: giúp người dùng nói thật trong không gian riêng tư, hiểu trạng thái của mình qua dữ liệu cá nhân, nhận hành động nhỏ có thể làm ngay, và được hỗ trợ an toàn khi có dấu hiệu nguy cơ cao.

Sản phẩm không phải bác sĩ AI, không chẩn đoán rối loạn tâm thần, không kê thuốc và không thay thế trị liệu chuyên nghiệp. Sản phẩm đóng vai trò **mental-health companion**: lắng nghe, sàng lọc ban đầu, hỗ trợ phản tư, đề xuất coping/resource phù hợp và kích hoạt luồng an toàn khi cần.

Kiến trúc runtime gồm ba vai trò chính:

| Vai trò | User-facing | Trách nhiệm |
|---|---:|---|
| Friend Agent | Có | Trò chuyện, phản hồi cảm xúc, áp dụng persona/style, tạo câu trả lời cuối cùng cho normal flow. |
| Analyst Agent | Không | Phân tích dữ liệu hội thoại, mood, PHQ-9/GAD-7, DASS-21, MDQ, PCL-5, meal check-in, memory và resource context để tạo structured insight. |
| Safety Agent | Có, qua payload kiểm soát | Xử lý high-risk/SOS, de-escalation, voice grounding, hotline/referral, audit và crisis logs. |

Các thành phần còn lại như screening, persona router, reward, memory, dashboard, resource retrieval, TTS, meme và notification là **service/router/worker**, không phải agent có danh tính riêng.

---

## 2. Product Thesis

Người dùng mục tiêu không bắt đầu bằng nhu cầu “được điều trị”. Họ thường bắt đầu bằng các trạng thái mơ hồ: “mình không ổn”, “mình muốn nói ra nhưng sợ bị đánh giá”, “mình không biết đang bị gì”, hoặc “mình chỉ cần ai đó nghe mình”.

Vì vậy, vòng lặp sản phẩm phải là:

```text
Talk → Understand → Act → Reflect → Return
```

- **Talk:** người dùng trò chuyện tự nhiên bằng tiếng Việt đời thường.
- **Understand:** hệ thống phân tích cảm xúc, stressor, trigger, thói quen và tín hiệu rủi ro.
- **Act:** hệ thống đề xuất một hành động nhỏ, có thể làm ngay, không giáo điều.
- **Reflect:** dashboard và memory giúp người dùng nhìn lại pattern, tiến triển và điều từng giúp họ ổn hơn.
- **Return:** gamification nhẹ, persona style, voice, memory card và knowledge unlock tạo động lực quay lại mà không gây nghiện hoặc phụ thuộc cảm xúc.

---

## 3. Người dùng mục tiêu

### 3.1 Primary users

Người trẻ 18–24 tuổi, đặc biệt là sinh viên và người mới đi làm, đang đối mặt với áp lực học tập, định hướng nghề nghiệp, tài chính, gia đình, quan hệ cá nhân, cô đơn hoặc tự ti nhưng chưa sẵn sàng tìm chuyên gia.

Nhu cầu chính:

- Có nơi riêng tư để nói thật mà không bị phán xét.
- Được phản hồi bằng tiếng Việt tự nhiên, không máy móc, không sáo rỗng.
- Hiểu vì sao mình hay tụt mood, stress hoặc mất năng lượng.
- Có hành động nhỏ để làm ngay thay vì lời khuyên chung chung.
- Có quyền kiểm soát dữ liệu cá nhân, ký ức và lịch sử trò chuyện.

### 3.2 Secondary users

Người đã có thói quen tự quan sát sức khỏe tinh thần, muốn theo dõi mood, sleep, meal, stress pattern, coping history và kết quả sàng lọc định kỳ.

Nhu cầu chính:

- Dashboard có insight thực sự, có bằng chứng và gợi ý cải thiện.
- Theo dõi PHQ-9/GAD-7 và các bài kiểm tra sâu như DASS-21, MDQ, PCL-5 theo thời gian mà không bị gắn nhãn bệnh.
- Lưu lại memory quan trọng nhưng có thể sửa/xóa.
- Có resource phù hợp với trạng thái hiện tại.

---

## 4. Nguyên tắc bất biến

1. **Safety-first:** mọi chat turn phải đi qua Safety Gate trước khi vào LLM hoặc advisor.
2. **Không chẩn đoán:** không nói “bạn bị trầm cảm/rối loạn lo âu/rối loạn lưỡng cực/PTSD”; chỉ mô tả dấu hiệu, mức độ sàng lọc và khuyến nghị tìm chuyên gia khi cần.
3. **Một identity ổn định:** Serene là một assistant duy nhất; persona chỉ là style mode.
4. **Internal Analyst không nói với user:** Analyst chỉ tạo structured signal/insight cho Friend Agent hoặc dashboard-safe layer.
5. **Advisor không viết final response:** advisor chỉ cung cấp evidence, context, recommendation candidates và provenance.
6. **Frontend không sở hữu safety/business logic:** frontend chỉ render trạng thái backend trả về.
7. **Dữ liệu nhạy cảm backend-only:** raw risk indicators, clinical notes, analyst rationale và crisis logs không được expose ra UI.
8. **Memory phải có kiểm soát:** memory card phải ngắn, rõ, có thể xem/sửa/xóa; không lưu lặp vô hạn.
9. **Voice/TTS không block chat:** text response phải trả trước; audio được xử lý async.
10. **Langfuse trace bắt buộc cho luồng agentic:** cần nhìn được routing, advisor usage, analyst reasoning summary, latency, token/cost và failure mode.

---

## 5. Phạm vi sản phẩm MVP

### 5.1 Chat cảm xúc an toàn

Chat là bề mặt chính. Serene phải phản hồi bằng tiếng Việt tự nhiên, bám ngữ cảnh, không lạc vai, không tạo cảm giác “AI-generated”. Câu trả lời cần ưu tiên lắng nghe, gọi đúng vấn đề người dùng vừa nêu, phản hồi ngắn vừa đủ và kết thúc bằng một câu hỏi hoặc hành động nhỏ khi phù hợp.

Yêu cầu:

- Bám conversation history và memory liên quan.
- Không nhồi quá nhiều câu hỏi trong một lượt.
- Không dùng giọng trị liệu khuôn mẫu.
- Không đưa lời khuyên sớm khi người dùng chỉ cần xả cảm xúc.
- Có thể dùng meme/giọng hài nhẹ trong low-risk turn nếu đúng ngữ cảnh và persona cho phép.
- Không dùng meme, joke hoặc persona “vui” trong grief, high-distress, SOS hoặc nội dung nhạy cảm.

### 5.2 Guided screening: cơ bản và kiểm tra sâu

Serene dùng các bài sàng lọc có cấu trúc để giúp người dùng tự quan sát sức khỏe tinh thần theo nhiều chiều. Tất cả kết quả chỉ là **tín hiệu sàng lọc**, không phải chẩn đoán, không kết luận bệnh và không thay thế đánh giá của chuyên gia.

#### 5.2.1 Screening cơ bản: PHQ-9 và GAD-7

PHQ-9 và GAD-7 được dùng để theo dõi dấu hiệu liên quan trầm cảm và lo âu ở mức sàng lọc ban đầu.

Yêu cầu:

- Hiển thị rõ đây là công cụ sàng lọc, không phải chẩn đoán.
- Lưu điểm số, severity band, thời điểm làm bài và coverage.
- Cho phép dashboard dùng kết quả như một nguồn evidence.
- Nếu điểm cao hoặc câu trả lời liên quan tự hại, phải kích hoạt luồng safety phù hợp.
- Nếu user chưa làm test, dashboard phải hiển thị lời mời rõ ràng: “Hãy làm bài test để Serene có thêm dữ liệu theo dõi xu hướng của bạn.”

#### 5.2.2 Kiểm tra sâu: DASS-21, MDQ và PCL-5

Nhóm kiểm tra sâu giúp Analyst Agent có thêm dữ liệu đa chiều để phân tích stress, dao động khí sắc và dấu hiệu sang chấn. Nhóm này chỉ nên được gợi ý khi người dùng đã có nhu cầu hiểu sâu hơn, dashboard thiếu dữ liệu để kết luận xu hướng, hoặc hệ thống phát hiện các pattern đủ đáng chú ý nhưng không nằm trong crisis flow.

| Bài kiểm tra | Mục tiêu sàng lọc | Dữ liệu lưu | Cách diễn đạt user-facing | Guardrail bắt buộc |
|---|---|---|---|---|
| DASS-21 | Phân tích chuyên sâu hơn về stress, lo âu và trầm cảm theo cụm tín hiệu. | Subscale scores, severity band, timestamp, completion coverage. | “Điểm của bạn cho thấy mức stress/lo âu/tâm trạng buồn đang ở vùng cần chú ý hơn.” | Không thay thế PHQ/GAD và không kết luận bệnh. |
| MDQ | Sàng lọc dấu hiệu dao động khí sắc/chu kỳ năng lượng có thể liên quan rối loạn lưỡng cực. | Positive item count, impairment marker, clustering marker, timestamp. | “Có một số dấu hiệu dao động khí sắc/năng lượng đáng theo dõi thêm.” | Không nói “bạn bị bipolar/rối loạn lưỡng cực”; điểm cao phải khuyến nghị gặp chuyên gia. |
| PCL-5 | Sàng lọc dấu hiệu liên quan sang chấn/PTSD theo nhóm triệu chứng. | Total score, cluster scores, timestamp, safe summary. | “Có một số phản ứng sau trải nghiệm căng thẳng/sang chấn đáng được chăm sóc kỹ hơn.” | Không hiển thị raw trauma detail lên dashboard; không ép user kể lại sang chấn. |

Yêu cầu triển khai:

- Mỗi bài kiểm tra có consent/disclaimer riêng trước khi bắt đầu.
- Cho phép user bỏ qua, dừng giữa chừng hoặc xóa kết quả theo retention policy.
- Lưu raw answer ở backend-only nếu cần tính điểm; dashboard chỉ dùng summary an toàn.
- Không dùng MDQ/PCL-5 để tự động gắn nhãn “rối loạn lưỡng cực”, “PTSD” hoặc bất kỳ chẩn đoán nào.
- Nếu câu trả lời cho thấy nguy cơ tự hại hoặc mất an toàn hiện tại, Safety Gate phải được kích hoạt ngay, không chờ hoàn tất bài test.
- Analyst chỉ được dùng kết quả kiểm tra sâu như một evidence source, kèm confidence và caveat.

### 5.3 Mood, meal, sleep và lifestyle check-in

Serene cần thu thập tín hiệu đời sống nhẹ, không gây ma sát, gồm mood check-in, meal check-in, sleep schedule từ onboarding và các phản tư ngắn.

Nguồn dữ liệu MVP:

- Mood check-in theo ngày hoặc theo buổi.
- Meal check-in sáng/trưa/tối.
- Thời gian ngủ/dậy nếu user cung cấp.
- Conversation memory và session summary.
- PHQ-9/GAD-7.
- DASS-21, MDQ, PCL-5 nếu user đã hoàn thành kiểm tra sâu.
- Coping action đã thử và mức độ hữu ích.

Yêu cầu:

- Check-in phải nhanh, có thể bỏ qua.
- Không phán xét người dùng vì ăn uống/ngủ nghỉ chưa tốt.
- Insight lifestyle chỉ dùng ngôn ngữ “có xu hướng/có dấu hiệu”, không kết luận bệnh.
- Khi sleep dưới 6 giờ nhiều ngày, dashboard có thể cảnh báo nhẹ và đề xuất tiny action.

### 5.4 Personal Insight Dashboard

Dashboard phải là nơi người dùng hiểu mình hơn, không phải trang chứa nhiều text chung chung. Dashboard cần tổng hợp dữ liệu thành insight có bằng chứng.

Dashboard phải trả lời được các câu hỏi:

- Điều gì thường làm mood của người dùng giảm?
- Thời điểm nào trong ngày/tuần người dùng dễ căng thẳng hơn?
- Thói quen ăn/ngủ có liên quan gì đến mood hoặc năng lượng?
- PHQ-9/GAD-7 gần nhất đang ở mức nào và xu hướng thay đổi ra sao?
- DASS-21, MDQ hoặc PCL-5 có bổ sung góc nhìn nào về stress, dao động khí sắc hoặc sang chấn không?
- Coping action nào từng giúp người dùng ổn hơn?
- Người dùng đang đối mặt với nhóm khó khăn nào: học tập, gia đình, quan hệ, công việc, sức khỏe, cô đơn, tự trách?
- Một việc nhỏ nên làm hôm nay là gì?

Mỗi insight nên có:

| Thành phần | Mô tả |
|---|---|
| Insight title | Một câu ngắn, rõ, có tính khai sáng. |
| Evidence | Dữ liệu hỗ trợ: mood, memory, meal, PHQ-9/GAD-7, DASS-21, MDQ, PCL-5, chat theme, thời gian. |
| Confidence | Low/medium/high; không giả vờ chắc chắn khi dữ liệu ít. |
| Meaning | Diễn giải vì sao pattern này quan trọng. |
| Suggested action | Một hành động nhỏ, khả thi trong 2–10 phút. |
| Safety boundary | Không chẩn đoán, không kết luận bệnh, không thay chuyên gia. |

### 5.5 Memory Cards

Memory giúp Serene có continuity nhưng không được tạo cảm giác bị theo dõi. Cách lưu ưu tiên “thẻ ký ức” ngắn, rõ, user kiểm soát được.

Yêu cầu:

- Lưu memory dưới dạng câu ngắn, có nghĩa độc lập.
- Không lưu trùng nội dung; nếu user nhắc lại cùng một ý, tăng số lần lặp hoặc cập nhật metadata thay vì tạo card mới.
- Mỗi reply chỉ dùng tối đa một memory liên quan để tránh creepy personalization.
- User có thể giữ, sửa, xóa hoặc tắt memory.
- Không lưu nội dung tự hại chi tiết, thông tin nhạy cảm không cần thiết hoặc kết luận chẩn đoán.

Loại memory MVP:

- Preference: cách user muốn được gọi, phong cách hỗ trợ ưa thích.
- Emotional pattern: trigger hoặc trạng thái lặp lại.
- Coping history: điều từng giúp user ổn hơn.
- Current stressor: áp lực đang diễn ra.
- Lifestyle pattern: ăn/ngủ/năng lượng nếu user chia sẻ.
- Persona preference: style mode user thích.

### 5.6 Persona, reward và progression

Persona là **style mode** của Serene, không phải agent riêng. Reward chỉ phục vụ engagement lành mạnh, không khóa hỗ trợ cốt lõi. Persona được áp dụng vào Friend Agent như một lớp giọng điệu, nhịp trả lời, cách dùng meme/voice và mức độ phân tích; persona không được sở hữu safety policy, memory riêng, clinical interpretation hoặc quyền quyết định crisis flow.

Persona registry MVP hiện hành:

| Persona | Canonical ID | Availability | Vai trò sản phẩm | Guardrail chính |
|---|---|---|---|---|
| Dũng | `dung_luong` | Core / mặc định | Vui vẻ, bắt mood tốt, biết lắng nghe, tử tế, có thể dùng meme nhẹ để làm cuộc trò chuyện bớt nặng. | Meme/hài chỉ dùng khi low-risk; khi distress tăng phải chuyển sang giọng an toàn, không đùa quá đà. |
| Đạt | `dat_le` | Core | Trầm tính, có chiều sâu, giúp người dùng nhìn vấn đề rõ ràng hơn, có thể gợi mở theo hướng triết lý và phản tư. | Không được biến thành giọng chuyên gia chẩn đoán, không giảng đạo hoặc phân tích quá dài khi user đang quá tải. |
| Hậu | `hau_luong` | Unlockable — 500 Tim | Hướng nội, đơn giản, ít áp lực, phù hợp khi user overthinking hoặc muốn được ở cạnh nhẹ nhàng; ưu tiên voice-message vibe. | Không dùng voice như nguồn logic riêng; voice phải bám cùng response plan và không tạo phụ thuộc cảm xúc. |

Yêu cầu:

- Safety override thắng mọi persona.
- High-risk/SOS luôn ép về style an toàn; không dùng meme, joke, flirt, voice vui hoặc persona stylization trong crisis.
- Dũng và Đạt là persona core, user mới có thể dùng ngay.
- Hậu là persona mở khóa bằng Tim; frontend được hiển thị locked state nhưng backend là nguồn quyết định unlock.
- Tim/Heart không được thưởng cho việc chat vô tận.
- Reward nên gắn với hành vi có ích: mood check-in, meal check-in, reflection, hoàn thành tiny action, đọc knowledge card, review memory.
- Frontend chỉ hiển thị wallet/unlock state; backend là nguồn quyết định selection, unlock, affordability và safety override.
- Legacy alias cũ nếu còn trong database hoặc client phải được migrate/fallback an toàn về `dung_luong`, không giữ lại persona cũ trong UI/PRD.

### 5.7 Voice, TTS và meme

Voice/TTS là lớp trải nghiệm, không phải nguồn quyết định nội dung. Meme là lớp biểu đạt tùy ngữ cảnh, không được phá vỡ safety hoặc tính chuyên nghiệp.

Yêu cầu voice/TTS:

- Text response trả về trước; TTS chạy async.
- Voice script có thể khác visible text để tự nhiên hơn khi nghe, nhưng không được mâu thuẫn nội dung.
- Không render voice script thành text trên UI.
- TTS có trạng thái rõ: queued, processing, completed, failed, provider_disabled, deduped.
- Dedup theo nội dung và style để tránh tạo audio lặp.
- SOS voice cần ưu tiên grounding, nhịp chậm, thuyết phục ở lại, không đọc cứng hotline như checklist.

Yêu cầu meme:

- Chỉ dùng ở low-risk, đúng ngữ cảnh, không làm người dùng thấy bị xem nhẹ.
- Không dùng meme cho tự hại, grief, trauma, panic, medical, abuse hoặc crisis.
- Meme phải đi kèm text đủ ý; không thay thế phản hồi cảm xúc.

### 5.8 Resource Hub và coping recommendation

Resource Hub cung cấp psychoeducation, CBT-lite exercise, grounding, journaling, sleep hygiene, stress management và tài nguyên hỗ trợ phù hợp văn hóa Việt Nam.

Yêu cầu:

- Resource recommendation dựa trên trạng thái, dữ liệu gần đây và mức rủi ro.
- Không dùng resource như cách né tránh việc lắng nghe người dùng.
- Mỗi lượt chỉ nên đề xuất 1–2 hành động nhỏ.
- External content phải có provenance, không đưa nội dung không kiểm chứng vào lời khuyên sức khỏe.

### 5.9 SOS và crisis support

Khi user có dấu hiệu tự hại hoặc nguy cơ cao, hệ thống phải ưu tiên giữ người dùng an toàn và tiếp tục tương tác theo hướng de-escalation.

Yêu cầu:

- Safety Gate chạy trước mọi LLM call.
- Nếu SOS rõ ràng: bypass normal flow, không gọi Conversation Agent.
- Response phải đồng cảm, ngắn, trực tiếp, không máy móc.
- Có thể gửi hotline/referral nhưng không biến hotline thành phản hồi chính duy nhất.
- Crisis flow cần khuyến khích user ở lại cuộc trò chuyện, nói tiếp điều đang xảy ra, di chuyển khỏi vật nguy hiểm nếu có, liên hệ người đáng tin cậy khi phù hợp.
- Ghi crisis log và audit log cho mọi SOS turn.
- Không lặp lại cùng một template cứng ở các lượt liên tiếp.

---

## 6. Kiến trúc hệ thống

### 6.1 Tổng quan

Serene sử dụng kiến trúc backend-centered, safety-first, với frontend là display layer. Runtime chính gồm:

```text
User
  → Frontend
  → Backend API
  → Input Normalization + PII Masking
  → Safety Gate
  → Risk-based Router
  → Normal Flow hoặc Analyst-Assisted Flow hoặc Crisis Flow
  → Output Validator
  → Response
  → Async workers: memory, TTS, dashboard rollup, notification, evaluation logs
```

### 6.2 Stack dữ liệu và runtime

| Layer | Vai trò |
|---|---|
| Frontend | Chat UI, dashboard, screening UI, memory card UI, reward/persona UI, voice/meme rendering. |
| Backend API | Auth, routing, validation, service orchestration, API contract. |
| LangGraph-style orchestration | Điều phối Safety, Analyst, Conversation, Crisis và side-effect events. |
| PostgreSQL/Supabase | Source of truth cho user, messages, screening, check-in, memory, reward, crisis log, insight. |
| pgvector | Semantic memory, RAG retrieval và context matching. |
| Redis | Cache, rate limit, ephemeral session state, queue coordination. |
| Outbox/worker | TTS, memory extraction, dashboard rollup, notification, evaluation events. |
| Langfuse | Trace agentic workflow, prompt version, advisor usage, latency, cost, failure mode. |
| LLM provider | Config-driven OpenAI-compatible model calls cho Conversation, Analyst và Crisis Planner khi được phép. |

### 6.3 Mô hình agent runtime

```text
Safety Gate
  ├── Crisis / SOS → Safety Agent → controlled crisis payload
  └── Non-crisis → Router
          ├── Simple support → Friend Agent
          └── Needs insight → Analyst Agent → Friend Agent
```

- **Safety Gate** là deterministic pre-LLM layer.
- **Friend Agent** là agent duy nhất viết final text trong normal flow.
- **Analyst Agent** phân tích nhưng không nói trực tiếp với user.
- **Safety Agent** tạo crisis payload khi risk vượt ngưỡng.

### 6.4 Advisor-assisted Analyst Pipeline

Analyst Agent có thể gọi các advisor để phân tích sâu hơn. Advisor không phải agent user-facing và không được viết câu trả lời cuối cùng.

Advisor MVP:

| Advisor | Nguồn dữ liệu | Output |
|---|---|---|
| Screening Advisor | PHQ-9/GAD-7 | Severity band, trend, caveat không chẩn đoán. |
| Deep Screening Advisor | DASS-21, MDQ, PCL-5 | Stress profile, mood-variation signal, trauma-related signal, confidence và caveat không chẩn đoán. |
| Mood Advisor | Mood check-in | Mood trend, recurring trigger, volatility. |
| Lifestyle Advisor | Meal, sleep, onboarding | Pattern ăn/ngủ/năng lượng. |
| Memory Advisor | Memory cards/session summary | Current stressor, coping history, preference. |
| Resource Advisor | Resource library + RAG | Coping/resource candidates có provenance. |
| External Search Advisor | Web/resource search có kiểm soát | Thông tin psychoeducation/resource cập nhật, không truyền PII. |
| Safety Context Advisor | Risk snapshots, crisis logs dạng safe summary | Cảnh báo luồng high-risk hoặc cần hạn chế insight. |

Quy tắc external search:

- Không gửi raw user text, PII, crisis content hoặc clinical notes ra ngoài.
- Chỉ dùng query đã được sanitize và tổng quát hóa.
- Chỉ dùng cho psychoeducation, resource, thuật ngữ, hoặc thông tin hỗ trợ có tính công khai.
- Mỗi kết quả phải có provenance và thời điểm truy xuất.
- Nếu không có nguồn đáng tin, Analyst phải đánh dấu uncertainty thay vì suy đoán.

### 6.5 Model strategy

- Model name, temperature, timeout và fallback policy phải cấu hình được theo môi trường.
- Safety Gate không phụ thuộc LLM.
- Normal chat chỉ có một LLM caller chính để giảm latency và tránh mâu thuẫn response.
- Analyst có thể chạy sync hoặc async tùy mức cần thiết; không được làm chat thường chậm quá mức.
- Crisis Planner có thể dùng LLM để tạo response nhân văn hơn, nhưng luôn phải qua crisis validator và fallback deterministic khi timeout.
- Output Validator phải chặn chẩn đoán, internal leak, unsafe medical advice, persona bypass và prompt-injection echo.

---

## 7. Luồng nghiệp vụ chính

### 7.1 Normal chat flow

```text
1. User gửi tin nhắn.
2. Backend chuẩn hóa input và mask PII nếu cần lưu.
3. Safety Gate phân loại risk.
4. Nếu risk bình thường: router quyết định direct response hay cần Analyst.
5. Conversation Agent tạo response dựa trên history, persona, memory an toàn và context liên quan.
6. Output Validator kiểm tra boundary.
7. Frontend hiển thị text; worker xử lý TTS/memory/dashboard async.
8. Langfuse ghi trace đầy đủ.
```

### 7.2 Analyst-assisted insight flow

```text
1. Trigger: user hỏi “mình đang bị sao?”, dashboard refresh, pattern inquiry, hoặc định kỳ rollup.
2. Analyst lấy dữ liệu đã được phép: chat summary, memory, PHQ/GAD, DASS-21, MDQ, PCL-5, mood, meal, sleep, coping history.
3. Analyst gọi advisor cần thiết.
4. Analyst tạo structured insight bundle: signals, hypotheses, confidence, evidence, recommended actions, caveats.
5. Nếu trong chat: Conversation Agent diễn đạt lại bằng ngôn ngữ user-safe.
6. Nếu cho dashboard: insight được sanitize và lưu vào dashboard-safe layer.
7. Langfuse trace ghi rõ advisor nào được gọi, dùng nguồn nào, latency/cost bao nhiêu.
```

### 7.3 Crisis/SOS flow

```text
1. User gửi nội dung nguy hiểm hoặc distress rất cao.
2. Safety Gate quyết định crisis/high-risk.
3. Normal flow bị bypass.
4. Safety Agent tạo crisis payload: visible text, optional voice script, action cards, hotline/referral.
5. Crisis Validator kiểm tra tone, safety, không gây guilt/shame, không lặp template cứng.
6. Crisis log và audit log được ghi.
7. Frontend hiển thị crisis UI, voice grounding và follow-up step.
8. Langfuse + metrics ghi reason codes, không ghi raw PII.
```

### 7.4 Dashboard rollup flow

```text
1. Worker lấy dữ liệu mới: mood, meal, PHQ/GAD, DASS-21, MDQ, PCL-5, memory, conversation summary, coping action.
2. Analyst tạo hoặc cập nhật hypotheses.
3. Safety/privacy sanitizer loại raw risk, clinical note và internal rationale.
4. Dashboard-safe insight được expose qua API.
5. Frontend hiển thị insight cards, charts, suggested action và data freshness.
```

---

## 8. Data Architecture

### 8.1 Source of truth

PostgreSQL/Supabase là source of truth duy nhất cho dữ liệu bền vững. Redis chỉ dùng cho trạng thái tạm thời và cache. pgvector lưu embedding phục vụ retrieval và semantic matching. Outbox/worker xử lý side effect không chặn request chính.

### 8.2 Data domains

| Domain | Dữ liệu |
|---|---|
| Identity/Auth | User, consent, policy acknowledgement, auth tokens. |
| Conversation | Sessions, messages, summaries, assistant metadata. |
| Screening | PHQ-9/GAD-7 score, DASS-21 subscale scores, MDQ screening markers, PCL-5 total/cluster scores, severity/signal band, coverage, timestamp. |
| Mood/Lifestyle | Mood check-ins, emotions, triggers, meal check-ins, sleep schedule. |
| Memory | Memory cards, audit events, duplicate count, user action. |
| Safety | Risk snapshots, crisis logs, admin audit logs, trusted-contact policy. |
| Analyst | Raw structured signals, hypotheses, evidence references, dashboard-safe insights. |
| Resource/RAG | Wellness resources, bookmarks, play/read events, embeddings. |
| Reward/Persona | Wallet, reward events, inventory, persona unlock/progress, selected persona, persona price, backend-owned availability. |
| Voice/TTS | TTS jobs, style id, event signature, audio status. |
| Notification | Push/SSE events and delivery state. |
| Evaluation | Golden eval outputs, guardrail eval, AI security eval, latency/cost metrics. |

### 8.3 Data privacy rules

- Raw user text không được đưa vào logs/metrics.
- PII phải được mask trước khi lưu vào các vùng không cần raw text.
- Crisis logs và risk inference là backend-only.
- Dashboard chỉ đọc insight đã sanitize.
- PCL-5 hoặc dữ liệu sang chấn không được expose raw detail; dashboard chỉ hiển thị summary an toàn và quyền kiểm soát dữ liệu.
- MDQ chỉ được lưu/hiển thị như screening signal, không phải nhãn rối loạn lưỡng cực.
- User có thể xóa memory card và yêu cầu xóa dữ liệu theo retention policy.
- External search không được nhận raw PII hoặc nội dung crisis cụ thể.

---

## 9. API/Product Contract cấp cao

Tài liệu này không khóa chi tiết endpoint, nhưng yêu cầu hệ thống phải có các nhóm API sau:

| Nhóm API | Trách nhiệm |
|---|---|
| Auth/User | Đăng nhập, guest mode, profile, consent, retention setting. |
| Chat | Gửi message, stream response, history, crisis payload, assistant metadata safe. |
| Screening | Submit PHQ-9/GAD-7, DASS-21, MDQ, PCL-5; lấy kết quả gần nhất, lịch sử xu hướng, summary an toàn và trạng thái completion. |
| Mood/Meal | Check-in cảm xúc, meal check-in, streak/reward state. |
| Dashboard | Insight cards, charts, trend, suggested actions, data freshness. |
| Memory | List/create/update/delete memory cards, duplicate count, audit action. |
| Persona/Reward | Wallet, reward catalog, purchase, inventory, persona progress, selected persona, unlock state. |
| Resource | Search resource, recommendation, bookmark, playback/read events. |
| Voice/TTS | Tạo job, lấy trạng thái, audio URL, provider fallback. |
| Notification | SSE/push event stream, delivery state. |
| Evaluation/Admin | Internal-only eval, audit, safety metrics, prompt/trace review. |

Frontend không được tự suy luận safety tier, reward grant, unlock eligibility, crisis state hoặc diagnosis-like interpretation.

---

## 10. Observability và Debuggability

Serene cần trace rõ ràng vì lỗi chính của hệ agentic thường không nằm ở model yếu, mà ở routing, context assembly, advisor misuse hoặc output validation.

### 10.1 Langfuse trace bắt buộc

Mỗi chat turn cần trace các trường:

- request/session id đã ẩn danh;
- safety decision và reason codes;
- route: direct, analyst-assisted, crisis;
- persona/style decision;
- memory card được dùng nếu có;
- advisor được gọi, input đã sanitize và output summary;
- prompt version;
- model, latency, token/cost;
- output validator verdict;
- fallback/degradation nếu xảy ra.

Không trace raw PII, raw crisis details hoặc thông tin nhạy cảm vượt phạm vi debug.

### 10.2 Metrics tối thiểu

| Metric | Mục tiêu |
|---|---|
| Chat p95 latency | Theo dõi normal vs analyst-assisted vs crisis. |
| Safety false negative | Release blocker nếu phát hiện. |
| Internal leak rate | 0 cho production. |
| Diagnosis violation rate | 0 cho production. |
| TTS completion rate | Theo provider/status. |
| Dashboard insight coverage | Tỷ lệ user có đủ evidence để tạo insight. |
| Advisor usefulness | Advisor được gọi có làm tăng chất lượng insight không. |
| Cost per conversation | Kiểm soát cost-to-serve. |

### 10.3 Degradation policy

- LLM timeout: dùng response fallback an toàn.
- Analyst timeout: Conversation Agent trả lời bình thường, không bịa insight.
- Advisor unavailable: bỏ advisor đó, đánh dấu confidence thấp.
- Resource retrieval lỗi: không chặn chat.
- TTS provider lỗi: trả text và trạng thái provider_disabled/failed.
- Dashboard thiếu dữ liệu: hiển thị empty state có hướng dẫn thu thập dữ liệu, không tạo insight giả.

---

## 11. Safety, Security và Abuse Prevention

### 11.1 Mental-health safety

- Không chẩn đoán bệnh.
- Không kê thuốc, chỉnh liều thuốc hoặc thay thế chỉ định bác sĩ.
- Không đảm bảo người dùng “sẽ ổn” hoặc phủ nhận cảm xúc của họ.
- Không dùng ngôn ngữ gây guilt/shame trong crisis.
- Không romanticize self-harm hoặc mô tả phương pháp tự hại.
- Không tạo phụ thuộc cảm xúc vào persona hoặc khiến người dùng hiểu Dũng/Đạt/Hậu là người thật, chuyên gia thật, người yêu thật hoặc nguồn hỗ trợ duy nhất.

### 11.2 AI security

Hệ thống phải chống các nhóm tấn công:

- direct/indirect prompt injection;
- system prompt extraction;
- persona override;
- safety bypass qua roleplay;
- memory poisoning;
- RAG context injection;
- PII exfiltration;
- frontend tampering;
- reward farming;
- TTS flooding;
- IDOR/BOLA;
- log leakage.

### 11.3 Output sanitizer

Mọi user-facing response phải được kiểm tra để chặn:

- internal fields hoặc routing metadata;
- diagnosis label, bao gồm gắn nhãn trầm cảm, lo âu, rối loạn lưỡng cực hoặc PTSD;
- clinical certainty quá mức;
- unsafe medical advice;
- hotline/referral sai ngữ cảnh;
- persona/style vi phạm safety;
- prompt-injection echo;
- meme hoặc voice script bị render sai chỗ.

---

## 12. Evaluation và Quality Gates

### 12.1 Baseline hiện tại

| Hạng mục | Baseline |
|---|---:|
| Backend test suite | 901 pass, 0 fail |
| Safety tests | 84 pass, 0 fail |
| Golden dataset | 88 pass, 0 fail |
| Adversarial guardrails | 44 pass, 6 skip live-backend, 0 fail |
| Heuristic LLM-as-Judge | 50 pass |
| RAGAS heuristic review set | 59 questions, 0 hard fail |
| Blueprint score | 98.5/100 |
| P0 guardrail failure rate | 0% |

### 12.2 Required evaluation layers

| Layer | Mục tiêu |
|---|---|
| Unit tests | Service logic, schema, sanitizer, router, reward, memory, TTS. |
| Integration tests | Chat route, crisis flow, analyst-assisted flow, dashboard rollup. |
| Golden conversation eval | Kiểm tra route, tone, expected behavior, disallowed behavior. |
| Adversarial eval | Prompt injection, persona bypass, memory poisoning, safety bypass. |
| AI security eval | P0/P1/P2 threat classes. |
| Judge eval | Empathy, relevance, actionability, Vietnamese naturalness, boundary. |
| RAG/resource eval | Faithfulness, context precision/recall, source grounding. |
| UI smoke tests | Chat, dashboard, memory, voice, reward, crisis panel. |

### 12.3 Release blockers

- SOS false negative.
- Internal prompt/metadata leak.
- Diagnosis claim in user-facing output.
- Frontend tự quyết định safety/crisis state.
- Crisis log/audit log không được ghi.
- Analyst raw output hiển thị lên dashboard.
- TTS/voice script render thành visible text.
- External search gửi PII/raw crisis content.
- Dashboard bịa insight khi thiếu dữ liệu.
- Dashboard hiển thị raw trauma detail từ PCL-5 hoặc gắn nhãn bipolar/PTSD từ MDQ/PCL-5.

---

## 13. MVP Scope và Non-goals

### 13.1 In scope

- Guest/auth user mode.
- Chat cảm xúc tiếng Việt.
- Safety Gate + crisis flow.
- PHQ-9/GAD-7 screening.
- Kiểm tra sâu DASS-21, MDQ, PCL-5 với guardrail không chẩn đoán.
- Mood, meal, sleep/lifestyle signals.
- Memory cards có user control và duplicate handling.
- Analyst-assisted insight pipeline.
- Dashboard insight + chart + suggested action.
- Persona style modes Dũng/Đạt/Hậu + reward/progression.
- Voice/TTS async + dedup.
- Meme low-risk rendering.
- Resource Hub + RAG/resource recommendation.
- Langfuse trace + metrics + evaluation gates.

### 13.2 Out of scope for MVP

- Chẩn đoán hoặc điều trị lâm sàng.
- Kê thuốc hoặc tư vấn liều thuốc.
- Human therapist marketplace.
- Tự động liên hệ người thân nếu chưa có consent/legal gate.
- Agent tự trị có danh tính riêng ngoài ba vai trò runtime chính.
- Frontend-only safety logic.
- Thu thập dữ liệu nền ngoài phạm vi user đồng ý.
- Dashboard kết luận bệnh lý từ pattern sinh hoạt.

---

## 14. Roadmap triển khai

### Phase 0 — Stabilize core safety and chat

- Safety Gate trước mọi LLM.
- Normal chat bám ngữ cảnh.
- Output sanitizer chặn internal leak, diagnosis, unsafe advice.
- Langfuse trace cho route và model call.

### Phase 1 — Analyst and dashboard insight

- Chuẩn hóa nguồn dữ liệu: PHQ/GAD, DASS-21, MDQ, PCL-5, mood, meal, sleep, memory, session summary.
- Xây advisor-assisted Analyst Pipeline.
- Bổ sung Deep Screening Advisor để phân tích DASS-21, MDQ, PCL-5 theo hướng evidence-based, có caveat không chẩn đoán.
- Tạo dashboard-safe insight cards có evidence/confidence/action.
- Kiểm định dashboard không còn text chung chung hoặc insight giả.

### Phase 2 — Memory and personalization

- Memory card duplicate handling.
- User controls: keep/edit/delete/disable.
- Context injection tối đa một memory liên quan.
- Audit memory changes.

### Phase 3 — Voice, meme and UX polish

- TTS async status model.
- Voice script tách khỏi visible text.
- Crisis voice grounding.
- Meme low-risk rendering có guardrail.
- UI tiếng Việt nhất quán, không chêm English không cần thiết.

### Phase 4 — Reward/persona progression

- Heart economy idempotent.
- Persona unlock state backend-owned.
- Dũng và Đạt là core personas; Hậu là persona mở khóa 500 Tim.
- PersonaRouter chỉ nhận canonical IDs: `dung_luong`, `dat_le`, `hau_luong`.
- Legacy IDs cũ được migrate/fallback về `dung_luong`.
- Reward không khuyến khích chat vô tận.

### Phase 5 — Security and production readiness

- AI security testset trong CI.
- Live backend guardrail tests.
- Rate limit, abuse prevention, IDOR/BOLA checks.
- Cost/latency budget monitoring.
- Data retention và deletion policy.

---

## 15. Success Metrics

### Product metrics

| Metric | Mục tiêu |
|---|---|
| First meaningful response rate | User nhận phản hồi đúng vấn đề trong lượt đầu. |
| Return rate | User quay lại check-in hoặc chat không do guilt/shame. |
| Insight usefulness | User thấy dashboard giúp hiểu bản thân hơn. |
| Tiny action completion | User hoàn thành hành động nhỏ được gợi ý. |
| Memory trust | User giữ/sửa/xóa memory mà không thấy creepy. |

### Safety metrics

| Metric | Mục tiêu |
|---|---:|
| SOS false negative | 0 |
| P0 guardrail failure | 0 |
| Diagnosis violation | 0 |
| Internal leak | 0 |
| Crisis audit coverage | 100% |

### Engineering metrics

| Metric | Mục tiêu |
|---|---|
| Normal chat p95 latency | Trong budget sản phẩm, không bị Analyst kéo chậm. |
| Crisis response latency | Ưu tiên thấp hơn normal flow, fallback nhanh khi LLM timeout. |
| TTS non-blocking rate | 100% text response không chờ audio. |
| Trace coverage | 100% agentic turns có trace. |
| Cost per active user | Có monitoring và budget rõ. |

---

## 16. Acceptance Criteria

PRD chỉ được coi là thỏa mãn khi:

1. Sản phẩm có định vị rõ: companion + screening + support, không phải bác sĩ AI.
2. Runtime giữ ba vai trò chính: Conversation, Analyst, Safety.
3. Safety Gate chạy trước mọi LLM/advisor.
4. High-risk/SOS bypass normal flow.
5. Analyst không user-facing và advisor không viết final response.
6. Dashboard insight có evidence, confidence và action; không chỉ là đoạn văn chung chung.
7. Memory card không lặp vô hạn; user có quyền sửa/xóa.
8. Persona là style mode, không phải agent riêng; canonical set chỉ gồm `dung_luong`, `dat_le`, `hau_luong`.
9. Dũng và Đạt khả dụng từ đầu; Hậu mở khóa bằng 500 Tim; không còn bộ persona cũ trong PRD runtime.
10. Reward không khóa hỗ trợ thiết yếu.
11. Voice/TTS async, không block chat và không render voice script thành text.
12. External search được sanitize, có provenance, không truyền PII.
13. Langfuse trace đủ để debug route, advisor, prompt, latency, cost và failure mode.
14. Evaluation suite pass các gate safety, guardrail, golden conversation và AI security.
15. Kiểm tra sâu DASS-21/MDQ/PCL-5 được lưu, diễn giải và hiển thị như screening signal; không chẩn đoán stress disorder, rối loạn lưỡng cực hoặc PTSD.
16. Dashboard không hiển thị raw trauma detail, không ép user kể lại sang chấn và không dùng kết quả MDQ/PCL-5 để gắn nhãn bệnh.
17. Frontend không sở hữu logic safety, reward, unlock hoặc crisis decisioning.
18. Toàn bộ user-facing copy dùng tiếng Việt rõ ràng, tự nhiên, không pha thuật ngữ không cần thiết.

---

## 17. Final Product Principle

Serene.AI phải giúp người dùng cảm thấy: “Mình có một nơi đủ an toàn để nói thật, đủ thông minh để hiểu mình, đủ thực tế để biết bước tiếp theo, và đủ tôn trọng để mình kiểm soát dữ liệu của chính mình.”
