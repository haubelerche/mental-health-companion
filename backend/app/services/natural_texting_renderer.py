"""Final rendering helpers for natural Vietnamese texting style."""

from __future__ import annotations

import re

from app.services.safety_output_validator import count_questions
from app.services.vietnamese_style_controller import VietnameseChatStyleState

_MARKDOWN_RE = re.compile(r"(```[\s\S]*?```|[*_#>\[\]]|^\s*[-+]\s+)", re.MULTILINE)
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?。！？])\s+")
_PROPER_STARTS = {"OpenAI", "Serene", "ChatGPT", "API", "SQL", "UI", "UX", "DSM-5", "CBT"}

_ROBOTIC_REWRITES: tuple[tuple[str, str], ...] = (
    ("Tôi rất tiếc khi nghe rằng bạn đang trải qua một khoảng thời gian khó khăn.", "ừ, nghe đoạn này nặng thật."),
    ("Tôi hiểu rằng bạn đang cảm thấy rất buồn và áp lực.", "ừ, nghe như bạn đang bị đè bởi nhiều thứ cùng lúc."),
    ("Bạn đã rất can đảm khi chia sẻ điều này.", "cảm ơn bạn vì đã nói thật với mình."),
    ("Bạn thật dũng cảm khi chia sẻ", "cảm ơn bạn vì đã nói thật đoạn này với mình"),
    ("Bạn không đơn độc trong cảm giác này.", "mình đang nghe bạn đây, không cần nói cho thật gọn hay thật đúng đâu."),
    ("Hãy thử hít thở sâu để bình tĩnh lại.", "mình kéo mọi thứ chậm lại một chút nhé. bạn thử thở ra dài hơn một nhịp thôi."),
    ("Cảm xúc của bạn là hoàn toàn hợp lệ.", "nghe vậy thì phản ứng của bạn có lý trong hoàn cảnh này."),
    ("Tôi luôn ở đây để hỗ trợ bạn.", "mình nghe tiếp được."),
    ("Mọi chuyện rồi sẽ " + "ổn.", "mình chưa vội kết luận gì lớn lúc này."),
    ("Mọi chuyện rồi sẽ " + "ổn thôi.", "mình chưa vội kết luận gì lớn lúc này."),
    ("Bạn có muốn chia sẻ " + "thêm không?", "mình nghe tiếp được, theo đoạn bạn thấy dễ nói nhất."),
    ("Cậu cứ thả tiếp một mẫu " + "cụ thể nhất", "cậu nói đoạn nào còn mắc trong đầu trước cũng được"),
    ("Cậu cứ thả tiếp một mẩu " + "cụ thể nhất", "cậu nói đoạn nào còn mắc trong đầu trước cũng được"),
    ("không trôi " + "mất đoạn này đâu", "mình bám theo đoạn này với bạn"),
)


def rewrite_anti_robotic_phrases(text: str) -> str:
    rendered = text or ""
    for source, target in _ROBOTIC_REWRITES:
        rendered = re.sub(re.escape(source), target, rendered, flags=re.IGNORECASE)
    rendered = rendered.replace(
        "cảm ơn bạn vì đã nói thật với mình.",
        "nói thật đoạn này không dễ, cảm ơn bạn vì đã nói với mình.",
    )
    return rendered


def strip_chat_markdown(text: str) -> str:
    return _MARKDOWN_RE.sub("", text or "").strip()


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in _SENTENCE_SPLIT_RE.split(text.strip()) if part.strip()]


def cap_sentences(text: str, max_sentences: int) -> str:
    parts = _sentences(text)
    if len(parts) <= max_sentences:
        return text.strip()
    return " ".join(parts[:max_sentences]).strip()


def cap_questions(text: str, max_questions: int) -> str:
    if count_questions(text) <= max_questions:
        return text.strip()
    kept: list[str] = []
    questions = 0
    for sentence in _sentences(text):
        q_count = count_questions(sentence)
        if questions + q_count > max_questions:
            continue
        kept.append(sentence)
        questions += q_count
    return " ".join(kept).strip() or text.split("?", 1)[0].strip()


def allow_lowercase_sentence_openings(text: str, *, preserve_proper_nouns: bool = True) -> str:
    def lower_one(sentence: str) -> str:
        if not sentence:
            return sentence
        first_word = sentence.split(maxsplit=1)[0].strip(".,;:!?")
        if preserve_proper_nouns and (first_word in _PROPER_STARTS or (first_word.isascii() and first_word.isupper())):
            return sentence
        return sentence[0].lower() + sentence[1:] if sentence[0].isupper() else sentence

    return " ".join(lower_one(sentence) for sentence in _sentences(text))


def render_final_text(text: str, *, style: VietnameseChatStyleState, emotional_chat: bool = True) -> str:
    rendered = rewrite_anti_robotic_phrases(text)
    if emotional_chat:
        rendered = strip_chat_markdown(rendered)
    rendered = re.sub(r"\s+", " ", rendered).strip()
    rendered = cap_questions(rendered, style.max_questions)
    rendered = cap_sentences(rendered, style.max_sentences)
    if style.lowercase_chat_allowed and not style.sentence_initial_uppercase_required:
        rendered = allow_lowercase_sentence_openings(
            rendered,
            preserve_proper_nouns=style.preserve_proper_nouns,
        )
    return rendered.strip()
