#!/usr/bin/env python3
"""
One-time preprocessing script: downloads MentalChat16K from HuggingFace,
selects diverse high-quality examples, and pre-computes OpenAI embeddings
so the runtime retriever can do instant cosine-similarity search.

Usage:
    cd backend
    pip install datasets
    OPENAI_API_KEY=sk-... python scripts/preprocess_mentalchat.py

Output:
    backend/data/mental_chat_examples.jsonl   – curated Q&A examples
    backend/data/mental_chat_embeddings.pkl   – numpy float32 embeddings
"""

from __future__ import annotations

import json
import os
import pickle
import random
import sys
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
EXAMPLES_PATH = DATA_DIR / "mental_chat_examples.jsonl"
EMBEDDINGS_PATH = DATA_DIR / "mental_chat_embeddings.pkl"

SAMPLE_SIZE = 800
EMBED_BATCH = 100
EMBED_MODEL = "text-embedding-3-small"

# Minimum response length to filter out low-quality examples
MIN_RESPONSE_WORDS = 20


def load_dataset_examples() -> list[dict[str, str]]:
    try:
        from datasets import load_dataset
    except ImportError:
        print("ERROR: 'datasets' library not installed. Run: pip install datasets")
        sys.exit(1)

    print("Loading ShenLab/MentalChat16K from HuggingFace …")
    ds = load_dataset("ShenLab/MentalChat16K")
    split_name = "train" if "train" in ds else list(ds.keys())[0]
    data = ds[split_name]
    print(f"  Split '{split_name}': {len(data)} rows — columns: {data.column_names}")
    return list(data)


def normalize_example(item: dict) -> dict[str, str] | None:
    """Map various column schemas to {instruction, response}."""
    instruction = (
        item.get("instruction")
        or item.get("input")
        or item.get("question")
        or item.get("Context")
        or ""
    ).strip()
    response = (
        item.get("output")
        or item.get("response")
        or item.get("answer")
        or item.get("Response")
        or ""
    ).strip()
    if not instruction or not response:
        return None
    if len(response.split()) < MIN_RESPONSE_WORDS:
        return None
    return {
        "instruction": instruction[:600],
        "response": response[:700],
    }


def curate_examples(raw: list[dict]) -> list[dict[str, str]]:
    random.seed(42)
    random.shuffle(raw)
    normalized = [n for item in raw if (n := normalize_example(item)) is not None]
    selected = normalized[:SAMPLE_SIZE]
    print(f"Curated {len(selected)} examples (from {len(normalized)} valid)")
    return selected


def save_examples(examples: list[dict[str, str]]) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    with open(EXAMPLES_PATH, "w", encoding="utf-8") as f:
        for item in examples:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"Saved examples → {EXAMPLES_PATH}")


def compute_embeddings(examples: list[dict[str, str]], api_key: str) -> None:
    try:
        from openai import OpenAI
    except ImportError:
        print("ERROR: 'openai' package not installed.")
        sys.exit(1)

    client = OpenAI(api_key=api_key)
    texts = [item["instruction"] for item in examples]
    all_embeddings: list[list[float]] = []

    print(f"Computing embeddings for {len(texts)} examples in batches of {EMBED_BATCH} …")
    for start in range(0, len(texts), EMBED_BATCH):
        batch = texts[start : start + EMBED_BATCH]
        resp = client.embeddings.create(model=EMBED_MODEL, input=batch)
        all_embeddings.extend([d.embedding for d in resp.data])
        done = min(start + EMBED_BATCH, len(texts))
        print(f"  [{done}/{len(texts)}] embedded")

    with open(EMBEDDINGS_PATH, "wb") as f:
        pickle.dump(all_embeddings, f)
    print(f"Saved embeddings → {EMBEDDINGS_PATH}")


def main() -> None:
    api_key = os.environ.get("OPENAI_API_KEY") or ""
    if not api_key:
        print(
            "WARNING: OPENAI_API_KEY not set — examples will be saved but embeddings "
            "will be computed on the fly at first runtime query (slower first request)."
        )

    raw = load_dataset_examples()
    examples = curate_examples(raw)
    save_examples(examples)

    if api_key:
        compute_embeddings(examples, api_key)
    else:
        print("Skipping embedding pre-computation (no API key).")

    print("\nDone! Now restart the backend server to activate MentalChat retriever.")


if __name__ == "__main__":
    main()
