from __future__ import annotations

import re
import unicodedata
from typing import Iterable

from app.personas.aliases import resolve_alias
from app.services.output_policy_validator import validate_final_response
from app.services.schemas.contracts import AdvisorAdvice, ContextPack, FriendAgentOutput

_LEAKY_TERMS = (
    "distress_score",
    "risk_level",
    "safety_tier",
    "reason_codes",
    "friendagent",
    "analystagent",
    "advisor",
    "evidence_refs",
    "item_id",
)
_DIAGNOSIS_RE = re.compile(r"\b(tram cam|roi loan|depression|anxiety disorder|bipolar|ptsd)\b", re.IGNORECASE)


def _clean_move(move: str) -> str:
    text = (move or "").strip()
    text = re.sub(r"\s+", " ", text)
    return text[:180]


def _ascii_fold(text: str) -> str:
    folded = unicodedata.normalize("NFD", text or "")
    folded = "".join(ch for ch in folded if unicodedata.category(ch) != "Mn")
    folded = folded.replace("đ", "d").replace("Đ", "D")
    return re.sub(r"\s+", " ", folded.lower()).strip()


def _has_phrase(normalized: str, phrase: str) -> bool:
    phrase_norm = re.escape(_ascii_fold(phrase))
    return bool(re.search(rf"(?<![a-z0-9]){phrase_norm}(?![a-z0-9])", normalized))


def _is_greeting_only(normalized: str) -> bool:
    compact = re.sub(r"[^a-z0-9\s]", " ", normalized)
    words = [w for w in compact.split() if w not in {"dung", "dat", "hau", "oi", "e"}]
    return bool(words) and all(w in {"hi", "hello", "helo", "chao", "yo", "hey"} for w in words)


def _is_short_social_emotion_ping(normalized: str) -> bool:
    compact = re.sub(r"[^a-z0-9\s]", " ", normalized)
    words = compact.split()
    if not words or len(words) > 6:
        return False
    greeting_words = {"hi", "hello", "helo", "chao", "yo", "hey", "e", "oi"}
    feeling_words = {"chan", "buon", "met", "duoi", "nan", "te", "vui", "on", "khong", "qua", "hoi"}
    return any(w in greeting_words for w in words) and any(w in feeling_words for w in words)


def _is_continuation_fragment(user_message: str) -> bool:
    normalized = _ascii_fold(user_message)
    words = normalized.split()
    if len(words) <= 5:
        return True
    return any(
        normalized.startswith(prefix)
        for prefix in (
            "thi kieu",
            "thi la",
            "vay do",
            "xong roi",
            "roi kieu",
            "kieu nhu",
            "y la",
        )
    )


def _recent_user_context(recent_messages: list[dict] | None, current_message: str) -> str:
    if not recent_messages:
        return ""
    current = str(current_message or "").strip()
    candidates: list[str] = []
    for item in reversed(recent_messages):
        if item.get("role") != "user":
            continue
        content = str(item.get("content") or "").strip()
        if not content or content == current:
            continue
        candidates.append(content)
        if len(candidates) >= 2:
            break
    return " ".join(reversed(candidates))


def _memory_context_text(active_memory: dict | None) -> str:
    if not isinstance(active_memory, dict):
        return ""
    parts: list[str] = []
    for key in ("mem0_facts", "recent_summaries", "top_triggers", "active_goals", "effective_coping"):
        value = active_memory.get(key)
        if isinstance(value, list):
            parts.extend(str(item) for item in value[:3] if str(item or "").strip())
        elif isinstance(value, str) and value.strip():
            parts.append(value)
    return " ".join(parts[:8])


