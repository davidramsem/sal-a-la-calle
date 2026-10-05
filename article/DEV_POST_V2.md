---
title: "Sal a la calle CDMX: local Gemma prints your outdoor plan so the screen ends at the park gate"
published: false
tags: devchallenge, hf26challenge, gemma, opensource
---

*This is a submission for the [Hacktoberfest Open-Source AI Challenge Week 1: Touch Grass](https://dev.to/challenges/hacktoberfest-week1-2026-10-05)*

## What I Built

I live in Mexico City and work as an AI consultant for HR. Most of my week is screens: models, dashboards, résumés. When I finally get a free hour, I do what everyone does — open Maps, weather, three “best parks” listicles — and somehow still stay on the couch.

**Sal a la calle CDMX** flips that loop.

You give it three things:

1. a **neighborhood** (Condesa, Roma, Coyoacán, Chapultepec…),
2. how many **minutes** you actually have, and
3. a **mood** (paseo tranquilo, birding, tianguis, easy bike).

It returns a **one-page outdoor plan card** — HTML you can print, plus PNG — with:

- a timed route using **only real places** from OpenStreetMap / a CDMX seed list,
- walking times computed from distance (not vibes),
- a **QR code** to the OSM walking map,
- a tiny schematic route sketch,
- an offline **field challenge** (spot birds/trees, sit without the phone),
- a **phone-down timer** suggestion.

Then the product is done. The phone goes in a pocket. The artifact is not a chat — it is *you outside*.

Under the hood:

- **Open-Meteo** for weather (no API key) + offline cache,
- **OpenStreetMap / Overpass** for parks and markets (curated CDMX seed fallback when Overpass is busy),
- **Google’s open-weight Gemma 3** (4B Q4 by default, 1B optional), running **locally through Ollama**, emitting **structured JSON** that a validator repairs before render.

![Architecture](https://raw.githubusercontent.com/davidramsem/sal-a-la-calle/main/images/architecture.png)

Who is it for? Chilangos who overthink free time. Visitors who want something more local than “go to the Zócalo.” Anyone who believes an AI tool can earn its keep by *ending* the session quickly.

## Demo

Real CPU-only runs on 2026-10-05 (America/Mexico_City). No fabricated timings — these are Ollama evals on this laptop-class box.

| Run | Inputs | Model | Wall time | tok/s |
|-----|--------|-------|-----------|-------|
| Condesa | 60 min · *paseo tranquilo* · ES | **gemma3-4b-cdmx** | **51.4 s** | 7.0 |
| Coyoacán | 90 min · birding · ES | gemma3-4b-cdmx | **34.3 s** | 9.9 |
| Chapultepec | 45 min · easy bike · EN | gemma3-4b-cdmx | **35.8 s** | 10.2 |
| Roma Norte | 50 min · tianguis · ES | gemma3-4b-cdmx | **30.2 s** | 11.0 |
| Condesa (compare) | same as row 1 | **gemma3-1b-cdmx** | **21.8 s** | 33.4 |

That afternoon was rainy (~19°C), so the cards leaned into umbrellas and sheltered corners — boring-but-useful advice before you leave the house.

![Demo flow](https://raw.githubusercontent.com/davidramsem/sal-a-la-calle/main/images/demo_flow.gif)

![Gradio UI](https://raw.githubusercontent.com/davidramsem/sal-a-la-calle/main/images/ui_demo.png)

![UI with card](https://raw.githubusercontent.com/davidramsem/sal-a-la-calle/main/images/ui_with_card.png)

### Sample excerpt (Condesa, Gemma 3 4B — real structured output)

> **Paseo Tranquilo en Condesa**  
> 1. Parque México — área de aves — 14 min — Observar aves en un entorno relajado.  
> 2. Parque México — 15 min — Disfrutar del ambiente tranquilo del parque.  
> 3. Parque España — 22 min — Un paseo agradable por un parque con mucha sombra.  
> **Si llueve:** Parque México — área de aves (bajo los árboles)  
> **Lleva:** Paraguas compacto, Agua, Snacks ligeros  
> **Phone tip:** Apaga tu teléfono y disfruta del momento presente.  
> **Phone-down:** 45 min  
> **Field challenge:** [ ] Identificar al menos 3 especies de aves · [ ] Observar 5 árboles diferentes · [ ] Sentarse sin usar el teléfono durante 5 minutos

![Plan card — Condesa](https://raw.githubusercontent.com/davidramsem/sal-a-la-calle/main/images/plan_card_condesa.png)

![CLI output](https://raw.githubusercontent.com/davidramsem/sal-a-la-calle/main/images/cli_demo.png)

Repo: [davidramsem/sal-a-la-calle](https://github.com/davidramsem/sal-a-la-calle)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# ollama serve + create/pull Gemma (see README / Modelfile.example)
python -m src.main -n condesa -m 60 --mood "paseo tranquilo" --lang es
python -m src.app   # Gradio UI → Print button
```

### 1B vs 4B (same prompt, same barrio)

I kept both models honest.

| | Gemma 3 **1B** Q4 | Gemma 3 **4B** Q4 |
|--|-------------------|-------------------|
| Speed on this CPU | **~22 s**, ~33 tok/s | **~51 s**, ~7 tok/s |
| Structured JSON | Often truncated / polluted place strings (`Parque México \| kind=park \| 0.15 km…`), English mixed into Spanish prompts | Clean Spanish JSON matching the schema |
| Without repair | Invents bus lines, repeats headers, typos like “Peseado Tranquilo”, suggests transit to a park **0.15 km** away | Uses allowed place names, respects the minute budget after scaling |
| With our validator | Falls back to a safe grounded card (still printable) | Light repairs only (e.g. stretch minutes to use the budget) |

![1B vs 4B cards](https://raw.githubusercontent.com/davidramsem/sal-a-la-calle/main/images/compare_1b_vs_4b.png)

Default in the app is **4B**. Set `SALA_MODEL=gemma3-1b-cdmx` if you only have ~1 GB free RAM. Swapping models is one env var — that is the point of open weights.

### Outdoor test (placeholder for Alex)

> **🚧 TOUCH GRASS FIELD NOTE — fill in after you walk a plan**  
> Date / barrio: _______________  
> Which sample plan did you follow?: _______________  
> What matched reality (park open, birds, rain tip)?: _______________  
> What Gemma invented or got wrong?: _______________  
> Photo of the printed card outdoors (optional): _______________  
>  
> *I am not claiming an outdoor test in this draft. The engineering run is real; the sidewalk story is yours to add before publishing.*

## Demo / Code

GitHub: **[davidramsem/sal-a-la-calle](https://github.com/davidramsem/sal-a-la-calle)**

```text
CLI / Gradio
   → barrio coords
   → Open-Meteo (or cache)
   → OSM Overpass (or CDMX seed)
   → local Gemma → JSON
   → validate / repair / walk_min
   → HTML card + QR + PNG
```

Stack choices I deliberately kept small:

- Python stdlib `urllib` for HTTP in the core path,
- Ollama `/api/generate` with `format: "json"`,
- Gradio for a one-page local UI,
- Pillow + headless Chrome for PNG cards,
- `qrcode` for the OSM link,
- MIT license, **no bundled model weights**.

## How I Built It

### Open-source AI at the core

This is not “call GPT and sprinkle some parks.” **Gemma is the planner.** Without a local open-weight model, the project collapses into a static list of links. With Gemma:

- the same retrieved spots become a *timed* itinerary matched to mood,
- language flips ES/EN without a second product,
- rainy-day advice appears because weather is in the prompt,
- a tiny model and a bigger model are interchangeable behind `SALA_MODEL`.

I installed Ollama on Linux, could not `ollama pull` through a CDN redirect quirk on this network, and instead downloaded public GGUFs from Hugging Face (`gemma-3-1b-it-Q4_K_M` and `gemma-3-4b-it-Q4_K_M` via `ggml-org`) and `ollama create`’d local tags. On CPU:

- **1B** ≈ 15–22 s / plan, ~33 tok/s  
- **4B** ≈ 30–51 s / plan, ~7–11 tok/s  

Slow for chat. *Perfect* for a tool you run once before leaving.

### Structured output + grounding (the quality fix)

Week-1 drafts with freeform 1B text had real bugs: typos, duplicate lists, “take the bus to a park 0.15 km away.” So v2 does three unglamorous things:

1. Ask Gemma for **strict JSON** (`title`, `steps[{place,minutes,why}]`, `rain_backup`, `what_to_bring`, `leave_the_phone_tip`, `field_challenge`, `phone_down_minutes`).
2. **Validate and repair**: place names must fuzzy-match the OSM/seed list; unknown places are dropped; minutes are scaled into the budget; Spanish defaults fill missing tips.
3. **Compute walking times** from haversine distance at ~4.5 km/h and show them on the card (`0.15 km → ~2 min walk`), so the model does not get to invent transit for a two-minute stroll.

### Design constraint from the theme

Touch Grass asks for the screen to be the *shortest* part. So I optimized for:

- one command or one Gradio form,
- one printable page with a **Print** button,
- QR → OSM route (the phone can navigate once, then pocket),
- an offline **field challenge** you check with a pen,
- a blunt footer: *Print · pocket · phone away · touch grass*.

No account. No streak. No push notification “reminding” you to go outside (the irony would write itself).

`--offline` uses seed places + cached weather + local Gemma — no internet required after the first warm cache.

## Why Does Open Innovation Matter?

If this planner depended on a closed cloud LLM, three things would break the use case:

1. **Location + mood are personal.** Even a “harmless” walk plan is a breadcrumb of where you live and when you’re free. Local Gemma means the prompt never leaves the laptop.
2. **Cost and offline reality.** I want this to run on a cheap CPU after work, not bill tokens every time Condesa looks tempting. Open weights + Ollama = **$0 inference**. Open-Meteo and OSM are free by design. Offline mode keeps working when the café Wi-Fi does not.
3. **Swappability.** Today the default is Gemma 3 4B because quality beats the extra ~20 seconds. Tomorrow it can be another open instruct model by changing `SALA_MODEL`. The app does not care. That is the opposite of locking the product to one vendor’s chat API.

Open innovation here is not ideology — it is how you build a tool whose job is to *stop needing the network* the moment you step onto Parque México’s paths.

Closed APIs are excellent at infinite conversation. This challenge asked for the opposite: finite help, then grass.

## My Agent Session

Optional — add a DevRelay / agent session link here if you save one while polishing the post.

## Prize Categories

- **Best Use of Gemma** — local Gemma 3 (1B and 4B via Ollama) is the planner that writes every outdoor card; structured JSON + measured CPU speeds + a side-by-side quality comparison are the product core, not a garnish.

---

Built in Mexico City · MIT · Map data © OpenStreetMap contributors · Weather © Open-Meteo · Model: Gemma (Google, open weights) via Ollama.

*Thanks for reading — now print a card and sal a la calle.*
