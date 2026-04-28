"""
Extract structured CBT knowledge from a large PDF into JSON.

Usage:
    python backend/app/data/scripts/extract_cbt_dummies.py \
        --input docs/cognitive-behavioural-therapy-for-dummies-copy.pdf \
        --output backend/app/data/data_raw/cbt_dummies_extracted.json \
        --chunk-pages 50 \
        --provider auto

Provider behavior:
- openai/anthropic: uses API key in environment.
- auto: tries OpenAI, then Anthropic.
- none: runs deterministic heuristic extraction (no API key required).
"""

from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pypdf import PdfReader

JSON_SCHEMA_HINT = {
    "cognitive_distortions": [
        {
            "slug": "string_snake_case",
            "name_en": "string",
            "definition_en": "string",
            "evidence": "short quote from source text",
            "confidence": 0.0,
        }
    ],
    "coping_actions": [
        {
            "action_id": "string_snake_case",
            "name_en": "string",
            "category_slug": "behavioral|cognitive|somatic|social",
            "targets_symptoms": ["symptom_slug"],
            "helps_with_disorders": ["disorder_slug"],
            "evidence": "short quote from source text",
            "confidence": 0.0,
        }
    ],
    "psych_processes": [
        {
            "slug": "string_snake_case",
            "name_en": "string",
            "definition_en": "string",
            "underlies_construct": "cognition|emotion|activity|communication|motivation",
            "psych_basis_for": ["symptom_slug"],
            "evidence": "short quote from source text",
            "confidence": 0.0,
        }
    ],
    "triggers": [
        {
            "slug": "string_snake_case",
            "name_en": "string",
            "manifests_as": ["symptom_slug"],
            "commonly_triggers_distortions": ["distortion_slug"],
            "evidence": "short quote from source text",
            "confidence": 0.0,
        }
    ],
}

PROMPT_TEMPLATE = """You are extracting clinical CBT knowledge from a psychology self-help PDF chunk.

Rules:
1) Return STRICT JSON only, no markdown.
2) Respect this schema exactly: {schema}
3) Keep only high-signal, reusable clinical concepts.
4) Use snake_case slugs/action_id.
5) Only include items present in the provided text chunk.
6) Provide concise evidence quote for every item.
7) Confidence is 0.0-1.0.

Known allowed symptom slugs:
insomnia, fatigue, anhedonia, low_mood, guilt, poor_concentration, appetite_change,
psychomotor_disturbance, suicidal_ideation, excessive_worry, irritability, tension,
social_withdrawal, hypervigilance

Known allowed disorder slugs:
mdd, pdd, gad, panic_disorder, social_anxiety_disorder, agoraphobia, specific_phobia,
ptsd, ocd, illness_anxiety, insomnia_disorder

TEXT CHUNK:
{chunk}
"""


@dataclass
class Chunk:
    start_page: int
    end_page: int
    text: str


def _read_pdf_chunks(pdf_path: Path, chunk_pages: int) -> list[Chunk]:
    reader = PdfReader(str(pdf_path))
    chunks: list[Chunk] = []
    current: list[str] = []
    start = 1

    for idx, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text() or ""
        page_text = re.sub(r"\s+\n", "\n", page_text)
        page_text = re.sub(r"\n{3,}", "\n\n", page_text)
        current.append(f"\n--- PAGE {idx} ---\n{page_text}")
        if idx % chunk_pages == 0:
            chunks.append(Chunk(start_page=start, end_page=idx, text="".join(current)))
            current = []
            start = idx + 1

    if current:
        chunks.append(Chunk(start_page=start, end_page=len(reader.pages), text="".join(current)))
    return chunks


def _openai_extract(chunk_text: str, model: str) -> dict[str, Any]:
    from openai import OpenAI

    client = OpenAI()
    prompt = PROMPT_TEMPLATE.format(schema=json.dumps(JSON_SCHEMA_HINT, ensure_ascii=False), chunk=chunk_text[:18000])
    resp = client.responses.create(
        model=model,
        input=prompt,
        temperature=0.0,
    )
    text = resp.output_text.strip()
    return json.loads(text)