def _topic_anchor(
    user_message: str,
    *,
    recent_messages: list[dict] | None = None,
    active_memory: dict | None = None,
) -> str:
    current = _ascii_fold(user_message)
    supporting = ""
    if _is_continuation_fragment(user_message):
        supporting = f"{_recent_user_context(recent_messages, user_message)} {_memory_context_text(active_memory)}"
    combined = _ascii_fold(f"{user_message} {supporting}")

    social_phrases = (
        "bi bo bo",
        "bi ignore",
        "khong ai rep",
        "khong ai tra loi",
        "group chat",
        "bi bo roi",
        "ban be",
        "bi seen",
    )
    if any(_has_phrase(current, phrase) for phrase in social_phrases) or (
        _is_continuation_fragment(user_message) and any(_has_phrase(combined, phrase) for phrase in social_phrases)
    ):
        return "chuyện bị bỏ bơ trong quan hệ"

    topic_checks: tuple[tuple[tuple[str, ...], str], ...] = (
        (("deadline", "han nop", "nop bai", "bai tap", "diem thi", "on thi", "thi cuoi ky", "mon hoc", "do an"), "deadline và chuyện học hành"),
        (("cong ty", "di lam", "sep", "dong nghiep", "intern", "luong"), "chuyện công việc"),
        (("mat ngu", "khong ngu", "thuc khuya", "ngu khong duoc"), "việc mất ngủ"),
        (("overthinking", "nghi nhieu", "lo qua", "lo au", "bat an"), "cơn lo và overthinking"),
        (("co don", "mot minh", "khong ai", "lac long"), "cảm giác một mình"),
        (("met", "kiet suc", "can kiet", "burnout", "qua tai", "duoi"), "cảm giác kiệt sức"),
        (("gia dinh", "bo me", "ba me", "me", "ba", "cha"), "chuyện gia đình"),
        (("chia tay", "nguoi yeu", "yeu don phuong"), "chuyện tình cảm"),
        (("tien", "no", "het tien", "tai chinh"), "áp lực tiền bạc"),
        (("buon", "khoc", "chan", "that vong"), "nỗi buồn này"),
        (("tuc", "gian", "buc", "kho chiu"), "cơn bực trong lòng"),
    )
    for needles, label in topic_checks:
        if any(_has_phrase(current, needle) for needle in needles):
            return label
    if _is_continuation_fragment(user_message):
        for needles, label in topic_checks:
            if any(_has_phrase(combined, needle) for needle in needles):
                return label

    stripped = user_message.strip()
    if len(stripped) <= 28:
        return f'chuyện "{stripped}"'
    return "điều cậu vừa kể"


def _is_asking_for_advice(user_message: str) -> bool:
    normalized = _ascii_fold(user_message)
    return "?" in user_message or any(
        _has_phrase(normalized, token)
        for token in (
            "lam sao",
            "nen lam gi",
            "phai lam gi",
            "cho minh loi khuyen",
            "tu van",
            "giup minh",
            "ke hoach",
        )
    )


def _is_reassurance_doubt(normalized: str) -> bool:
    return any(
        _has_phrase(normalized, token)
        for token in (
            "ao tuong",
            "hoang tuong",
            "tuong tuong",
            "minh co dien",
            "minh sai ha",
            "minh sai khong",
            "qua nhay cam",
        )
    )


def _is_physical_discomfort(normalized: str) -> bool:
    return any(
        _has_phrase(normalized, token)
        for token in ("dau bung", "dau dau", "buon non", "non", "sot", "kho chiu trong nguoi")
    )


def _is_diagnosis_request(normalized: str) -> bool:
    return any(
        _has_phrase(normalized, token)
        for token in (
            "minh bi benh gi",
            "toi bi benh gi",
            "chan doan",
            "co phai minh bi tram cam",
            "co phai minh bi roi loan",
        )
    )


def _safe_advisor_sentence(moves: list[str]) -> str | None:
    for move in moves:
        if not move:
            continue
        folded = _ascii_fold(move)
        if any(token in folded for token in _LEAKY_TERMS):
            continue
        if re.fullmatch(r"[a-z0-9_]+", folded) and "_" in folded:
            continue
        return move.rstrip(".?!") + "."
    return None


def _second_safe_advisor_sentence(moves: list[str]) -> str | None:
    first = _safe_advisor_sentence(moves)
    for move in moves:
        sentence = _safe_advisor_sentence([move])
        if sentence and sentence != first:
            return sentence
    return None


