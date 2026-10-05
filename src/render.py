"""Render printable HTML / text / PNG plan cards with QR + route sketch."""

from __future__ import annotations

import base64
import html
import io
import json
import textwrap
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

CDMX = ZoneInfo("America/Mexico_City")


def now_cdmx_str() -> str:
    return datetime.now(CDMX).strftime("%Y-%m-%d %H:%M %Z")


def _qr_data_uri(url: str, box_size: int = 4) -> str:
    try:
        import qrcode

        qr = qrcode.QRCode(version=None, box_size=box_size, border=1)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#1f5c2e", back_color="#fffef8")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        return f"data:image/png;base64,{b64}"
    except Exception:  # noqa: BLE001
        return ""


def render_text(plan: dict[str, Any]) -> str:
    nb = plan["neighborhood"]
    weather = plan["weather"]
    meta = plan["meta"]
    structured = plan.get("structured") or {}
    lines = [
        "=" * 52,
        "SAL A LA CALLE CDMX — outdoor plan card",
        "=" * 52,
        f"Title        : {structured.get('title', '')}",
        f"Neighborhood : {nb['name']} ({nb.get('alcaldia','')})",
        f"When         : {plan['generated_at']}",
        f"Free time    : {plan['minutes']} min | Mood: {plan['mood']}",
        f"Weather      : {weather.get('label')} · {weather.get('temp_c')}°C · {weather.get('advice')}",
        f"Model        : {meta.get('model')} · {meta.get('elapsed_s')}s · {meta.get('tokens_per_s')} tok/s",
        "-" * 52,
        "STEPS:",
    ]
    for i, st in enumerate(structured.get("steps") or [], 1):
        lines.append(f"  {i}. {st.get('place')} — {st.get('minutes')} min")
        lines.append(f"     {st.get('why')}")
    lines += [
        f"Rain backup  : {structured.get('rain_backup')}",
        f"Bring        : {', '.join(structured.get('what_to_bring') or [])}",
        f"Phone tip    : {structured.get('leave_the_phone_tip')}",
        f"Phone-down   : {structured.get('phone_down_minutes')} min",
        "Field challenge:",
    ]
    for c in structured.get("field_challenge") or []:
        lines.append(f"  [ ] {c}")
    lines += ["-" * 52, "Nearby OSM / seed picks:"]
    for s in plan.get("spots", [])[:6]:
        lines.append(
            f"  • {s['name']} [{s['kind']}] ~{s['distance_km']} km (~{s.get('walk_min','?')} min walk)"
        )
    if plan.get("map_url"):
        lines.append(f"Map QR target: {plan['map_url']}")
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
    structured = plan.get("structured") or {}
    lang = plan.get("language") or "es"
    spots_html = "".join(
        f"<li><strong>{html.escape(s['name'])}</strong> "
        f"<span class='kind'>{html.escape(s['kind'])}</span> "
        f"<span class='dist'>~{s['distance_km']} km · ~{s.get('walk_min','?')} min</span></li>"
        for s in plan.get("spots", [])[:6]
    )
    steps_html = "".join(
        f"<li><div class='step-head'><span class='n'>{i}</span> "
        f"<strong>{html.escape(str(st.get('place')))}</strong> "
        f"<span class='mins'>{st.get('minutes')} min</span></div>"
        f"<div class='why'>{html.escape(str(st.get('why') or ''))}</div></li>"
        for i, st in enumerate(structured.get("steps") or [], 1)
    )
    bring_html = "".join(
        f"<li>{html.escape(str(x))}</li>" for x in (structured.get("what_to_bring") or [])
    )
    challenge_html = "".join(
        f"<li><label><input type='checkbox'/> {html.escape(str(x))}</label></li>"
        for x in (structured.get("field_challenge") or [])
    )
    map_url = plan.get("map_url") or ""
    qr = _qr_data_uri(map_url) if map_url else ""
    qr_img = (
        f'<img class="qr" src="{qr}" alt="QR map"/>'
        if qr
        else f'<a class="maplink" href="{html.escape(map_url)}">Open map</a>'
        if map_url
        else ""
    )
    svg = plan.get("route_svg") or ""
    title = html.escape(str(structured.get("title") or f"{nb['name']} · {plan['minutes']} min"))
    labels = {
        "es": {
            "mood": "Mood",
            "when": "Cuándo",
            "weather": "Clima",
            "model": "Modelo",
            "steps": "Ruta",
            "rain": "Si llueve",
            "bring": "Lleva",
            "phone": "Tip anti-celular",
            "timer": "Temporizador phone-down",
            "field": "Reto de campo (offline)",
            "nearby": "Lugares cercanos (OSM/seed)",
            "cta": "Imprime · bolsillo · celular lejos · toca el pasto 🌿",
            "scan": "Escanea para el mapa a pie",
            "min": "min",
        },
        "en": {
            "mood": "Mood",
            "when": "When",
            "weather": "Weather",
            "model": "Model",
            "steps": "Route",
            "rain": "If it rains",
            "bring": "Bring",
            "phone": "Phone-away tip",
            "timer": "Phone-down timer",
            "field": "Field challenge (offline)",
            "nearby": "Nearby places (OSM/seed)",
            "cta": "Print · pocket · phone away · touch grass 🌿",
            "scan": "Scan for walking map",
            "min": "min",
        },
    }
    L = labels["en"] if lang.lower().startswith("en") else labels["es"]
    return textwrap.dedent(
        f"""\
        <!DOCTYPE html>
        <html lang="{html.escape(lang)}">
        <head>
          <meta charset="utf-8"/>
          <meta name="viewport" content="width=device-width, initial-scale=1"/>
          <title>Sal a la calle — {html.escape(nb['name'])}</title>
          <style>
            @page {{ size: A5; margin: 10mm; }}
            * {{ box-sizing: border-box; }}
            body {{
              font-family: "Segoe UI", system-ui, sans-serif;
              color: #1a2e1a;
              background: #e8f0e4;
              margin: 0;
              padding: 18px;
            }}
            .card {{
              max-width: 720px;
              margin: 0 auto;
              background: linear-gradient(165deg, #fffef8 0%, #f3f9ef 100%);
              border: 3px solid #2f6b3a;
              border-radius: 18px;
              padding: 26px 28px 22px;
              box-shadow: 0 10px 28px rgba(47,107,58,.18);
            }}
            .tag {{
              display: inline-block;
              background: #d8f0c8;
              color: #1f5c2e;
              font-size: .72rem;
              font-weight: 800;
              padding: 3px 10px;
              border-radius: 999px;
              text-transform: uppercase;
              letter-spacing: .07em;
            }}
            h1 {{
              margin: 8px 0 2px;
              font-size: 1.55rem;
              color: #1f5c2e;
              line-height: 1.25;
            }}
            .sub {{ color: #4a6a4a; font-size: .95rem; margin-bottom: 10px; }}
            .meta {{
              display: grid;
              grid-template-columns: 1fr 1fr;
              gap: 4px 14px;
              font-size: .88rem;
              color: #334433;
              margin-bottom: 14px;
            }}
            .grid {{
              display: grid;
              grid-template-columns: 1.4fr 0.9fr;
              gap: 16px;
              align-items: start;
            }}
            @media (max-width: 640px) {{
              .grid, .meta {{ grid-template-columns: 1fr; }}
            }}
            h2 {{
              font-size: .95rem;
              margin: 0 0 8px;
              color: #2f6b3a;
              text-transform: uppercase;
              letter-spacing: .04em;
            }}
            ol.steps {{ list-style: none; padding: 0; margin: 0 0 12px; }}
            ol.steps li {{
              background: #fff;
              border: 1px solid #cfe3c8;
              border-radius: 12px;
              padding: 10px 12px;
              margin-bottom: 8px;
            }}
            .step-head {{ display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }}
            .step-head .n {{
              background: #2f6b3a; color: #fff; width: 22px; height: 22px;
              border-radius: 50%; display: inline-flex; align-items: center;
              justify-content: center; font-size: .75rem; font-weight: 700;
            }}
            .mins {{
              margin-left: auto; background: #fff3d6; color: #7a4e00;
              font-size: .75rem; font-weight: 700; padding: 2px 8px; border-radius: 999px;
            }}
            .why {{ font-size: .88rem; color: #445544; margin-top: 4px; }}
            .rain, .tip, .timer {{
              font-size: .9rem; background: #eef6ea; border-left: 4px solid #2f6b3a;
              padding: 8px 10px; border-radius: 0 8px 8px 0; margin: 8px 0;
            }}
            ul.bring, ul.challenge, ul.spots {{ padding-left: 1.1rem; margin: 4px 0 10px; }}
            ul.challenge {{ list-style: none; padding-left: 0; }}
            ul.challenge li {{ margin: 6px 0; font-size: .92rem; }}
            ul.spots .kind {{ color: #5a7a5a; font-size: .82rem; }}
            ul.spots .dist {{ color: #888; font-size: .78rem; }}
            .side {{ text-align: center; }}
            .qr {{ width: 120px; height: 120px; image-rendering: pixelated; }}
            .mapcap {{ font-size: .72rem; color: #667766; margin: 4px 0 10px; }}
            .route {{ margin: 0 auto 8px; display: block; }}
            .cta {{
              margin-top: 12px; font-weight: 800; color: #1f5c2e; font-size: 1.05rem;
              text-align: center;
            }}
            footer {{
              margin-top: 10px; font-size: .72rem; color: #667766; text-align: center;
            }}
            .print-bar {{
              max-width: 720px; margin: 0 auto 12px; display: flex; gap: 8px; justify-content: flex-end;
            }}
            .print-bar button {{
              background: #2f6b3a; color: #fff; border: 0; border-radius: 8px;
              padding: 8px 14px; font-weight: 700; cursor: pointer;
            }}
            @media print {{
              body {{ background: #fff; padding: 0; }}
              .print-bar {{ display: none; }}
              .card {{ box-shadow: none; }}
            }}
          </style>
        </head>
        <body>
          <div class="print-bar">
            <button onclick="window.print()">Print / PDF</button>
          </div>
          <article class="card">
            <span class="tag">Sal a la calle CDMX</span>
            <h1>{title}</h1>
            <div class="sub">{html.escape(nb['name'])} · {plan['minutes']} {L['min']} · {html.escape(plan['mood'])}</div>
            <div class="meta">
              <div><strong>{L['when']}:</strong> {html.escape(plan['generated_at'])}</div>
              <div><strong>{L['weather']}:</strong> {html.escape(str(weather.get('label')))} · {weather.get('temp_c')}°C</div>
              <div><strong>{L['model']}:</strong> {html.escape(str(meta.get('model')))} · {meta.get('elapsed_s')}s</div>
              <div><strong>{L['timer']}:</strong> {structured.get('phone_down_minutes')} {L['min']}</div>
            </div>
            <div class="grid">
              <div>
                <h2>{L['steps']}</h2>
                <ol class="steps">{steps_html}</ol>
                <div class="rain"><strong>{L['rain']}:</strong> {html.escape(str(structured.get('rain_backup') or ''))}</div>
                <h2>{L['bring']}</h2>
                <ul class="bring">{bring_html}</ul>
                <div class="tip"><strong>{L['phone']}:</strong> {html.escape(str(structured.get('leave_the_phone_tip') or ''))}</div>
                <h2>{L['field']}</h2>
                <ul class="challenge">{challenge_html}</ul>
              </div>
              <div class="side">
                {svg.replace('<svg', '<svg class="route"', 1) if svg else ''}
                {qr_img}
                <div class="mapcap">{L['scan']}</div>
                <h2>{L['nearby']}</h2>
                <ul class="spots" style="text-align:left">{spots_html}</ul>
              </div>
            </div>
            <p class="cta">{L['cta']}</p>
            <footer>
              OpenStreetMap + Open-Meteo · Gemma local via Ollama · MIT · 2026
              {" · offline seed" if plan.get("offline") else ""}
            </footer>
          </article>
        </body>
        </html>
        """
    )


