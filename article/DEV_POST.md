---
title: "Sal a la calle CDMX: a printable outdoor plan from local Gemma (so the screen ends at the park gate)"
published: false
tags: devchallenge, hf26challenge, gemma, opensource, python, mexico
---

*This is a submission for the [Hacktoberfest Open-Source AI Challenge Week 1: Touch Grass](https://dev.to/challenges/hacktoberfest-week1-2026-10-05)*

## What I Built

I live and work in Mexico City as an AI consultant for HR and recruitment. Most of my week is screens: models, dashboards, résumés. When I finally get a free hour, I do what everyone does — open Maps, weather, three “best parks” listicles — and somehow still stay on the couch.

**Sal a la calle CDMX** flips that loop.

You give it three things:

1. a **neighborhood** (Condesa, Coyoacán, Chapultepec…),
2. how many **minutes** you actually have, and
3. a **mood** (calm walk, birding, tianguis, easy bike).

It returns a **one-page outdoor plan card** — HTML or plain text — meant to be printed or screenshotted once. Then the phone goes in a pocket. The product is not a chat. The product is *you outside*.

Under the hood:

- **Open-Meteo** for live weather (no API key),
- **OpenStreetMap / Overpass** for nearby parks, gardens, and markets (with a curated CDMX seed fallback when public Overpass is overloaded),
- **Google’s open-weight Gemma 3 1B**, running **locally through Ollama**, to turn those facts into a short Spanish or English plan.

![Architecture](https://raw.githubusercontent.com/davidramsem/sal-a-la-calle/main/images/architecture.png)

Who is it for? Chilangos who overthink free time. Visitors who want something more local than “go to the Zócalo.” Anyone who believes an AI tool can earn its keep by *ending* the session quickly.

## Demo

I ran the full pipeline on 2026-10-05 (CST) on a CPU-only Linux box. No fabricated timings — these are real Ollama evals with `gemma3-1b-cdmx` (Gemma 3 1B Instruct, Q4_K_M GGUF).

| Run | Inputs | Model wall time |
|-----|--------|-----------------|
| Condesa | 60 min · *paseo tranquilo* · ES | **19.18 s** |
| Coyoacán | 90 min · birdwatching · ES | **13.53 s** |
| Chapultepec | 45 min · easy bike · EN | **13.03 s** |

Weather that afternoon was honestly rainy (~19°C), so Gemma leaned into umbrellas and short sheltered walks — which is exactly the kind of boring-but-useful advice you want before leaving the house.

![CLI demo](https://raw.githubusercontent.com/davidramsem/sal-a-la-calle/main/images/cli_demo.png)

Sample excerpt (Condesa, real output):

> **Primary Activity:** Bird Watching & Gentle Stroll  
> 1. Start at Parque México (~0.15 km)  
> 2. Explore the park’s trails / birdwatching areas (30 minutes)  
> 3. If rain persists, short sheltered walk in the same park  
> 4. Coffee + pastel at Mercado de Medellín (~0.87 km) as backup  
> **Leave the Phone:** Disconnect from technology and truly enjoy the moment

![Plan card — Condesa](https://raw.githubusercontent.com/davidramsem/sal-a-la-calle/main/images/plan_card_condesa.png)

Repo (to be published): `https://github.com/davidramsem/sal-a-la-calle`  
Clone, start Ollama with a Gemma tag, run:

```bash
python -m src.main -n condesa -m 60 --mood "paseo tranquilo" --lang es
# open samples/*.html → print → leave
```

### Outdoor test (placeholder for Alex)

> **🚧 TOUCH GRASS FIELD NOTE — fill in after you walk a plan**  
> Date / barrio: _______________  
> Which sample plan did you follow?: _______________  
> What matched reality (park open, birds, rain tip)?: _______________  
> What Gemma invented or got wrong?: _______________  
> Photo of the printed card outdoors (optional): _______________  
>  
> *I am not claiming an outdoor test in this draft. The engineering run is real; the sidewalk story is yours to add before publishing.*

## Code

GitHub repo: **[davidramsem/sal-a-la-calle](https://github.com/davidramsem/sal-a-la-calle)** *(publish the contents of `repo_upload/`)*

Core idea in one sentence: *retrieve open facts → prompt a local open-weight model → emit a printable artifact, not another feed.*

```text
CLI → barrio coords → Open-Meteo → OSM/seed spots → local Gemma → TXT/HTML card
```

Stack choices I deliberately kept small:

- Python stdlib `urllib` for HTTP (no heavy framework),
- Ollama HTTP `/api/generate` for inference,
- Jinja-free HTML templates as plain f-strings (easy to read in a PR),
- MIT license, no bundled model weights.

## How I Built It

### Open-source AI at the core

This is not “call GPT and sprinkle some parks.” **Gemma is the planner.** Without a local open-weight model, the project collapses into a static list of links. With Gemma:

- the same retrieved spots become a *timed* itinerary matched to mood,
- language flips ES/EN without a second product,
- rainy-day advice appears because weather is in the prompt, not because I hardcoded an if-tree for every mood.

I installed Ollama on Linux, could not `ollama pull` through a CDN redirect quirk on this network, and instead downloaded the public GGUF `gemma-3-1b-it-Q4_K_M` (from `ggml-org` on Hugging Face) and `ollama create`’d a local tag `gemma3-1b-cdmx`. On CPU, cold-ish generations for a ~200-word plan landed in **13–19 seconds**. That is slow for chat — and *perfect* for a tool you run once before leaving.

### Open data as grounding

Small models hallucinate transit lines. I accept that and **ground** them:

- neighborhood centroids for CDMX barrios,
- live weather from Open-Meteo,
- OSM parks/markets via Overpass when reachable,
- a clearly labeled curated seed of real CDMX places when Overpass times out (it did, intermittently, during builds).

The plan card always shows the spots list separately so a human can sanity-check before walking.

### Design constraint from the theme

Touch Grass asks for the screen to be the *shortest* part. So I optimized for:

- one command,
- one page,
- print CSS friendly HTML,
- a blunt footer: *Print · pocket · phone away · touch grass*.

No account. No streak. No push notifications “reminding” you to go outside (the irony would write itself).

## Why Does Open Innovation Matter?

If this planner depended on a closed cloud LLM, three things would break the use case:

1. **Location + mood are personal.** Even a “harmless” walk plan is a breadcrumb of where you live and when you’re free. Local Gemma means the prompt never leaves the laptop.
2. **Cost and offline reality.** I want this to run on a cheap CPU after work, not bill tokens every time Condesa looks tempting. Open weights + Ollama = **$0 inference**. Open-Meteo and OSM are free by design.
3. **Swappability.** Today it is Gemma 3 1B because it fits RAM. Tomorrow it can be `gemma3:4b` or another open instruct model by changing `SALA_MODEL`. The app does not care. That is the opposite of locking the product to one vendor’s chat API.

Open innovation here is not ideology — it is how you build a tool whose job is to *stop needing the network* the moment you step onto Parque México’s paths.

Closed APIs are excellent at infinite conversation. This challenge asked for the opposite: finite help, then grass.

## My Agent Session

Optional — add a DevRelay / agent session link here if you save one while polishing the post.

## Prize Categories

- **Best Use of Gemma** — local Gemma 3 1B (Ollama) is the planner that writes every outdoor card; open-weight inference is the product core, not a garnish.

---

Built in Mexico City · MIT · Map data © OpenStreetMap contributors · Weather © Open-Meteo · Model: Gemma (Google, open weights) via Ollama.

*Thanks for reading — now print a card and sal a la calle.*