def _response_context(pack: ContextPack) -> tuple[list[dict], dict | None]:
    recent_messages = list(pack.recent_messages or [])
    active_memory = pack.active_memory if isinstance(pack.active_memory, dict) else None
    return recent_messages, active_memory


def _contains_any(normalized: str, tokens: tuple[str, ...]) -> bool:
    return any(_has_phrase(normalized, token) or token in normalized for token in tokens)


def _dung_intents(user_message: str, pack: ContextPack) -> list[str]:
    recent_messages, active_memory = _response_context(pack)
    supporting = ""
    if _is_continuation_fragment(user_message):
        supporting = f"{_recent_user_context(recent_messages, user_message)} {_memory_context_text(active_memory)}"
    text = _ascii_fold(f"{user_message} {supporting}")
    checks: tuple[tuple[str, tuple[str, ...]], ...] = (
        ("deadline", ("deadline", "han nop", "nop bai", "bai tap", "thi cu", "on thi", "do an", "hoc tiep")),
        ("bữa ăn/năng lượng", ("bo bua", "khong an", "an uong", "khong con thay vi", "vi giac", "an gi", "ca phe", "bua", "doi", "run")),
        ("tự trách", ("tu trach", "loi tai minh", "do minh", "vo dung", "minh te", "thua kem")),
        ("overthinking", ("overthinking", "nghi nhieu", "suy dien", "lo qua", "bat an")),
        ("quan hệ", ("ban be", "nguoi yeu", "dong nghiep", "group chat", "bi seen", "bo roi", "bi bo bo", "bo bo")),
        ("mệt/quá tải", ("met", "qua tai", "kiet suc", "can kiet", "can suc", "het suc", "het pin", "burnout", "duoi")),
        ("cần kế hoạch", ("ke hoach", "phuong an", "phai lam gi", "nen lam gi", "lam gi tiep", "go tung nut")),
    )
    out: list[str] = []
    for label, tokens in checks:
        if _contains_any(text, tokens):
            out.append(label)
    return out[:4]


def _dung_context_line(user_message: str, pack: ContextPack) -> str:
    recent_messages, active_memory = _response_context(pack)
    anchor = _topic_anchor(user_message, recent_messages=recent_messages, active_memory=active_memory)
    if _has_phrase(_ascii_fold(anchor), "bo bo"):
        return "Bị bỏ bơ trong quan hệ dễ làm người ta tự xoáy thật."
    intents = _dung_intents(user_message, pack)
    if len(intents) >= 2:
        return "Tớ thấy đang dồn mấy cục cùng lúc: " + ", ".join(intents) + "."
    if intents:
        return f"Phần {intents[0]} có vẻ đang kéo mood cậu xuống khá rõ."
    recent_messages, active_memory = _response_context(pack)
    anchor = _topic_anchor(user_message, recent_messages=recent_messages, active_memory=active_memory)
    return f"Đoạn về {anchor} có vẻ đang mắc lại khá rõ."


def _dung_tiny_step(user_message: str, pack: ContextPack) -> str:
    intents = set(_dung_intents(user_message, pack))
    if "bữa ăn/năng lượng" in intents:
        return "Bước nhỏ nhất: uống vài ngụm nước rồi kiếm một món dễ nuốt trước, kiểu bánh/sữa/cháo cũng tính là cứu pin rồi."
    if "deadline" in intents or "cần kế hoạch" in intents:
        return "Bước nhỏ nhất: mở đúng một file, làm 10 phút phần dễ nhất, chưa cần thắng cả deadline trong một pha."
    if "tự trách" in intents:
        return "Bước nhỏ nhất: tách một dòng sự kiện thật với một dòng cậu đang tự kết tội mình, để não đỡ tự xử oan."
    if "overthinking" in intents:
        return "Bước nhỏ nhất: chốt một điều chắc chắn đang xảy ra, còn mấy giả thuyết thì để tớ ngồi lọc cùng cậu sau."
    if "quan hệ" in intents:
        return "Bước nhỏ nhất: chỉ ghi lại điều thật sự xảy ra trước, rồi hãy quyết định có cần nhắn một câu rất ngắn không."
    if _is_asking_for_advice(user_message):
        return "Bước nhỏ nhất: chọn một việc làm được trong 10 phút trước, lụm lại chút quyền điều khiển đã."
    return "Cậu nói đoạn nào còn mắc trong đầu trước cũng được, tớ bám theo mạch đó với cậu."


