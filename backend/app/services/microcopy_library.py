"""Curated Vietnamese microcopy for humane support turns."""

from __future__ import annotations

GENERIC_EMPATHY_PATTERNS = (
    "bạn không đơn độc",
    "ban khong don doc",
    "mọi chuyện rồi sẽ ổn",
    "moi chuyen roi se on",
    "hãy suy nghĩ tích cực",
    "hay suy nghi tich cuc",
    "hãy bình tĩnh",
    "hay binh tinh",
    "bạn rất can đảm",
    "ban rat can dam",
    "bạn thật dũng cảm khi chia sẻ",
    "ban that dung cam khi chia se",
    "tôi rất tiếc khi nghe",
    "toi rat tiec khi nghe",
    "mình thật sự rất xin lỗi",
    "minh that su rat xin loi",
    "cảm xúc của bạn là hoàn toàn hợp lệ",
    "cam xuc cua ban la hoan toan hop le",
    "tôi luôn ở đây để hỗ trợ bạn",
    "toi luon o day de ho tro ban",
    "bạn nên tìm kiếm sự giúp đỡ chuyên nghiệp",
    "ban nen tim kiem su giup do chuyen nghiep",
)

GRIEF_ANCHORS = (
    "Nghe vậy thì đau thật.",
    "Đoạn này không nhẹ đâu.",
    "Mất mát kiểu này dễ làm mọi thứ trong đầu rối tung lên.",
)

OVERWHELM_ANCHORS = (
    "Mình giảm mọi thứ xuống một chút nhé.",
    "Mình chưa vội gỡ hết. Mình đi từng chút thôi.",
    "Lúc này chỉ cần một bước rất nhỏ là đủ.",
)

SELF_BLAME_ANCHORS = (
    "Không phải bạn yếu đâu.",
    "Phản ứng vậy trong hoàn cảnh này là dễ hiểu.",
)

SAFETY_VISIBLE_VARIANTS = (
    "Mình nghe thấy lúc này đang rất nặng. Trước mắt mình chỉ muốn bạn ở lại đây với mình thêm một chút.",
    "Đoạn này nguy hiểm cho bạn rồi, nên mình sẽ nói thật chậm. Mình ở đây, và mình muốn mình cùng làm một việc nhỏ trước.",
    "Mình nghe rõ cảm giác tuyệt vọng trong câu bạn vừa viết. Chưa cần quyết gì lúc này; mình giữ nhịp với bạn từng chút.",
)

SAFETY_VOICE_VARIANTS = (
    "Bạn thử đặt điện thoại xuống thấp hơn một chút. Đặt hai chân chạm sàn. Hít vào nhẹ thôi, rồi thở ra dài hơn một nhịp. Chưa cần nghĩ đến chuyện tiếp theo; chỉ ở lại với mình trong vài hơi thở này.",
    "Mình sẽ đi chậm. Nhìn quanh và gọi thầm tên một vật ở gần bạn. Chạm tay vào mặt bàn hoặc áo của mình. Hít vào một nhịp ngắn, thở ra chậm hơn. Việc duy nhất lúc này là giữ bạn an toàn thêm một phút.",
    "Nếu có thể, bạn ngồi xuống hoặc tựa lưng vào đâu đó. Nới lỏng hàm, thả vai xuống. Mình đếm cùng bạn ba nhịp thở chậm; trong lúc này chưa cần giải thích gì cả.",
)

SAFETY_FOLLOW_UPS = (
    "Bạn chỉ cần nói một chút thôi: lúc này phần nào đang nghẹn nhất?",
    "Ngay bây giờ, bạn đang ở gần ai hoặc gần chỗ nào an toàn hơn không?",
    "Bạn muốn mình ở lại với phần cảm giác nào trước?",
)


def contains_generic_empathy(text: str) -> bool:
    lowered = (text or "").lower()
    return any(pattern in lowered for pattern in GENERIC_EMPATHY_PATTERNS)
