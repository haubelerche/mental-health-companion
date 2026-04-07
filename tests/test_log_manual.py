import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scripts.log_manual import make_entry, save_entry, main


# ── make_entry ────────────────────────────────────────────────────────────────

def test_prompt_truncated_at_1000():
    entry = make_entry("chatgpt", "x" * 1500)
    assert len(entry["prompt"]) == 1000


def test_prompt_exact_limit_unchanged():
    entry = make_entry("chatgpt", "y" * 1000)
    assert len(entry["prompt"]) == 1000


def test_response_summary_truncated_at_500():
    entry = make_entry("chatgpt", "hello", response_summary="z" * 600)
    assert len(entry["response_summary"]) == 500


def test_entry_id_uniqueness():
    e1 = make_entry("chatgpt", "a")
    e2 = make_entry("chatgpt", "a")
    assert e1["entry_id"] != e2["entry_id"]


def test_entry_id_format():
    entry = make_entry("chatgpt", "test")
    assert entry["entry_id"].startswith("manual-")
    parts = entry["entry_id"].split("-")
    # manual-YYYYMMDD-HHMMSS-<hex8>
    assert len(parts) == 4
    assert len(parts[3]) == 8


def test_git_failure_returns_empty_strings():
    with patch("scripts.log_manual.git", return_value=""):
        entry = make_entry("chatgpt", "test")
    assert entry["repo"] == ""
    assert entry["branch"] == ""
    assert entry["commit"] == ""
    assert entry["student"] == ""


def test_empty_model_and_response():
    entry = make_entry("gemini-web", "q")
    assert entry["model"] == ""
    assert entry["response_summary"] == ""


# ── save_entry ────────────────────────────────────────────────────────────────

def test_save_entry_creates_directory(tmp_path):
    target = tmp_path / "nonexistent" / "nested"
    os.environ["AI_LOG_DIR"] = str(target)
    try:
        save_entry({"test": "data"})
        assert (target / "session.jsonl").exists()
    finally:
        del os.environ["AI_LOG_DIR"]


def test_save_entry_appends_not_overwrites(tmp_path):
    os.environ["AI_LOG_DIR"] = str(tmp_path)
    try:
        save_entry({"n": 1})
        save_entry({"n": 2})
        lines = (tmp_path / "session.jsonl").read_text(encoding="utf-8").splitlines()
        assert len(lines) == 2
        assert json.loads(lines[0])["n"] == 1
        assert json.loads(lines[1])["n"] == 2
    finally:
        del os.environ["AI_LOG_DIR"]


def test_save_entry_writes_valid_json(tmp_path):
    os.environ["AI_LOG_DIR"] = str(tmp_path)
    try:
        entry = make_entry("chatgpt", "hello")
        save_entry(entry)
        line = (tmp_path / "session.jsonl").read_text(encoding="utf-8").strip()
        parsed = json.loads(line)
        assert parsed["tool"] == "chatgpt"
    finally:
        del os.environ["AI_LOG_DIR"]


def test_save_entry_returns_path(tmp_path):
    os.environ["AI_LOG_DIR"] = str(tmp_path)
    try:
        result = save_entry({"x": 1})
        assert isinstance(result, Path)
        assert result.name == "session.jsonl"
    finally:
        del os.environ["AI_LOG_DIR"]


# ── main (CLI) ────────────────────────────────────────────────────────────────

def test_main_tool_without_prompt_exits(tmp_path):
    with patch("sys.argv", ["log_manual.py", "--tool", "chatgpt"]):
        with pytest.raises(SystemExit):
            main()


def test_main_tool_and_prompt_saves_entry(tmp_path):
    os.environ["AI_LOG_DIR"] = str(tmp_path)
    try:
        with patch("sys.argv", ["log_manual.py", "--tool", "chatgpt", "--prompt", "hello"]):
            main()
        lines = (tmp_path / "session.jsonl").read_text(encoding="utf-8").splitlines()
        assert len(lines) == 1
        assert json.loads(lines[0])["tool"] == "chatgpt"
    finally:
        del os.environ["AI_LOG_DIR"]


def test_main_neither_arg_falls_back_to_interactive(tmp_path):
    os.environ["AI_LOG_DIR"] = str(tmp_path)
    try:
        inputs = iter(["1", "my test prompt", ""])  # tool=chatgpt, prompt, model=empty
        with patch("sys.argv", ["log_manual.py"]), \
             patch("builtins.input", side_effect=inputs):
            main()
        lines = (tmp_path / "session.jsonl").read_text(encoding="utf-8").splitlines()
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["tool"] == "chatgpt"
        assert entry["prompt"] == "my test prompt"
    finally:
        del os.environ["AI_LOG_DIR"]


def test_main_interactive_empty_prompt_exits(tmp_path):
    inputs = iter(["1", ""])  # tool=chatgpt, empty prompt
    with patch("sys.argv", ["log_manual.py"]), \
         patch("builtins.input", side_effect=inputs):
        with pytest.raises(SystemExit):
            main()
