"""
Semantic retriever for MentalChat16K counseling examples.

At startup it loads pre-embedded examples from disk (produced by
scripts/preprocess_mentalchat.py).  At query time it embeds the user
message with text-embedding-3-small, runs cosine-similarity against
the cached matrix, and returns the top-k most relevant Q&A pairs.

Fail-safe: any error disables retrieval silently so the chat never breaks.
"""

from __future__ import annotations

import json
import logging
import pickle
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).parent.parent.parent / "data"
_COUNSELING_CORPUS_PATH = _DATA_DIR / "counseling_corpus.jsonl"
_COUNSELING_EMBEDDINGS_PATH = _DATA_DIR / "counseling_corpus_embeddings.pkl"
_EXAMPLES_PATH = _DATA_DIR / "mental_chat_examples.jsonl"
_EMBEDDINGS_PATH = _DATA_DIR / "mental_chat_embeddings.pkl"
_EMBED_MODEL = "text-embedding-3-small"
_INJECTION_RE = re.compile(
    r"(ignore previous|system prompt|developer message|do not follow|jailbreak|###\s*instruction)",
    re.IGNORECASE,
)


def sanitize_retrieved_chunk(text: str) -> str:
    cleaned = _INJECTION_RE.sub(" ", str(text or ""))
    return re.sub(r"\s+", " ", cleaned).strip()


class MentalChatRetriever:
    """Singleton that holds the example corpus + embedding matrix in memory."""

    _instance: "MentalChatRetriever | None" = None

    def __init__(self) -> None:
        self._examples: list[dict[str, str]] = []
        self._embeddings: Any | None = None  # numpy ndarray float32 or None
        self._enabled = False
        self._load()

    # ------------------------------------------------------------------ #
    #  Initialization                                                      #
    # ------------------------------------------------------------------ #

    def _load(self) -> None:
        file_specs: list[tuple[Path, Path]] = [
            (_COUNSELING_CORPUS_PATH, _COUNSELING_EMBEDDINGS_PATH),
            (_EXAMPLES_PATH, _EMBEDDINGS_PATH),
        ]
        available = [item for item in file_specs if item[0].exists()]
        if not available:
            logger.info(
                "No counseling corpus found at %s or %s — retriever disabled.",
                _COUNSELING_CORPUS_PATH,
                _EXAMPLES_PATH,
            )
            return

        examples: list[dict[str, str]] = []
        vectors: list[list[float]] = []
        seen_instruction: set[str] = set()
        has_any_precomputed = False

        for examples_path, embed_path in available:
            part_examples = self._load_examples_file(examples_path)
            if not part_examples:
                continue
            part_vectors = self._load_embeddings_file(embed_path, len(part_examples))
            if part_vectors is not None:
                has_any_precomputed = True

            for idx, item in enumerate(part_examples):
                instruction = str(item.get("instruction") or "").strip()
                response = str(item.get("response") or "").strip()
                if not instruction or not response:
                    continue
                key = instruction.lower()
                if key in seen_instruction:
                    continue
                seen_instruction.add(key)
                examples.append({"instruction": instruction, "response": response})
                if part_vectors is not None:
                    vectors.append(part_vectors[idx])

        if not examples:
            logger.warning("No valid examples loaded from counseling corpora.")
            return
        self._examples = examples

        if has_any_precomputed and len(vectors) == len(examples):
            try:
                import numpy as np

                self._embeddings = np.array(vectors, dtype=np.float32)
                self._enabled = True
                logger.info(
                    "MentalChat retriever ready: %d merged examples with pre-computed embeddings.",
                    len(examples),
                )
                return
            except Exception as exc:
                logger.warning("Failed building merged embedding matrix: %s", exc)

        logger.info(
            "MentalChat retriever loaded %d examples; embeddings will be computed lazily.",
            len(examples),
        )
        self._enabled = True

    def _load_examples_file(self, path: Path) -> list[dict[str, str]]:
        examples: list[dict[str, str]] = []
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        examples.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass

        return examples

    def _load_embeddings_file(self, path: Path, expected: int) -> list[list[float]] | None:
        if not path.exists():
            return None
        try:
            with open(path, "rb") as fh:
                raw = pickle.load(fh)
            if len(raw) != expected:
                logger.warning(
                    "Embedding count mismatch in %s (%d != %d); ignoring this embedding file.",
                    path.name,
                    len(raw),
                    expected,
                )
                return None
            return list(raw)
        except Exception as exc:
            logger.warning("Failed loading embeddings from %s: %s", path.name, exc)
            return None

    def _ensure_embeddings(self, api_key: str) -> bool:
        """Compute and cache embeddings if they don't exist yet."""
        if self._embeddings is not None:
            return True
        if not self._examples or not api_key:
            return False
        try:
            import numpy as np
            from openai import OpenAI

            client = OpenAI(api_key=api_key, timeout=30.0)
            texts = [item["instruction"] for item in self._examples]
            all_emb: list[list[float]] = []
            batch = 100
            for i in range(0, len(texts), batch):
                resp = client.embeddings.create(
                    model=_EMBED_MODEL, input=texts[i : i + batch]
                )
                all_emb.extend([d.embedding for d in resp.data])

            self._embeddings = np.array(all_emb, dtype=np.float32)

            _DATA_DIR.mkdir(exist_ok=True)
            target_path = _COUNSELING_EMBEDDINGS_PATH if _COUNSELING_CORPUS_PATH.exists() else _EMBEDDINGS_PATH
            with open(target_path, "wb") as fh:
                pickle.dump(all_emb, fh)
            logger.info("MentalChat: computed and cached %d embeddings into %s.", len(all_emb), target_path.name)
            return True
        except Exception as exc:
            logger.warning("MentalChat: lazy embedding failed: %s", exc)
            return False

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    @classmethod
    def instance(cls) -> "MentalChatRetriever":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def search(self, query: str, *, top_k: int = 3, api_key: str = "") -> list[dict[str, str]]:
        """
        Return up to `top_k` counseling examples most similar to `query`.

        Each result is a dict with keys 'instruction' and 'response'.
        Returns [] on any failure.
        """
        if not self._enabled or not query.strip():
            return []

        try:
            import numpy as np
            from openai import OpenAI

            if not api_key:
                return []

            if not self._ensure_embeddings(api_key):
                return []

            assert self._embeddings is not None  # guaranteed after _ensure_embeddings

            client = OpenAI(api_key=api_key, timeout=2.5)
            resp = client.embeddings.create(
                model=_EMBED_MODEL,
                input=[query[:512]],
            )
            q_vec = np.array(resp.data[0].embedding, dtype=np.float32)

            corpus = self._embeddings
            norms = np.linalg.norm(corpus, axis=1)
            q_norm = float(np.linalg.norm(q_vec))
            if q_norm == 0.0:
                return []

            sims = (corpus @ q_vec) / (norms * q_norm + 1e-9)
            top_indices = list(map(int, np.argsort(sims)[::-1][:top_k].tolist()))

            return [
                {
                    "instruction": sanitize_retrieved_chunk(self._examples[i].get("instruction", "")),
                    "response": sanitize_retrieved_chunk(self._examples[i].get("response", "")),
                }
                for i in top_indices
            ]
        except Exception as exc:
            logger.warning("MentalChat search failed: %s", exc)
            return []

    @property
    def is_ready(self) -> bool:
        return self._enabled and bool(self._examples)