def _anthropic_extract(chunk_text: str, model: str) -> dict[str, Any]:
    from anthropic import Anthropic

    client = Anthropic()
    prompt = PROMPT_TEMPLATE.format(schema=json.dumps(JSON_SCHEMA_HINT, ensure_ascii=False), chunk=chunk_text[:18000])
    resp = client.messages.create(
        model=model,
        max_tokens=4000,
        temperature=0.0,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(block.text for block in resp.content if getattr(block, "text", None)).strip()
    return json.loads(text)


def _snippet(text: str, term: str, window: int = 140) -> str:
    i = text.lower().find(term.lower())
    if i < 0:
        return ""
    start = max(0, i - window)
    end = min(len(text), i + len(term) + window)
    return re.sub(r"\s+", " ", text[start:end]).strip()


def _heuristic_extract(chunk_text: str) -> dict[str, Any]:
    low = chunk_text.lower()
    out: dict[str, list[dict[str, Any]]] = {
        "cognitive_distortions": [],
        "coping_actions": [],
        "psych_processes": [],
        "triggers": [],
    }

    distortion_map = {
        "core belief": ("core_belief_globalizing", "Core belief globalizing", "Rigid global negative self-beliefs."),
        "intermediate belief": ("intermediate_belief_rigidity", "Intermediate belief rigidity", "Conditional assumptions that increase distress."),
        "all-or-nothing": ("all_or_nothing", "All-or-nothing thinking", "Binary evaluations with no gradient."),
        "mental filter": ("mental_filter", "Mental filter", "Selective attention to negative information."),
    }
    for needle, (slug, name, definition) in distortion_map.items():
        if needle in low:
            out["cognitive_distortions"].append(
                {
                    "slug": slug,
                    "name_en": name,
                    "definition_en": definition,
                    "evidence": _snippet(chunk_text, needle),
                    "confidence": 0.55,
                }
            )

    action_map = {
        "behavioral experiment": ("behavioral_experiment", "Behavioral Experiment", "cognitive", ["excessive_worry"], ["gad", "social_anxiety_disorder"]),
        "exposure and response prevention": ("erp", "Exposure and Response Prevention", "behavioral", ["excessive_worry", "hypervigilance"], ["ocd"]),
        "thought record": ("thought_recording", "Thought Record", "cognitive", ["low_mood", "guilt"], ["mdd", "gad"]),
        "activity scheduling": ("activity_scheduling", "Activity Scheduling", "behavioral", ["anhedonia", "social_withdrawal"], ["mdd", "pdd"]),
    }
    for needle, item in action_map.items():
        if needle in low:
            action_id, name, cat, targets, helps = item
            out["coping_actions"].append(
                {
                    "action_id": action_id,
                    "name_en": name,
                    "category_slug": cat,
                    "targets_symptoms": targets,
                    "helps_with_disorders": helps,
                    "evidence": _snippet(chunk_text, needle),
                    "confidence": 0.58,
                }
            )

    process_map = {
        "schema": ("schema_activation", "Schema Activation", "Activation of deep cognitive templates.", "cognition", ["low_mood", "excessive_worry"]),
        "safety behavior": ("safety_behaviour", "Safety Behaviour", "Short-term anxiety reduction that maintains fear.", "activity", ["hypervigilance", "excessive_worry"]),
    }
    for needle, (slug, name, definition, construct, basis) in process_map.items():
        if needle in low:
            out["psych_processes"].append(
                {
                    "slug": slug,
                    "name_en": name,
                    "definition_en": definition,
                    "underlies_construct": construct,
                    "psych_basis_for": basis,
                    "evidence": _snippet(chunk_text, needle),
                    "confidence": 0.57,
                }
            )

    trigger_map = {
        "social scrutiny": ("social_scrutiny", "Social scrutiny", ["hypervigilance", "excessive_worry"], ["mind_reading"]),
        "health uncertainty": ("health_uncertainty", "Health uncertainty", ["excessive_worry"], ["catastrophizing"]),
    }
    for needle, (slug, name, manifests, trig_distortions) in trigger_map.items():
        if needle in low:
            out["triggers"].append(
                {
                    "slug": slug,
                    "name_en": name,
                    "manifests_as": manifests,
                    "commonly_triggers_distortions": trig_distortions,
                    "evidence": _snippet(chunk_text, needle),
                    "confidence": 0.52,
                }
            )

    return out


def _dedupe(items: list[dict[str, Any]], key_field: str) -> list[dict[str, Any]]:
    best: dict[str, dict[str, Any]] = {}
    for item in items:
        key = str(item.get(key_field, "")).strip()
        if not key:
            continue
        old = best.get(key)
        if old is None or float(item.get("confidence", 0.0)) > float(old.get("confidence", 0.0)):
            best[key] = item
    return list(best.values())


def _extract_chunk(chunk: Chunk, provider: str, openai_model: str, anthropic_model: str) -> dict[str, Any]:
    if provider == "none":
        return _heuristic_extract(chunk.text)
    if provider == "openai":
        return _openai_extract(chunk.text, openai_model)
    if provider == "anthropic":
        return _anthropic_extract(chunk.text, anthropic_model)

    # auto mode
    if os.getenv("OPENAI_API_KEY"):
        try:
            return _openai_extract(chunk.text, openai_model)
        except Exception:
            pass
    if os.getenv("ANTHROPIC_API_KEY"):
        return _anthropic_extract(chunk.text, anthropic_model)
    return _heuristic_extract(chunk.text)


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract CBT graph candidates from PDF")
    parser.add_argument("--input", required=True, type=Path, help="Input PDF path")
    parser.add_argument("--output", required=True, type=Path, help="Output JSON path")
    parser.add_argument("--chunk-pages", type=int, default=50, help="Pages per extraction chunk")
    parser.add_argument("--provider", choices=["auto", "openai", "anthropic", "none"], default="auto")
    parser.add_argument("--openai-model", default="gpt-4.1-mini")
    parser.add_argument("--anthropic-model", default="claude-3-5-sonnet-latest")
    args = parser.parse_args()

    chunks = _read_pdf_chunks(args.input, args.chunk_pages)

    aggregate: dict[str, list[dict[str, Any]]] = {
        "cognitive_distortions": [],
        "coping_actions": [],
        "psych_processes": [],
        "triggers": [],
    }
    chunk_reports: list[dict[str, Any]] = []

    for chunk in chunks:
        result = _extract_chunk(chunk, args.provider, args.openai_model, args.anthropic_model)
        for key in aggregate:
            aggregate[key].extend(result.get(key, []))
        chunk_reports.append(
            {
                "pages": [chunk.start_page, chunk.end_page],
                "counts": {k: len(result.get(k, [])) for k in aggregate},
            }
        )

    aggregate["cognitive_distortions"] = _dedupe(aggregate["cognitive_distortions"], "slug")
    aggregate["coping_actions"] = _dedupe(aggregate["coping_actions"], "action_id")
    aggregate["psych_processes"] = _dedupe(aggregate["psych_processes"], "slug")
    aggregate["triggers"] = _dedupe(aggregate["triggers"], "slug")

    payload = {
        "source_pdf": str(args.input),
        "generated_at": datetime.now(UTC).isoformat(),
        "provider": args.provider,
        "chunk_pages": args.chunk_pages,
        "chunks": chunk_reports,
        "results": aggregate,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote extraction to: {args.output}")


if __name__ == "__main__":
    main()
