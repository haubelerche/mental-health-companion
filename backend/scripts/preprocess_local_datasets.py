#!/usr/bin/env python3
"""
Build local cold-start data artifacts from CSV datasets.

Inputs:
  - docs/mental_health.csv
  - docs/mental_health_2.csv
  - docs/Text Emotion Classification 150k Dataset.csv
  - optional backend/data/mental_chat_examples.jsonl (existing curated HF examples)

Outputs:
  - backend/data/counseling_corpus.jsonl
  - backend/data/counseling_corpus_embeddings.pkl
  - backend/data/emotion_anchors.json
  - backend/data/emotion_centroids.pkl
"""

from __future__ import annotations

import csv
import json
import os
import pickle
import random
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
DOCS_DIR = ROOT_DIR / "docs"
DATA_DIR = ROOT_DIR / "backend" / "data"

MENTAL_HEALTH_PATHS = [
    DOCS_DIR / "mental_health.csv",
    DOCS_DIR / "mental_health_2.csv",
]
EMOTION_DATASET_PATH = DOCS_DIR / "Text Emotion Classification 150k Dataset.csv"
MENTALCHAT_JSONL_PATH = DATA_DIR / "mental_chat_examples.jsonl"

COUNSELING_OUT_PATH = DATA_DIR / "counseling_corpus.jsonl"
COUNSELING_EMBED_PATH = DATA_DIR / "counseling_corpus_embeddings.pkl"
EMOTION_ANCHORS_PATH = DATA_DIR / "emotion_anchors.json"
EMOTION_CENTROIDS_PATH = DATA_DIR / "emotion_centroids.pkl"

EMBED_MODEL = "text-embedding-3-small"
COUNSELING_TARGET_SIZE = 1200
MIN_RESPONSE_WORDS = 30
MAX_CONTEXT_CHARS = 800
ANCHOR_SAMPLE_SIZE = 80
ANCHOR_CATEGORIES = [
    "sadness",
    "fear",
    "anger",
    "joy",
    "achievement",
    "bonding",
    "exercise",
]


def _clean_text(value: str) -> str:
    return " ".join(str(value or "").strip().split())


def _context_key(instruction: str, response: str) -> str:
    return f"{instruction.lower()}|||{response.lower()}"


def load_mental_health_pairs() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    for path in MENTAL_HEALTH_PATHS:
        if not path.exists():
            continue
        with open(path, "r", encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            for item in reader:
                instruction = _clean_text(item.get("Context", ""))
                response = _clean_text(item.get("Response", ""))
                if not instruction or not response:
                    continue
                if len(instruction) > MAX_CONTEXT_CHARS:
                    continue
                if len(response.split()) < MIN_RESPONSE_WORDS:
                    continue
                key = _context_key(instruction, response)
                if key in seen:
                    continue
                seen.add(key)
                rows.append(
                    {
                        "instruction": instruction[:MAX_CONTEXT_CHARS],
                        "response": response[:900],
                        "source": path.name,
                    }
                )
    return rows


def load_existing_mentalchat() -> list[dict[str, str]]:
    if not MENTALCHAT_JSONL_PATH.exists():
        return []
    rows: list[dict[str, str]] = []
    with open(MENTALCHAT_JSONL_PATH, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            instruction = _clean_text(item.get("instruction", ""))
            response = _clean_text(item.get("response", ""))
            if instruction and response:
                rows.append(
                    {
                        "instruction": instruction[:MAX_CONTEXT_CHARS],
                        "response": response[:900],
                        "source": "mental_chat_examples.jsonl",
                    }
                )
    return rows


def curate_counseling_corpus() -> list[dict[str, str]]:
    random.seed(42)
    local_rows = load_mental_health_pairs()
    hf_rows = load_existing_mentalchat()
    merged = local_rows + hf_rows
    random.shuffle(merged)

    picked: list[dict[str, str]] = []
    seen_instruction: set[str] = set()
    for row in merged:
        instruction = row["instruction"]
        key = instruction.lower()
        if key in seen_instruction:
            continue
        seen_instruction.add(key)
        picked.append(row)
        if len(picked) >= COUNSELING_TARGET_SIZE:
            break
    return picked


def save_jsonl(path: Path, rows: list[dict[str, str]]) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        for row in rows:
            payload = {"instruction": row["instruction"], "response": row["response"], "source": row.get("source", "")}
            fh.write(json.dumps(payload, ensure_ascii=False) + "\n")


def load_emotion_anchors() -> dict[str, list[str]]:
    per_cat: dict[str, list[str]] = {name: [] for name in ANCHOR_CATEGORIES}
    if not EMOTION_DATASET_PATH.exists():
        return per_cat
    with open(EMOTION_DATASET_PATH, "r", encoding="utf-8", errors="ignore", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            category = _clean_text(row.get("category", "")).lower()
            if category not in per_cat:
                continue
            text = _clean_text(row.get("cleaned_text", "") or row.get("original_text", ""))
            if not text:
                continue
            per_cat[category].append(text[:500])
    random.seed(42)
    sampled: dict[str, list[str]] = {}
    for category, items in per_cat.items():
        random.shuffle(items)
        sampled[category] = items[:ANCHOR_SAMPLE_SIZE]
    return sampled


def _embed_texts(texts: list[str], api_key: str) -> list[list[float]]:
    from openai import OpenAI

    client = OpenAI(api_key=api_key, timeout=30.0)
    all_vectors: list[list[float]] = []
    batch = 100
    for idx in range(0, len(texts), batch):
        part = texts[idx : idx + batch]
        response = client.embeddings.create(model=EMBED_MODEL, input=part)
        all_vectors.extend([entry.embedding for entry in response.data])
        print(f"Embedded {min(idx + batch, len(texts))}/{len(texts)}")
    return all_vectors


def build_artifacts() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    corpus = curate_counseling_corpus()
    save_jsonl(COUNSELING_OUT_PATH, corpus)
    print(f"Saved counseling corpus: {COUNSELING_OUT_PATH} ({len(corpus)} rows)")

    anchors = load_emotion_anchors()
    with open(EMOTION_ANCHORS_PATH, "w", encoding="utf-8") as fh:
        json.dump(anchors, fh, ensure_ascii=False, indent=2)
    print(f"Saved emotion anchors: {EMOTION_ANCHORS_PATH}")

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        print("OPENAI_API_KEY not set; skipping embedding outputs.")
        return

    corpus_texts = [row["instruction"] for row in corpus]
    corpus_vectors = _embed_texts(corpus_texts, api_key)
    with open(COUNSELING_EMBED_PATH, "wb") as fh:
        pickle.dump(corpus_vectors, fh)
    print(f"Saved counseling embeddings: {COUNSELING_EMBED_PATH}")

    try:
        import numpy as np
    except Exception as exc:  # pragma: no cover
        print(f"NumPy missing, cannot compute centroids: {exc}")
        return

    centroids: dict[str, list[float]] = {}
    for category, texts in anchors.items():
        if not texts:
            continue
        vectors = _embed_texts(texts, api_key)
        matrix = np.array(vectors, dtype=np.float32)
        centroids[category] = matrix.mean(axis=0).tolist()
    with open(EMOTION_CENTROIDS_PATH, "wb") as fh:
        pickle.dump(centroids, fh)
    print(f"Saved emotion centroids: {EMOTION_CENTROIDS_PATH}")


if __name__ == "__main__":
    build_artifacts()
