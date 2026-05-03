# Problem Brief — AI20K030: Sàng Lọc & Hỗ Trợ Sức Khỏe Tinh Thần

## 1. Bối cảnh

Sức khỏe tinh thần đang trở thành một vấn đề nổi bật trong nhóm người trẻ 18–24 tuổi, đặc biệt là sinh viên và người mới đi làm. Đây là nhóm thường xuyên đối mặt với áp lực học tập, định hướng nghề nghiệp, tài chính, kỳ vọng gia đình, quan hệ cá nhân và cảm giác cô đơn trong môi trường số. Tuy nhiên, nhiều người không tìm đến bác sĩ tâm lý hoặc chuyên gia tham vấn vì sĩ diện, sợ bị đánh giá, sợ gia đình hoặc bạn bè biết, hoặc chưa tin rằng vấn đề của mình “đủ nghiêm trọng” để cần hỗ trợ chuyên môn.

Dự án ra đời nhằm tạo ra một điểm chạm đầu tiên, riêng tư và an toàn, giúp người trẻ dám nói ra điều khó nói, hiểu trạng thái tâm lý của mình, nhận hỗ trợ ban đầu phù hợp và được chuyển đến nguồn lực chuyên môn khi cần thiết.

## 2. Vấn đề cốt lõi

Người dùng mục tiêu không bắt đầu bằng nhu cầu “được điều trị”. Họ thường bắt đầu bằng cảm giác mơ hồ như: “mình không ổn”, “mình không biết đang bị gì”, “mình muốn nói ra nhưng sợ bị đánh giá”, hoặc “mình chỉ cần ai đó lắng nghe”. Các giải pháp hiện tại còn phân mảnh: bài test tâm lý trực tuyến thường khô cứng, chatbot AI phổ thông thiếu cơ chế sàng lọc và an toàn, ứng dụng thiền/self-care chưa đủ cá nhân hóa, còn dịch vụ chuyên gia có rào cản về chi phí, thời gian và định kiến xã hội.

Bài toán cần giải quyết là: làm thế nào để xây dựng một ứng dụng AI đủ riêng tư để người trẻ dám chia sẻ, đủ thông minh để hiểu trạng thái tâm lý ban đầu, đủ thực tế để đưa ra hành động nhỏ có thể làm ngay, và đủ an toàn để chuyển người dùng đến hỗ trợ chuyên môn khi rủi ro vượt khỏi phạm vi tự hỗ trợ.

## 3. Insight người dùng

Người dùng 18–24 không tìm một “bác sĩ AI” thay thế trị liệu. Họ tìm một không gian đủ kín đáo để không phải giả vờ ổn, đủ ít phán xét để dám nói thật, đủ thấu hiểu để phản hồi đúng vấn đề, và đủ thực tế để giúp họ biết bước tiếp theo là gì.

Vì vậy, trải nghiệm sản phẩm cần đi theo vòng lặp: **Talk → Understand → Act → Reflect**. Người dùng trò chuyện để giải tỏa, hệ thống phân tích cảm xúc và dấu hiệu rủi ro, đề xuất một hành động nhỏ phù hợp, sau đó giúp người dùng nhìn lại tiến triển, trigger và cách hỗ trợ từng có hiệu quả.

## 4. Đề xuất giải pháp

Sản phẩm nên được định vị là **AI mental-health companion for private screening, emotional first-aid, and guided support**, không phải ứng dụng chẩn đoán hay thay thế bác sĩ. Kiến trúc multi-agent có thể gồm: Conversation Agent để lắng nghe và phản hồi không phán xét; Screener Agent để sàng lọc mức độ stress, lo âu, tâm trạng và rủi ro; Resource Agent để gợi ý self-help resources như grounding, journaling, sleep routine hoặc task breakdown; Escalation Agent để kết nối người dùng với hotline, chuyên gia hoặc cơ sở hỗ trợ khi cần; và Safety Guardrail để đảm bảo phản hồi không vượt phạm vi chuyên môn.

MVP nên tập trung vào các tính năng: guest/anonymous mode, trò chuyện cảm xúc an toàn, check-in ngắn, sàng lọc nhẹ qua hội thoại, dashboard cá nhân, trigger map, coping history, gợi ý hành động nhỏ, xóa lịch sử, giải thích quyền riêng tư và escalation flow khi rủi ro cao.

## 5. Giá trị khác biệt

Trong bối cảnh ứng dụng AI tràn ngập, lợi thế cạnh tranh không nằm ở việc “có chatbot”, mà nằm ở **niềm tin, bản địa hóa, an toàn và khả năng chăm sóc liên tục**. Sản phẩm cần hiểu tiếng Việt đời thường, cách người Việt nói vòng, nói giảm, nói đùa hoặc né tránh cảm xúc. Đồng thời, app phải nhớ người dùng “đúng cách”: ghi nhận trigger, thói quen cảm xúc và phương pháp từng giúp họ tốt hơn, nhưng vẫn cho phép xem, sửa và xóa dữ liệu cá nhân.

Dashboard không nên chỉ hiển thị điểm số tâm trạng, mà cần trả lời các câu hỏi có giá trị: điều gì thường làm người dùng tụt mood, khi nào họ căng thẳng nhất, điều gì từng giúp họ ổn hơn, và khi nào họ nên tìm hỗ trợ chuyên môn.

## 6. Kết luận

Dự án không nên được xây dựng như một chatbot AI đơn thuần, mà là một lớp hỗ trợ đầu tiên trong hành trình chăm sóc sức khỏe tinh thần của người trẻ Việt Nam. Người dùng sẽ ở lại nếu app đủ riêng tư để họ dám nói thật, đủ thấu hiểu để họ cảm thấy được nhìn thấy, đủ thực tế để họ biết phải làm gì tiếp theo, và đủ an toàn để không bỏ mặc họ khi cần hỗ trợ thật.

**Định vị đề xuất:** “Nơi an toàn để bạn nói thật, hiểu mình hơn, và biết bước tiếp theo.”
