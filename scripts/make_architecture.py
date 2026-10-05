"""Draw a simple architecture diagram for the DEV post."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

W, H = 1200, 640
img = Image.new("RGB", (W, H), "#f4f7f0")
d = ImageDraw.Draw(img)
try:
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
    font_s = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
    font_xs = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
except Exception:
    font = font_s = font_xs = ImageFont.load_default()

def box(xy, title, lines, fill, outline="#2f6b3a"):
    x0,y0,x1,y1 = xy
    d.rounded_rectangle(xy, radius=16, fill=fill, outline=outline, width=3)
    d.text((x0+16, y0+12), title, fill="#1f5c2e", font=font_s)
    yy = y0 + 42
    for line in lines:
        d.text((x0+16, yy), line, fill="#334433", font=font_xs)
        yy += 22

d.text((40, 24), "Sal a la calle CDMX — architecture", fill="#1f5c2e", font=font)
d.text((40, 60), "Local Gemma plans a walk. Open data grounds it. The card ends the screen.", fill="#445544", font=font_s)

box((40, 110, 280, 280), "1. Inputs", ["Neighborhood", "Minutes free", "Mood + language", "CLI or Gradio UI"], "#e8f5e0")
box((320, 110, 580, 280), "2. Open data", ["Open-Meteo weather", "OSM Overpass spots", "CDMX seed fallback", "Offline cache mode"], "#e0eef8")
box((620, 110, 900, 280), "3. Local Gemma", ["Ollama on CPU", "Gemma 3 1B or 4B", "JSON schema output", "Validate + repair"], "#fff0d9")
box((940, 110, 1160, 280), "4. Artifact", ["Printable HTML", "PNG / PDF", "QR → OSM route", "Field challenge"], "#f0e6ff")

# arrows
for x in (280, 580, 900):
    d.polygon([(x+8, 185), (x+32, 195), (x+8, 205)], fill="#2f6b3a")

box((40, 320, 580, 520), "Why open weights", [
    "Prompt (location + mood) never leaves the laptop",
    "$0 inference after the GGUF is local",
    "Swap gemma3-1b-cdmx ↔ gemma3-4b-cdmx via SALA_MODEL",
    "Works offline with seed places + cached weather",
], "#ffffff")
box((620, 320, 1160, 520), "Touch-grass constraint", [
    "Screen is the shortest part of the loop",
    "One card → print → pocket → phone-down timer",
    "Offline field challenge (birds / trees / sit)",
    "No account · no streak · no push nag",
], "#ffffff")

d.text((40, 560), "MIT · Map data © OpenStreetMap · Weather © Open-Meteo · Model: Google Gemma (open weights) via Ollama", fill="#667766", font=font_xs)

out = Path("/workspace/hacktoberfest_w1/images/architecture.png")
img.save(out, "PNG")
print("wrote", out, out.stat().st_size)
