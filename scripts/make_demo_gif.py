"""Build a short demo GIF from plan card PNGs + UI mock frames."""
from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "images" / "demo_flow.gif"
CARDS = [
    ROOT / "samples" / "condesa_60m_paseo.png",
    ROOT / "samples" / "coyoacan_90m_birding.png",
    ROOT / "samples" / "chapultepec_45m_bike.png",
]


def frame_label(img: Image.Image, text: str) -> Image.Image:
    canvas = Image.new("RGB", (900, 1100), "#e8f0e4")
    # fit card
    card = img.convert("RGB")
    card.thumbnail((860, 980), Image.Resampling.LANCZOS)
    x = (900 - card.width) // 2
    y = 70
    canvas.paste(card, (x, y))
    d = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
    except Exception:
        font = ImageFont.load_default()
    d.rectangle((0, 0, 900, 54), fill="#2f6b3a")
    d.text((20, 12), text, fill="#fffef8", font=font)
    return canvas


def ui_mock() -> Image.Image:
    img = Image.new("RGB", (900, 1100), "#f4f7f0")
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
        font_s = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
    except Exception:
        font = font_s = ImageFont.load_default()
    d.rectangle((0, 0, 900, 54), fill="#2f6b3a")
    d.text((20, 12), "1 · Pick barrio + minutes + mood", fill="#fffef8", font=font)
    d.rounded_rectangle((60, 120, 840, 980), radius=20, fill="#ffffff", outline="#2f6b3a", width=3)
    d.text((90, 160), "Sal a la calle CDMX", fill="#1f5c2e", font=font)
    rows = [
        ("Neighborhood", "Condesa"),
        ("Minutes", "60"),
        ("Mood", "paseo tranquilo"),
        ("Language", "es"),
        ("Model", "gemma3-4b-cdmx"),
    ]
    y = 240
    for k, v in rows:
        d.rounded_rectangle((90, y, 810, y + 70), radius=12, fill="#eef6ea", outline="#cfe3c8")
        d.text((110, y + 20), f"{k}:  {v}", fill="#334433", font=font_s)
        y += 90
    d.rounded_rectangle((90, y + 20, 810, y + 100), radius=14, fill="#2f6b3a")
    d.text((280, y + 42), "Generate plan 🌿", fill="#fffef8", font=font)
    return img


def main() -> None:
    frames = [ui_mock()]
    labels = [
        "2 · Local Gemma writes JSON plan",
        "3 · Printable card + field challenge",
        "4 · QR map · phone-down · touch grass",
    ]
    for path, label in zip(CARDS, labels):
        if path.exists():
            frames.append(frame_label(Image.open(path), label))
    if len(frames) < 2:
        raise SystemExit("Need at least one card PNG")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        OUT,
        save_all=True,
        append_images=frames[1:],
        duration=[1800] + [2200] * (len(frames) - 1),
        loop=0,
        optimize=True,
    )
    print("wrote", OUT, OUT.stat().st_size)


if __name__ == "__main__":
    main()
