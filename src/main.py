#!/usr/bin/env python3
"""CLI: Sal a la calle CDMX — turn neighborhood + time + mood into a printable outdoor plan."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow running as `python -m src.main` or `python src/main.py`
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.neighborhoods import resolve, list_names, NEIGHBORHOODS  # noqa: E402
from src.weather import fetch_weather  # noqa: E402
from src.osm import find_outdoor_spots  # noqa: E402
from src.gemma import generate_plan_text, ensure_ollama, DEFAULT_MODEL  # noqa: E402
from src.render import save_outputs, render_text, now_cdmx_str  # noqa: E402


def build_plan(
    neighborhood: str,
    minutes: int,
    mood: str,
    language: str,
    radius_m: int,
    model: str,
) -> dict:
    nb = resolve(neighborhood)
    weather = fetch_weather(nb["lat"], nb["lon"])
    spots = find_outdoor_spots(nb["lat"], nb["lon"], radius_m=radius_m)
    if not ensure_ollama():
        raise SystemExit(
            "Ollama is not reachable at OLLAMA_HOST. Start with `ollama serve` "
            f"and pull/create model `{model}`."
        )
    gen = generate_plan_text(
        neighborhood=nb["name"],
        minutes=minutes,
        mood=mood,
        language=language,
        weather=weather,
        spots=spots,
        model=model,
    )
    return {
        "neighborhood": nb,
        "minutes": minutes,
        "mood": mood,
        "language": language,
        "weather": weather,
        "spots": spots,
        "plan_text": gen["text"],
        "meta": {
            "model": gen["model"],
            "elapsed_s": gen["elapsed_s"],
            "eval_count": gen["eval_count"],
            "tokens_per_s": gen["tokens_per_s"],
        },
        "generated_at": now_cdmx_str(),
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Sal a la calle CDMX — printable outdoor plans powered by local Gemma + open data",
    )
    p.add_argument("--neighborhood", "-n", default="condesa", help="Neighborhood key or name")
    p.add_argument("--minutes", "-m", type=int, default=60, help="Free time in minutes")
    p.add_argument("--mood", default="calm walk", help="Mood / vibe (e.g. birding, tianguis, bike)")
    p.add_argument("--lang", default="es", choices=["es", "en"], help="Plan language")
    p.add_argument("--radius", type=int, default=1800, help="OSM search radius in meters")
    p.add_argument("--model", default=DEFAULT_MODEL, help="Ollama model name")
    p.add_argument("--out", default=None, help="Output directory (default: samples/)")
    p.add_argument("--stem", default=None, help="Output filename stem")
    p.add_argument("--list", action="store_true", help="List built-in neighborhoods and exit")
    p.add_argument("--json-stdout", action="store_true", help="Also print JSON to stdout")
    args = p.parse_args(argv)

    if args.list:
        for k, v in NEIGHBORHOODS.items():
            print(f"  {k:12} → {v['name']} ({v['alcaldia']})")
        return 0

    plan = build_plan(
        neighborhood=args.neighborhood,
        minutes=args.minutes,
        mood=args.mood,
        language=args.lang,
        radius_m=args.radius,
        model=args.model,
    )
    out_dir = Path(args.out) if args.out else ROOT / "samples"
    stem = args.stem or f"{resolve(args.neighborhood)['name'].lower().replace(' ', '_')}_{args.minutes}m"
    stem = "".join(c if c.isalnum() or c in "-_" else "_" for c in stem)
    paths = save_outputs(plan, out_dir, stem)
    print(render_text(plan))
    print(f"Saved: {paths['txt']}")
    print(f"Saved: {paths['html']}")
    print(f"Saved: {paths['json']}")
    if args.json_stdout:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
