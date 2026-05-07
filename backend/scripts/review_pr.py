from __future__ import annotations

import re


_HEADER_RE = re.compile(r"^diff --git a/(.+?) b/(.+)$", re.MULTILINE)


def _file_name(chunk: str) -> str:
    m = _HEADER_RE.search(chunk)
    if not m:
        return "unknown"
    return m.group(1)


def _split_files(diff_text: str) -> list[str]:
    if not diff_text:
        return []
    starts = [m.start() for m in _HEADER_RE.finditer(diff_text)]
    if not starts:
        return [diff_text]
    parts: list[str] = []
    for i, s in enumerate(starts):
        e = starts[i + 1] if i + 1 < len(starts) else len(diff_text)
        parts.append(diff_text[s:e])
    return parts


def _smart_truncate(diff_text: str, max_chars: int) -> str:
    if len(diff_text) <= max_chars:
        return diff_text

    chunks = _split_files(diff_text)
    if not chunks:
        return diff_text

    kept: list[str] = []
    omitted_files: list[str] = []
    used = 0

    for i, chunk in enumerate(chunks):
        chunk_len = len(chunk)
        if used + chunk_len <= max_chars:
            kept.append(chunk)
            used += chunk_len
            continue
        if i == 0:
            omitted_files = [_file_name(c) for c in chunks[1:]]
            omitted_chars = len(diff_text) - max_chars
            note = (
                f"\n[diff truncated: {len(omitted_files)} file(s) omitted "
                f"({omitted_chars} chars); omitted from first file: {_file_name(chunk)}"
            )
            if omitted_files:
                note += f"; omitted files: {', '.join(omitted_files)}"
            note += "]"
            return diff_text[:max_chars] + note

        omitted_files = [_file_name(c) for c in chunks[i:]]
        omitted_chars = len(diff_text) - used
        note = (
            f"\n[diff truncated: {len(omitted_files)} file(s) omitted "
            f"({omitted_chars} chars); omitted files: {', '.join(omitted_files)}]"
        )
        return "".join(kept) + note

    return "".join(kept)