def _dung_response(user_message: str, moves: list[str], supportive_mode: bool, pack: ContextPack) -> str:
    normalized = _ascii_fold(user_message)
    advisor = _safe_advisor_sentence(moves)

    if _is_physical_discomfort(normalized):
        return "Ủa đau kiểu âm ỉ hay quặn lên vậy? Nếu đau dữ, kèm sốt/nôn, hoặc khác hẳn bình thường thì đừng cố chịu một mình nha. Còn nếu chỉ khó chịu nhẹ, tớ nghe cậu than tiếp."
    if _is_diagnosis_request(normalized):
        return "Tớ không thể chẩn đoán cậu bị bệnh gì qua chat được. Nhưng tớ có thể giúp cậu tách triệu chứng, cảm giác và chuyện vừa xảy ra để xem bước an toàn tiếp theo là gì."
    if _is_reassurance_doubt(normalized):
        return "Tớ không thấy cậu ảo tưởng chỉ vì cậu đã hy vọng. Có thể đã có vài tín hiệu khiến cậu bám vào thật, nhưng mình cũng chưa kết luận thay người kia được; tớ tách cùng cậu phần dấu hiệu thật với phần tự suy ra nhé?"
    if _is_greeting_only(normalized):
        return "Tớ đây. Hôm nay cậu muốn kể gì trước?"
    if _is_short_social_emotion_ping(normalized):
        if any(_has_phrase(normalized, token) for token in ("chan", "buon", "nan", "te")):
            return "Ơ, nghe hơi tụt mood rồi đó. Kể tớ nghe: chán vì chuyện gì vậy?"
        if any(_has_phrase(normalized, token) for token in ("met", "duoi")):
            return "Nghe mệt thật. Cậu muốn than một chút hay cần tớ gỡ cùng một việc nhỏ trước?"
        return "Tớ đây. Hôm nay mood cậu đang thế nào?"
    if "dung" in normalized and len(normalized.split()) <= 4:
        return "Tớ nghe nè. Gọi Dũng là có mặt, cậu đang cần gỡ khúc nào trước?"
    if supportive_mode:
        context_line = _dung_context_line(user_message, pack)
        return f"{context_line} Tớ chậm lại một nhịp đã; phần nào đang nặng nhất ngay lúc này?"
    if advisor:
        context_line = _dung_context_line(user_message, pack)
        follow = _second_safe_advisor_sentence(moves)
        if follow and "?" in follow:
            return f"{context_line} Cái khó ở đây không chỉ là cảm xúc hiện tại, mà là vòng lặp khiến cậu thấy mất quyền điều khiển. {advisor} {follow}"
        return f"{context_line} Cái khó ở đây không chỉ là cảm xúc hiện tại, mà là vòng lặp khiến cậu thấy mất quyền điều khiển. {advisor} Tớ lấy một bước nhỏ trước nhé."
        return f"{context_line} {advisor} Tớ lấy một bước nhỏ trước nhé."
    if _is_asking_for_advice(user_message):
        context_line = _dung_context_line(user_message, pack)
        return f"{context_line} Tớ không quăng cả giáo trình đâu. {_dung_tiny_step(user_message, pack)}"
    if any(_has_phrase(normalized, token) for token in ("deadline", "han nop", "bai tap", "nop bai")):
        return "Deadline dí thì não dễ đứng hình thật. Cậu mở phần dễ nhất làm 10 phút trước đã, xong tớ tính tiếp với cậu."
    if any(_has_phrase(normalized, token) for token in ("overthinking", "nghi nhieu", "lo qua")):
        return "Overthinking đang kéo cậu chạy vòng vòng rồi. Tớ với cậu chốt một điều chắc chắn đang xảy ra trước nhé."
    context_line = _dung_context_line(user_message, pack)
    return f"{context_line} {_dung_tiny_step(user_message, pack)}"


