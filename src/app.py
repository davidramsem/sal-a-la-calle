"""Gradio UI for Sal a la calle CDMX — neighborhood · minutes · mood → printable card."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import gradio as gr

from src.neighborhoods import NEIGHBORHOODS
from src.gemma import DEFAULT_MODEL, list_models
from src.main import build_plan
from src.render import save_outputs, render_html

NB_CHOICES = [(f"{v['name']} ({k})", k) for k, v in NEIGHBORHOODS.items()]
MOOD_PRESETS_ES = [
    "paseo tranquilo",
    "birdwatching / aves",
    "tianguis / mercado",
    "bici fácil",
    "correr suave",
]
MOOD_PRESETS_EN = [
    "calm walk",
    "birdwatching",
    "street market",
    "easy bike",
    "easy jog",
]


def _models() -> list[str]:
    found = list_models()
    preferred = []
    for name in ("gemma3-4b-cdmx:latest", "gemma3-4b-cdmx", "gemma3-1b-cdmx:latest", "gemma3-1b-cdmx"):
        if name in found or name.replace(":latest", "") in [f.replace(":latest", "") for f in found]:
            preferred.append(name.replace(":latest", ""))
    # unique preserve order
    out = []
    for m in preferred + [f.replace(":latest", "") for f in found]:
        if m not in out:
            out.append(m)
    return out or [DEFAULT_MODEL]


def generate(neighborhood, minutes, mood, lang, model, offline):
    plan = build_plan(
        neighborhood=neighborhood,
        minutes=int(minutes),
        mood=mood or ("paseo tranquilo" if lang == "es" else "calm walk"),
        language=lang,
        radius_m=1800,
        model=model or DEFAULT_MODEL,
        offline=bool(offline),
    )
    out_dir = Path(tempfile.mkdtemp(prefix="sala_"))
    stem = "plan"
    paths = save_outputs(plan, out_dir, stem, also_png=True)
    html = render_html(plan)
    png = str(paths["png"]) if "png" in paths else None
    meta = (
        f"**{plan['structured'].get('title')}**  \n"
        f"Model `{plan['meta']['model']}` · {plan['meta']['elapsed_s']}s · "
        f"{plan['meta'].get('tokens_per_s')} tok/s  \n"
        f"Phone-down timer: **{plan['structured'].get('phone_down_minutes')} min**"
    )
    return html, png, meta, str(paths.get("html", ""))


def build_ui() -> gr.Blocks:
    models = _models()
    with gr.Blocks(title="Sal a la calle CDMX") as demo:
        gr.Markdown(
            """
# 🌿 Sal a la calle CDMX
Neighborhood + minutes + mood → a **printable outdoor plan card** powered by local **Gemma** (Ollama).
Print it, put the phone away, touch grass.
"""
        )
        with gr.Row():
            with gr.Column(scale=1):
                nb = gr.Dropdown(NB_CHOICES, value="condesa", label="Neighborhood / Barrio")
                minutes = gr.Slider(20, 180, value=60, step=5, label="Minutes free")
                lang = gr.Radio(["es", "en"], value="es", label="Language")
                mood = gr.Textbox(value="paseo tranquilo", label="Mood / vibe")
                model = gr.Dropdown(models, value=models[0], label="Gemma model (Ollama)")
                offline = gr.Checkbox(value=False, label="Offline mode (seed places + cached weather)")
                go = gr.Button("Generate plan 🌿", variant="primary")
                meta = gr.Markdown()
                gr.Markdown("Presets: " + " · ".join(f"`{m}`" for m in MOOD_PRESETS_ES[:3]))
            with gr.Column(scale=2):
                card_html = gr.HTML(label="Plan card")
                card_png = gr.Image(label="Card preview (PNG)", type="filepath")
                path_out = gr.Textbox(label="Saved HTML path", interactive=False)
        go.click(
            generate,
            inputs=[nb, minutes, mood, lang, model, offline],
            outputs=[card_html, card_png, meta, path_out],
        )
        gr.Markdown(
            "*Local inference · OpenStreetMap + Open-Meteo · MIT — Hacktoberfest Touch Grass 2026*"
        )
    return demo


if __name__ == "__main__":
    port = int(os.environ.get("SALA_PORT", "7860"))
    build_ui().launch(server_name="0.0.0.0", server_port=port, share=False, theme=gr.themes.Soft())