def html_to_png(html_path: Path, png_path: Path, width: int = 900) -> Path | None:
    """Render HTML card to PNG via headless Chrome."""
    import subprocess

    html_path = html_path.resolve()
    png_path = png_path.resolve()
    cmd = [
        "google-chrome",
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--hide-scrollbars",
        f"--screenshot={png_path}",
        f"--window-size={width},1200",
        f"file://{html_path}",
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=60)
        if png_path.exists() and png_path.stat().st_size > 1000:
            return png_path
    except Exception as e:  # noqa: BLE001
        print(f"[render] chrome screenshot failed: {e}", flush=True)
    return None


def save_outputs(plan: dict[str, Any], out_dir: Path, stem: str, also_png: bool = True) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    txt = out_dir / f"{stem}.txt"
    htm = out_dir / f"{stem}.html"
    txt.write_text(render_text(plan), encoding="utf-8")
    htm.write_text(render_html(plan), encoding="utf-8")
    paths["txt"] = txt
    paths["html"] = htm
    js = out_dir / f"{stem}.json"
    # Strip bulky SVG from JSON? keep it — useful. But keep under control.
    js.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    paths["json"] = js
    if also_png:
        png = out_dir / f"{stem}.png"
        if html_to_png(htm, png):
            paths["png"] = png
    return paths
