"""Render printable HTML / text plan cards."""

from __future__ import annotations

import html
import textwrap
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

CDMX = ZoneInfo("America/Mexico_City")


def render_text(plan: dict[str, Any]) -> str:
    nb = plan["neighborhood"]
    weather = plan["weather"]
    meta = plan["meta"]
    lines = [
        "=" * 52,
        "SAL A LA CALLE CDMX — outdoor plan card",
        "=" * 52,
        f"Neighborhood : {nb['name']} ({nb.get('alcaldia','')})",
        f"When         : {plan['generated_at']}",
        f"Free time    : {plan['minutes']} min | Mood: {plan['mood']}",
        f"Weather      : {weather.get('label')} · {weather.get('temp_c')}°C · {weather.get('advice')}",
        f"Model        : {meta.get('model')} · {meta.get('elapsed_s')}s",
        "-" * 52,
        plan["plan_text"],
        "-" * 52,
        "Nearby OSM picks:",
    ]
    for s in plan.get("spots", [])[:6]:
        lines.append(f"  • {s['name']} [{s['kind']}] ~{s['distance_km']} km")
    lines += [
        "-" * 52,
        "Print this card. Put the phone away. Touch grass.",
        "Open data: OpenStreetMap + Open-Meteo · LLM: local Gemma via Ollama",
        "=" * 52,
    ]
    return "\n".join(lines) + "\n"


def render_html(plan: dict[str, Any]) -> str:
    nb = plan["neighborhood"]
    weather = plan["weather"]
    meta = plan["meta"]
    spots_html = "".join(
        f"<li><strong>{html.escape(s['name'])}</strong> "
        f"<span class='kind'>{html.escape(s['kind'])}</span> "
        f"<span class='dist'>~{s['distance_km']} km</span></li>"
        for s in plan.get("spots", [])[:6]
    )
    body = html.escape(plan["plan_text"]).replace("\n", "<br>\n")
    return textwrap.dedent(
        f"""\
        <!DOCTYPE html>
        <html lang="es">
        <head>
          <meta charset="utf-8"/>
          <title>Sal a la calle — {html.escape(nb['name'])}</title>
          <style>
            @page {{ size: A5; margin: 12mm; }}
            body {{
              font-family: "Segoe UI", system-ui, sans-serif;
              color: #1a2e1a;
              background: #f4f7f0;
              margin: 0;
              padding: 24px;
            }}
            .card {{
              max-width: 640px;
              margin: 0 auto;
              background: #fffef8;
              border: 3px solid #2f6b3a;
              border-radius: 16px;
              padding: 28px 32px;
              box-shadow: 0 8px 24px rgba(47,107,58,.15);
            }}
            h1 {{
              margin: 0 0 4px;
              font-size: 1.6rem;
              color: #1f5c2e;
              letter-spacing: .02em;
            }}
            .tag {{
              display: inline-block;
              background: #d8f0c8;
              color: #1f5c2e;
              font-size: .75rem;
              font-weight: 700;
              padding: 3px 10px;
              border-radius: 999px;
              text-transform: uppercase;
              letter-spacing: .06em;
            }}
            .meta {{
              margin: 14px 0 18px;
              font-size: .92rem;
              line-height: 1.45;
              color: #334433;
            }}
            .plan {{
              font-size: 1rem;
              line-height: 1.5;
              border-top: 2px dashed #a8c9a0;
              border-bottom: 2px dashed #a8c9a0;
              padding: 16px 0;
              margin: 12px 0;
            }}
            ul.spots {{ padding-left: 1.1rem; margin: 8px 0 0; }}
            ul.spots .kind {{ color: #5a7a5a; font-size: .85rem; }}
            ul.spots .dist {{ color: #888; font-size: .8rem; }}
            footer {{
              margin-top: 18px;
              font-size: .78rem;
              color: #667766;
            }}
            .cta {{
              margin-top: 14px;
              font-weight: 700;
              color: #1f5c2e;
              font-size: 1.05rem;
            }}
          </style>
        </head>
        <body>
          <article class="card">
            <span class="tag">Sal a la calle CDMX</span>
            <h1>{html.escape(nb['name'])} · {plan['minutes']} min</h1>
            <div class="meta">
              <div><strong>Mood:</strong> {html.escape(plan['mood'])}</div>
              <div><strong>When:</strong> {html.escape(plan['generated_at'])}</div>
              <div><strong>Weather:</strong> {html.escape(str(weather.get('label')))} ·
                {weather.get('temp_c')}°C — {html.escape(str(weather.get('advice','')))}</div>
              <div><strong>Model:</strong> {html.escape(str(meta.get('model')))}
                · {meta.get('elapsed_s')}s local</div>
            </div>
            <div class="plan">{body}</div>
            <div><strong>Nearby OSM picks</strong></div>
            <ul class="spots">{spots_html}</ul>
            <p class="cta">Print · pocket · phone away · touch grass 🌿</p>
            <footer>
              Open data: OpenStreetMap (Overpass) + Open-Meteo ·
              Open-weight LLM: Gemma via Ollama (local). MIT · 2026
            </footer>
          </article>
        </body>
        </html>
        """
    )


def save_outputs(plan: dict[str, Any], out_dir: Path, stem: str) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {}
    txt = out_dir / f"{stem}.txt"
    htm = out_dir / f"{stem}.html"
    txt.write_text(render_text(plan), encoding="utf-8")
    htm.write_text(render_html(plan), encoding="utf-8")
    paths["txt"] = txt
    paths["html"] = htm
    # Also dump raw JSON for reproducibility
    import json

    js = out_dir / f"{stem}.json"
    js.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    paths["json"] = js
    return paths


def now_cdmx_str() -> str:
    return datetime.now(CDMX).strftime("%Y-%m-%d %H:%M %Z")