def _dat_response(user_message: str, moves: list[str], supportive_mode: bool, pack: ContextPack) -> str:
    normalized = _ascii_fold(user_message)
    recent_messages, active_memory = _response_context(pack)
    anchor = _topic_anchor(user_message, recent_messages=recent_messages, active_memory=active_memory).replace("cậu", "bạn")
    advisor = _safe_advisor_sentence(moves)

    if _is_physical_discomfort(normalized):
        return "Bạn đau kiểu âm ỉ hay quặn lên? Nếu đau dữ, kèm sốt/nôn, hoặc khác hẳn bình thường, bạn nên tìm người gần mình hoặc hỗ trợ y tế thay vì cố chịu."
    if _is_diagnosis_request(normalized):
        return "Tôi không thể chẩn đoán bạn bị bệnh gì qua chat. Điều tôi có thể làm là cùng bạn tách dấu hiệu đang có, mức độ ảnh hưởng, và bước an toàn nên làm tiếp."
    if _is_reassurance_doubt(normalized):
        return "Tôi không nghĩ chỉ vì bạn hy vọng mà có thể gọi là ảo tưởng. Có thể đã có vài tín hiệu khiến bạn tin vào một khả năng, nhưng ta vẫn nên tách dữ kiện thật khỏi phần mình đang diễn giải."
    if _is_greeting_only(normalized):
        return "Tôi đây. Hôm nay bạn muốn cùng tôi nhìn rõ chuyện gì?"
    if _is_short_social_emotion_ping(normalized):
        if any(_has_phrase(normalized, token) for token in ("chan", "buon", "nan", "te")):
            return "Tôi nghe bạn đang chùng xuống một chút. Chuyện gì làm bạn thấy chán nhất lúc này?"
        if any(_has_phrase(normalized, token) for token in ("met", "duoi")):
            return "Tôi nghe bạn đang mệt. Ta bắt đầu từ một phần nhỏ nhất đang làm bạn đuối trước nhé?"
        return "Tôi đây. Hôm nay trạng thái của bạn đang nghiêng về phía nào?"
    if "dat" in normalized and len(normalized.split()) <= 4:
        return "Tôi nghe bạn. Có điều gì đang cần một góc nhìn bình tĩnh hơn không?"
    if supportive_mode:
        return f"Tôi nghe {anchor} đang làm bạn nặng lòng. Trước khi phân tích, ta giữ mọi thứ chậm lại một chút: điều nào đang đè lên bạn nhiều nhất?"
    if advisor:
        return f"{anchor.capitalize()} có vẻ không chỉ là một cảm xúc thoáng qua. {advisor} Điều quan trọng là chọn một điểm tựa nhỏ để bạn lấy lại quyền chủ động."
    if _is_asking_for_advice(user_message):
        return f"Tôi nghĩ với {anchor}, ta nên tách cảm xúc khỏi quyết định. Bạn hãy viết ra một điều chắc chắn, một điều chỉ là giả định, rồi chọn bước ít rủi ro nhất."
    return f"Tôi nghe {anchor}. Có lẽ trước mắt chưa cần kết luận vội; bạn nói phần đang mắc nhất, rồi ta cùng nhìn nó rõ hơn."


