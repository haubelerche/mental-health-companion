import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.review_pr import _smart_truncate


def _file(name: str, body_size: int, char: str = "x") -> str:
    return f"diff --git a/{name} b/{name}\n" + char * body_size + "\n"


def test_no_truncation_when_within_limit():
    diff = _file("foo.py", 100)
    assert _smart_truncate(diff, 10_000) == diff


def test_returns_unchanged_at_exact_limit():
    diff = _file("foo.py", 100)
    assert _smart_truncate(diff, len(diff)) == diff


def test_omits_second_file():
    file1 = _file("a.py", 40)
    file2 = _file("b.py", 40)
    result = _smart_truncate(file1 + file2, len(file1) + 10)
    assert file1 in result
    assert "[diff truncated" in result
    assert "b.py" in result


def test_first_file_not_in_omitted_list():
    file1 = _file("a.py", 40)
    file2 = _file("b.py", 40)
    result = _smart_truncate(file1 + file2, len(file1) + 10)
    assert "a.py" not in result.split("[diff truncated")[1]


def test_omitted_char_count_is_accurate():
    file1 = _file("a.py", 40)
    file2 = _file("b.py", 40)
    diff = file1 + file2
    result = _smart_truncate(diff, len(file1) + 10)
    expected_omitted = len(diff) - len(file1)
    assert f"({expected_omitted} chars)" in result


def test_fallback_hard_truncates_single_oversized_file():
    diff = _file("big.py", 200)
    max_chars = 50
    result = _smart_truncate(diff, max_chars)
    assert result.startswith(diff[:max_chars])
    assert "[diff truncated" in result  # notice appended even with no omitted files
    assert "omitted from first file" in result


def test_fallback_omitted_list_excludes_truncated_file():
    file1 = _file("big.py", 200)
    file2 = _file("other.py", 200)
    diff = file1 + file2
    result = _smart_truncate(diff, 50)
    # big.py is partially included (fallback), other.py is omitted
    assert "other.py" in result
    assert "[diff truncated" in result


def test_filename_with_spaces():
    name = "my file.py"
    diff = f"diff --git a/{name} b/{name}\n" + "x" * 200
    result = _smart_truncate(diff, 50)
    assert "my file.py" in result


def test_malformed_diff_header_uses_unknown():
    diff = "not a real diff header\n" + "x" * 200
    max_chars = 50
    # Won't split on file boundary — treated as one chunk, fallback truncates
    result = _smart_truncate(diff, max_chars)
    assert result.startswith(diff[:max_chars])
    assert "[diff truncated" in result


def test_multiple_files_omitted():
    files = [_file(f"f{i}.py", 30) for i in range(5)]
    diff = "".join(files)
    result = _smart_truncate(diff, len(files[0]) + 10)
    assert "f1.py" in result
    assert "f2.py" in result
    assert "f3.py" in result
    assert "f4.py" in result
    assert "4 file(s) omitted" in result


def test_empty_diff():
    assert _smart_truncate("", 1000) == ""


def test_whitespace_only_diff():
    diff = "   \n\n  "
    assert _smart_truncate(diff, 1000) == diff
