#!/usr/bin/env python3
"""CLI: Sal a la calle CDMX — neighborhood + time + mood → printable outdoor plan."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.neighborhoods import resolve, NEIGHBORHOODS  # noqa: E402
from src.weather import fetch_weather  # noqa: E402
from src.osm import find_outdoor_spots  # noqa: E402
from src.gemma import generate_plan_json, ensure_ollama, DEFAULT_MODEL  # noqa: E402
from src.plan import (  # noqa: E402
    enrich_spots,
    validate_and_repair,
    osm_route_url,
    tiny_route_svg,
)
from src.render import save_outputs, render_text, now_cdmx_str  # noqa: E402


def build_plan(
    neighborhood: str,
    minutes: int,
    mood: str,
    language: str,
    radius_m: int,
    model: str,
    offline: bool = False,
) -> dict:
    nb = resolve(neighborhood)
    weather = fetch_weather(nb["lat"], nb["lon"], offline=offline)
    if offline or os.environ.get("SALA_OFFLINE") == "1":
        spots = find_outdoor_spots(nb["lat"], nb["lon"], radius_m=radius_m, force_seed=True)
    else:
        spots = find_outdoor_spots(nb["lat"], nb["lon"], radius_m=radius_m)
    spots = enrich_spots(spots)
    if not ensure_ollama():
        raise SystemExit(
            "Ollama is not reachable at OLLAMA_HOST. Start with `ollama serve` "
            f"and create/pull model `{model}`."
        )
    gen = generate_plan_json(
        neighborhood=nb["name"],
        minutes=minutes,
        mood=mood,
        language=language,
        weather=weather,
        spots=spots,
        model=model,
    )
    structured = validate_and_repair(
        gen.get("parsed"),
        neighborhood=nb["name"],
        minutes=minutes,
        mood=mood,
        language=language,
        weather=weather,
        spots=spots,
    )
    # Resolve step places to full spot dicts for map
    by_name = {s["name"]: s for s in spots}
    route_places = [by_name[s["place"]] for s in structured["steps"] if s["place"] in by_name]
    map_url = osm_route_url(nb, route_places)
    route_svg = tiny_route_svg(nb, route_places)
    return {
        "neighborhood": nb,
        "minutes": minutes,
        "mood": mood,
        "language": language,
        "weather": weather,
        "spots": spots,
        "structured": structured,
        "plan_text": render_text_from_structured(structured, language),
        "map_url": map_url,
        "route_svg": route_svg,
        "offline": bool(offline or weather.get("offline")),
        "meta": {
            "model": gen["model"],
            "elapsed_s": gen["elapsed_s"],
            "eval_count": gen["eval_count"],
            "tokens_per_s": gen["tokens_per_s"],
            "prompt_eval_s": gen.get("prompt_eval_s"),
            "eval_s": gen.get("eval_s"),
            "raw_json": gen.get("parsed"),
            "repair_notes": structured.get("_repair_notes"),
        },
        "generated_at": now_cdmx_str(),
    }


def render_text_from_structured(structured: dict, language: str) -> str:
    """Compact plan_text for JSON consumers / comparisons."""
    lines = [structured.get("title", ""), ""]
    for i, st in enumerate(structured.get("steps") or [], 1):
        lines.append(f"{i}. {st.get('place')} ({st.get('minutes')} min) — {st.get('why')}")
    lines += [
        "",
        f"Rain: {structured.get('rain_backup')}",
        f"Bring: {', '.join(structured.get('what_to_bring') or [])}",
        f"Phone tip: {structured.get('leave_the_phone_tip')}",
        f"Phone-down: {structured.get('phone_down_minutes')} min",
        "Field challenge:",
    ]
    for c in structured.get("field_challenge") or []:
        lines.append(f"  [ ] {c}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Sal a la calle CDMX — printable outdoor plans powered by local Gemma + open data",
    )
    p.add_argument("--neighborhood", "-n", default="condesa", help="Neighborhood key or name")
    p.add_argument("--minutes", "-m", type=int, default=60, help="Free time in minutes")
    p.add_argument("--mood", default="paseo tranquilo", help="Mood / vibe")
    p.add_argument("--lang", default="es", choices=["es", "en"], help="Plan language")
    p.add_argument("--radius", type=int, default=1800, help="OSM search radius in meters")
    p.add_argument("--model", default=DEFAULT_MODEL, help="Ollama model name")
    p.add_argument("--out", default=None, help="Output directory (default: samples/)")
    p.add_argument("--stem", default=None, help="Output filename stem")
    p.add_argument("--list", action="store_true", help="List built-in neighborhoods and exit")
    p.add_argument("--json-stdout", action="store_true", help="Also print JSON to stdout")
    p.add_argument("--offline", action="store_true", help="Use seed places + cached weather only")
    p.add_argument("--no-png", action="store_true", help="Skip HTML→PNG screenshot")
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
        offline=args.offline,
    )
    out_dir = Path(args.out) if args.out else ROOT / "samples"
    stem = args.stem or f"{resolve(args.neighborhood)['name'].lower().replace(' ', '_')}_{args.minutes}m"
    stem = "".join(c if c.isalnum() or c in "-_" else "_" for c in stem)
    paths = save_outputs(plan, out_dir, stem, also_png=not args.no_png)
    print(render_text(plan))
    for k, v in paths.items():
        print(f"Saved ({k}): {v}")
    if args.json_stdout:
        # omit huge svg optionally
        dump = dict(plan)
        print(json.dumps(dump, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