def _hau_response(user_message: str, moves: list[str], supportive_mode: bool, pack: ContextPack) -> str:
    normalized = _ascii_fold(user_message)
    recent_messages, active_memory = _response_context(pack)
    anchor = _topic_anchor(user_message, recent_messages=recent_messages, active_memory=active_memory).replace("cậu", "bạn")
    advisor = _safe_advisor_sentence(moves)

    if _is_physical_discomfort(normalized):
        return "đau kiểu âm ỉ hay quặn lên vậy? nếu đau dữ, kèm sốt/nôn, hoặc khác hẳn bình thường thì bạn đừng cố chịu một mình nha. còn nếu chỉ khó chịu nhẹ, mình nghe bạn than tiếp."
    if _is_diagnosis_request(normalized):
        return "mình không chẩn đoán bạn bị bệnh gì qua chat được. mình chỉ giúp bạn nhìn lại dấu hiệu đang có và chọn bước an toàn tiếp theo thôi."
    if _is_reassurance_doubt(normalized):
        return "mình chưa muốn gọi đó là ảo tưởng. có thể đã có vài tín hiệu làm bạn hy vọng, chỉ là mình chưa kết luận thay người kia được."
    if _is_greeting_only(normalized):
        return "Mình đây. Bạn cứ nói ngắn thôi cũng được, mình nghe."
    if _is_short_social_emotion_ping(normalized):
        if any(_has_phrase(normalized, token) for token in ("chan", "buon", "nan", "te")):
            return "Ừm, nghe hơi chán thật. Bạn thả một ý ngắn thôi cũng được: chán vì chuyện gì vậy?"
        if any(_has_phrase(normalized, token) for token in ("met", "duoi")):
            return "Nghe đuối quá. Bạn không cần kể mạch lạc đâu, nói một mẩu nhỏ trước là được."
        return "Mình đây. Hôm nay bạn đang thấy thế nào?"
    if "hau" in normalized and len(normalized.split()) <= 4:
        return "Hậu nghe nè. Nếu lười gõ dài thì thả từng ý một cũng được."
    if supportive_mode:
        return f"Mình nghe {anchor} đang làm bạn căng quá. Không cần nhắn cho mạch lạc đâu, bạn cứ thả một ý ngắn nhất trước."
    if advisor:
        return f"Ừm, {anchor} nghe mệt thật. {advisor} Làm một bước bé thôi, kiểu đủ để não bớt chạy vòng vòng."
    if any(_has_phrase(normalized, token) for token in ("overthinking", "nghi nhieu", "lo qua", "lo au")):
        return "Não bạn đang mở hơi nhiều tab rồi đó. Mình ngồi đây với bạn, mình chỉ cần bạn nói một điều thật sự xảy ra, còn mấy điều não tự suy diễn thì để lát xử sau."
    return f"Mình nghe {anchor}. Bạn cứ kể lộn xộn cũng được, mình lọc cùng bạn từ từ."


