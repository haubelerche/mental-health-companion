"""Cold-start screener to infer initial emotional profile for new users."""

from __future__ import annotations

import json
import logging
import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).parent.parent.parent / "data"
_ANCHORS_PATH = _DATA_DIR / "emotion_anchors.json"
_CENTROIDS_PATH = _DATA_DIR / "emotion_centroids.pkl"
_EMBED_MODEL = "text-embedding-3-small"

_EMOTION_DELTAS = {
    "sadness": 0.18,
    "fear": 0.12,
    "anger": 0.08,
    "joy": -0.10,
    "achievement": -0.08,
    "bonding": -0.05,
    "exercise": -0.05,
}

_EMOTION_TRAITS = {
    "sadness": {
        "preferred_tone": "empathetic",
        "communication_style": "lang nghe truoc, de xuat nhe sau",
    },
    "fear": {
        "preferred_tone": "reassuring",
        "communication_style": "chia buoc nho, khong don dap",
    },
    "anger": {
        "preferred_tone": "calm_validation",
        "communication_style": "xac nhan cam xuc truoc khi chuyen huong",
    },
    "joy": {
        "preferred_tone": "celebratory",
        "communication_style": "khuyech dai dieu tich cuc",
    },
    "achievement": {
        "preferred_tone": "affirming",
        "communication_style": "cu cung co diem manh va da tien bo",
    },
    "bonding": {
        "preferred_tone": "warm",
        "communication_style": "uu tien ket noi xa hoi va nguon luc xung quanh",
    },
    "exercise": {
        "preferred_tone": "energetic",
        "communication_style": "khuyen khich duy tri coping co san",
    },
}


@dataclass
class ColdStartProfile:
    detected_emotions: list[str]
    distress_delta: float
    warm_traits: dict[str, str]
    screening_note: str


class ColdStartScreener:
    _instance: "ColdStartScreener | None" = None

    def __init__(self) -> None:
        self._anchors: dict[str, list[str]] = {}
        self._centroids: dict[str, Any] = {}
        self._load_data()

    @classmethod
    def instance(cls) -> "ColdStartScreener":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_data(self) -> None:
        if _ANCHORS_PATH.exists():
            try:
                with open(_ANCHORS_PATH, "r", encoding="utf-8") as fh:
                    self._anchors = dict(json.load(fh) or {})
            except Exception as exc:
                logger.warning("cold-start screener: failed loading anchors: %s", exc)
        if _CENTROIDS_PATH.exists():
            try:
                with open(_CENTROIDS_PATH, "rb") as fh:
                    self._centroids = dict(pickle.load(fh) or {})
            except Exception as exc:
                logger.warning("cold-start screener: failed loading centroids: %s", exc)

    def _heuristic_emotions(self, normalized: str) -> list[str]:
        rules = [
            ("sadness", ("buon", "vo nghia", "bat luc", "chan nan", "co don", "trong rong")),
            ("fear", ("so", "lo", "hoang", "bat an", "panic", "worried")),
            ("anger", ("tuc", "gian", "uc che", "frustrated", "cay", "met qua")),
            ("joy", ("vui", "hanh phuc", "nhe nhom", "on hon", "tot len")),
            ("achievement", ("lam duoc", "hoan thanh", "dat duoc", "tu hao", "progress")),
            ("bonding", ("ban be", "gia dinh", "nguoi yeu", "duoc ho tro", "ket noi")),
            ("exercise", ("tap", "the duc", "chay bo", "yoga", "van dong")),
        ]
        found: list[str] = []
        for label, keywords in rules:
            if any(key in normalized for key in keywords):
                found.append(label)
        return found[:2]

    def _pick_traits(self, emotion: str) -> dict[str, str]:
        return dict(_EMOTION_TRAITS.get(emotion) or {"preferred_tone": "empathetic", "communication_style": "lang nghe va dong hanh"})

    def _profile_from_emotions(self, emotions: list[str]) -> ColdStartProfile:
        if not emotions:
            return ColdStartProfile(
                detected_emotions=[],
                distress_delta=0.0,
                warm_traits={"preferred_tone": "empathetic", "communication_style": "lang nghe va hoi mo tung buoc"},
                screening_note="Cold-start screening: chua du tin hieu, giu tone dong hanh an toan.",
            )
        primary = emotions[0]
        delta = sum(_EMOTION_DELTAS.get(item, 0.0) for item in emotions[:2])
        traits = self._pick_traits(primary)
        note = f"Cold-start screening: phat hien cam xuc uu tien {', '.join(emotions[:2])}."
        return ColdStartProfile(
            detected_emotions=emotions[:2],
            distress_delta=float(delta),
            warm_traits=traits,
            screening_note=note,
        )

    def _embedding_emotion(self, text: str, api_key: str) -> list[str]:
        if not self._centroids or not api_key.strip():
            return []
        try:
            import numpy as np
            from openai import OpenAI

            client = OpenAI(api_key=api_key, timeout=2.5)
            resp = client.embeddings.create(model=_EMBED_MODEL, input=[text[:512]])
            query = np.array(resp.data[0].embedding, dtype=np.float32)
            query_norm = float(np.linalg.norm(query))
            if query_norm == 0.0:
                return []
            scores: list[tuple[str, float]] = []
            for label, centroid in self._centroids.items():
                c_vec = np.array(centroid, dtype=np.float32)
                c_norm = float(np.linalg.norm(c_vec))
                if c_norm == 0.0:
                    continue
                sim = float((query @ c_vec) / (query_norm * c_norm + 1e-9))
                scores.append((label, sim))
            if not scores:
                return []
            scores.sort(key=lambda pair: pair[1], reverse=True)
            top = [scores[0][0]]
            if len(scores) > 1 and scores[1][1] >= scores[0][1] - 0.04:
                top.append(scores[1][0])
            return top
        except Exception as exc:
            logger.debug("cold-start screener embedding fallback: %s", exc)
            return []

    def screen(self, user_message: str, *, api_key: str = "") -> ColdStartProfile:
        normalized = " ".join((user_message or "").lower().split())
        if not normalized:
            return self._profile_from_emotions([])

        heuristic = self._heuristic_emotions(normalized)
        if heuristic:
            return self._profile_from_emotions(heuristic)

        from_embedding = self._embedding_emotion(user_message, api_key)
        return self._profile_from_emotions(from_embedding)
