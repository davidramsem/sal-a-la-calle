"""Local Gemma via Ollama HTTP API — structured JSON outdoor plans."""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from typing import Any

DEFAULT_MODEL = os.environ.get("SALA_MODEL", "gemma3-4b-cdmx")
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")

PLAN_SCHEMA_HINT = {
    "title": "short catchy title",
    "steps": [
        {"place": "EXACT name from spot list", "minutes": 20, "why": "one short reason"}
    ],
    "rain_backup": "one short indoor-edge / sheltered option using a listed place",
    "what_to_bring": ["item1", "item2", "item3"],
    "leave_the_phone_tip": "one concrete tip",
    "field_challenge": ["checkbox task 1", "checkbox task 2", "checkbox task 3"],
    "phone_down_minutes": 40,
}


def ensure_ollama(timeout: float = 2.0) -> bool:
    try:
        with urllib.request.urlopen(f"{OLLAMA_HOST}/api/tags", timeout=timeout) as r:
            r.read()
        return True
    except Exception:  # noqa: BLE001
        return False


def list_models() -> list[str]:
    try:
        with urllib.request.urlopen(f"{OLLAMA_HOST}/api/tags", timeout=5) as r:
            data = json.loads(r.read().decode())
        return [m.get("name", "") for m in data.get("models", [])]
    except Exception:  # noqa: BLE001
        return []


def _spot_block(spots: list[dict[str, Any]]) -> str:
    lines = []
    for s in spots[:8]:
        walk = s.get("walk_min")
        walk_bit = f", ~{walk} min walk" if walk is not None else ""
        lines.append(
            f"- {s['name']} | kind={s['kind']} | {s['distance_km']} km{walk_bit}"
        )
    return "\n".join(lines) or "- (no spots — refuse to invent distant places)"


def build_prompt(
    *,
    neighborhood: str,
    minutes: int,
    mood: str,
    language: str,
    weather: dict[str, Any],
    spots: list[dict[str, Any]],
) -> str:
    lang_line = "Spanish (Mexico)" if language.lower().startswith("es") else "English"
    allowed = [s["name"] for s in spots[:8]]
    return f"""You write ONE outdoor micro-plan for Mexico City as STRICT JSON (no markdown, no prose outside JSON).

Neighborhood: {neighborhood}
Free time budget: {minutes} minutes TOTAL
Mood: {mood}
Language for ALL string values: {lang_line}
CRITICAL: every human-readable string (title, why, rain_backup, what_to_bring, leave_the_phone_tip, field_challenge) MUST be written in {lang_line}. Do not mix languages.
Weather: {weather.get('label')}, {weather.get('temp_c')}°C, humidity {weather.get('humidity')}%. Advice: {weather.get('advice')}

ALLOWED PLACES (you MUST use only these exact names in steps[].place and rain_backup):
{_spot_block(spots)}
Allowed names list: {json.dumps(allowed, ensure_ascii=False)}

JSON schema (fill every key):
{json.dumps(PLAN_SCHEMA_HINT, ensure_ascii=False, indent=2)}

HARD RULES:
1. Output a single JSON object. No ``` fences. No commentary before/after.
2. steps: 2 to 4 items. Sum of steps[].minutes should be between {int(minutes*0.7)} and {minutes} (use most of the budget at the places, not commuting). Do NOT invent bus/metro for places under 1.5 km.
3. steps[].place MUST be copied EXACTLY from the allowed names list (character-for-character).
4. Prefer the closest places that match the mood. Never suggest taking a bus/metro for places under 1.5 km — say walk or bike.
5. Do NOT invent street names, bus lines, cafés, or places not in the list.
6. field_challenge: 3 offline checkboxes (birds/trees/sit without phone). phone_down_minutes roughly 70% of budget.
7. what_to_bring: 3 short items matching weather + mood.
8. title: <= 8 words, no typos.
"""


def _extract_json(text: str) -> dict[str, Any] | None:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass
    # Find outermost { ... }
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            obj = json.loads(text[start : end + 1])
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            return None
    return None


def generate_raw(
    prompt: str,
    *,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.4,
    num_predict: int = 700,
    num_ctx: int = 4096,
) -> dict[str, Any]:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": temperature,
            "top_p": 0.9,
            "num_ctx": num_ctx,
            "num_predict": num_predict,
        },
    }
    t0 = time.time()
    req = urllib.request.Request(
        f"{OLLAMA_HOST}/api/generate",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.URLError as e:
        raise RuntimeError(
            f"Cannot reach Ollama ({model}). Start `ollama serve`. Error: {e}"
        ) from e
    elapsed = time.time() - t0
    text = (data.get("response") or "").strip()
    eval_count = data.get("eval_count") or 0
    eval_ns = data.get("eval_duration") or 0
    prompt_ns = data.get("prompt_eval_duration") or 0
    toks_per_s = (eval_count / (eval_ns / 1e9)) if eval_ns else None
    return {
        "text": text,
        "parsed": _extract_json(text),
        "model": model,
        "elapsed_s": round(elapsed, 2),
        "eval_count": eval_count,
        "tokens_per_s": round(toks_per_s, 2) if toks_per_s else None,
        "prompt_eval_s": round(prompt_ns / 1e9, 2) if prompt_ns else None,
        "eval_s": round(eval_ns / 1e9, 2) if eval_ns else None,
    }


def generate_plan_json(
    *,
    neighborhood: str,
    minutes: int,
    mood: str,
    language: str,
    weather: dict[str, Any],
    spots: list[dict[str, Any]],
    model: str = DEFAULT_MODEL,
) -> dict[str, Any]:
    """Ask Gemma for structured JSON. Returns raw + timing; caller validates."""
    prompt = build_prompt(
        neighborhood=neighborhood,
        minutes=minutes,
        mood=mood,
        language=language,
        weather=weather,
        spots=spots,
    )
    # Smaller models benefit from lower context.
    num_ctx = 2048 if "1b" in model.lower() else 4096
    num_predict = 500 if "1b" in model.lower() else 700
    temperature = 0.55 if "1b" in model.lower() else 0.35
    result = generate_raw(
        prompt,
        model=model,
        temperature=temperature,
        num_predict=num_predict,
        num_ctx=num_ctx,
    )
    result["prompt_preview"] = prompt[:500]
    return result


# Back-compat alias used by older callers
def generate_plan_text(**kwargs: Any) -> dict[str, Any]:
    r = generate_plan_json(**kwargs)
    return {
        "text": r.get("text") or "",
        "model": r["model"],
        "elapsed_s": r["elapsed_s"],
        "eval_count": r["eval_count"],
        "tokens_per_s": r["tokens_per_s"],
        "prompt_preview": r.get("prompt_preview", ""),
        "parsed": r.get("parsed"),
        "raw": r,
    }