class FriendAgent:
    def _style_strength(self, pack: ContextPack) -> float:
        try:
            return float(pack.safety_policy.persona_style_strength)
        except Exception:
            return 0.6

    @staticmethod
    def _collect_safe_moves(advice: Iterable[AdvisorAdvice]) -> list[str]:
        out: list[str] = []
        for item in advice:
            for move in item.suggested_response_moves:
                m = _clean_move(move)
                if not m:
                    continue
                folded = _ascii_fold(m)
                if any(token in folded for token in _LEAKY_TERMS):
                    continue
                if re.fullmatch(r"[a-z0-9_]+", folded) and "_" in folded:
                    continue
                out.append(m)
                if len(out) >= 2:
                    return out
        return out

    @staticmethod
    def _shape_response(
        *,
        user_message: str,
        moves: list[str],
        supportive_mode: bool,
        persona_id: str,
        context_pack: ContextPack,
    ) -> str:
        persona_id = resolve_alias(persona_id)
        if persona_id == "dat_le":
            return _dat_response(user_message, moves, supportive_mode, context_pack)
        if persona_id == "hau_luong":
            return _hau_response(user_message, moves, supportive_mode, context_pack)
        return _dung_response(user_message, moves, supportive_mode, context_pack)

    @staticmethod
    def _enforce_must_avoid(text: str, must_avoid: list[str], *, persona_id: str) -> str:
        lowered = _ascii_fold(text)
        persona_id = resolve_alias(persona_id)
        if "diagnosis" in must_avoid or "diagnosis_or_disorder_probability" in must_avoid:
            if _DIAGNOSIS_RE.search(lowered):
                return (
                    "Tôi ở đây với bạn. Tôi muốn hiểu rõ hơn điều đang làm bạn nặng nhất lúc này."
                    if persona_id == "dat_le"
                    else "Mình ở đây với bạn. Bạn kể thêm một chút về phần đang nặng nhất lúc này nhé?"
                )
        if any(token in lowered for token in _LEAKY_TERMS):
            return (
                "Tôi ở đây với bạn. Bạn kể thêm một chút về điều đang vướng nhất nhé?"
                if persona_id == "dat_le"
                else "Mình ở đây với bạn. Bạn kể thêm một chút về điều đang vướng nhất nhé?"
            )
        return text

    def compose(
        self,
        *,
        user_message: str,
        context_pack: ContextPack,
        advisor_advice: list[AdvisorAdvice] | None = None,
    ) -> FriendAgentOutput:
        advice = [a for a in (advisor_advice or []) if a.should_use]
        safe_moves = self._collect_safe_moves(advice)
        supportive_mode = context_pack.safety_policy.policy_action in {"supportive_continuation", "constrain_response"}
        persona_context = context_pack.persona_context if isinstance(context_pack.persona_context, dict) else {}
        persona_id = resolve_alias(str(persona_context.get("selected") or "dung_luong"))

        final_text = self._shape_response(
            user_message=user_message,
            moves=safe_moves,
            supportive_mode=supportive_mode,
            persona_id=persona_id,
            context_pack=context_pack,
        )
        final_text = self._enforce_must_avoid(final_text, context_pack.safety_policy.must_avoid, persona_id=persona_id)

        if self._style_strength(context_pack) < 0.3:
            final_text = re.sub(r"\s{2,}", " ", final_text).strip()
            final_text = final_text[:260]

        verdict = validate_final_response(final_text, surface="chat", policy_decision=context_pack.safety_policy)
        if verdict.verdict != "allow":
            if persona_id == "dat_le":
                final_text = "Tôi nghe bạn. Hãy nói phần đang làm bạn vướng nhất, rồi ta nhìn nó từng bước."
            elif persona_id == "hau_luong":
                final_text = "mình nghe nè. bạn nói một ý ngắn trước thôi, mình lọc cùng bạn từ từ."
            else:
                final_text = "tớ nghe nè. cậu nói phần đang mắc nhất trước thôi, tớ bám theo chuyện đó với cậu."

        risk_level = context_pack.safety_policy.risk_level if context_pack.safety_policy else 0
        distress_score = context_pack.safety_policy.distress_score if context_pack.safety_policy else 0.0

        # tts_candidate: short voice script derived from final_text.
        # Suppressed for high-risk turns; only emit when text is substantive.
        tts_candidate: dict | None = None
        if risk_level < 3 and distress_score < 0.70 and len(final_text) >= 20:
            sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", final_text) if s.strip()]
            voice_text = " ".join(sentences[:2]) if sentences else final_text[:160]
            tts_candidate = {"voice_text": voice_text, "source": "friend_finalizer"}

        # meme_candidate: reason code hint for meme selection.
        # Suppressed for any elevated/high-risk distress. Only for lighthearted low-risk context.
        meme_candidate: str | None = None
        if risk_level < 2 and distress_score < 0.45:
            user_lower = user_message.lower()
            if any(k in user_lower for k in ("meme", "vui", "cuoi", "cười", "hai", "funny", "mood")):
                meme_candidate = "playful_low_risk"

        return FriendAgentOutput(
            final_text=final_text,
            response_intent="reflect",
            used_advisor_ids=[a.advisor_id for a in advice],
            used_resource_ids=[],
            suggested_next_action=None,
            memory_write_candidates=[],
            tts_candidate=tts_candidate,
            meme_candidate=meme_candidate,
            confidence=0.78 if advice else 0.7,
        )
