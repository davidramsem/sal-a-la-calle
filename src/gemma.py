"""Local Gemma via Ollama HTTP API."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any

DEFAULT_MODEL = os.environ.get("SALA_MODEL", "gemma3-1b-cdmx")
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")


def ensure_ollama(timeout: float = 2.0) -> bool:
    try:
        with urllib.request.urlopen(f"{OLLAMA_HOST}/api/tags", timeout=timeout) as r:
            r.read()
        return True
    except Exception:  # noqa: BLE001
        return False


def generate_plan_text(
    *,
    neighborhood: str,
    minutes: int,
    mood: str,
    language: str,
    weather: dict[str, Any],
    spots: list[dict[str, Any]],
    model: str = DEFAULT_MODEL,
) -> dict[str, Any]:
    """Ask Gemma to write a one-page outdoor plan. Returns text + timing meta."""
    lang_line = "Spanish (Mexico)" if language.lower().startswith("es") else "English"
    spot_lines = "\n".join(
        f"- {s['name']} ({s['kind']}, ~{s['distance_km']} km)" for s in spots[:8]
    ) or "- (no OSM spots found — invent a safe generic walk using public parks you know in CDMX)"
    prompt = f"""Create a ONE-PAGE printable outdoor plan for Mexico City.

Neighborhood: {neighborhood}
Free time: {minutes} minutes
Mood: {mood}
Language: write the whole plan in {lang_line}
Weather now: {weather.get('label')}, {weather.get('temp_c')}°C, humidity {weather.get('humidity')}%. Advice: {weather.get('advice')}

Nearby open-data spots (from OpenStreetMap):
{spot_lines}

RULES:
- Screen should be the shortest part: the plan must be printable / screenshot-ready.
- Pick 1 primary activity that fits the time + mood. Optionally add 1 backup if rain.
- Use real place names from the list when possible.
- Include: title, where to go, how to get there on foot/bike/transit tip, what to bring, a simple timeline, and one "leave the phone" tip.
- Keep it under 220 words. No markdown tables. Use short headings and bullets.
- Do NOT invent dangerous activities. Prefer parks, walks, birding, tianguis, bike paths.
"""
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.7,
            "top_p": 0.9,
            "num_ctx": 2048,
            "num_predict": 450,
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
        with urllib.request.urlopen(req, timeout=300) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.URLError as e:
        raise RuntimeError(
            "Cannot reach Ollama. Start it with `ollama serve` and ensure the model is loaded "
            f"(default: {model}). Original error: {e}"
        ) from e
    elapsed = time.time() - t0
    text = (data.get("response") or "").strip()
    eval_count = data.get("eval_count") or 0
    eval_ns = data.get("eval_duration") or 0
    toks_per_s = (eval_count / (eval_ns / 1e9)) if eval_ns else None
    return {
        "text": text,
        "model": model,
        "elapsed_s": round(elapsed, 2),
        "eval_count": eval_count,
        "tokens_per_s": round(toks_per_s, 2) if toks_per_s else None,
        "prompt_preview": prompt[:400],
    }
