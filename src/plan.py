"""Validate / repair Gemma JSON plans; add walking times, field challenge, map URL."""

from __future__ import annotations

import math
import re
import unicodedata
from typing import Any
from urllib.parse import quote


WALK_SPEED_KMH = 4.5  # casual urban walk


def walk_minutes(distance_km: float) -> int:
    if distance_km is None:
        return 0
    mins = (float(distance_km) / WALK_SPEED_KMH) * 60.0
    return max(1, int(round(mins)))


def enrich_spots(spots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for s in spots:
        s2 = dict(s)
        s2["walk_min"] = walk_minutes(s.get("distance_km") or 0)
        out.append(s2)
    return out


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s


def _match_place(name: str, spots: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not name:
        return None
    # Tiny models sometimes paste "Name | kind=park | 0.15 km" — keep the name part.
    name = str(name).split("|")[0].split(" (")[0].strip()
    n = _norm(name)
    # exact
    for s in spots:
        if _norm(s["name"]) == n:
            return s
    # contains / contained
    for s in spots:
        sn = _norm(s["name"])
        if n in sn or sn in n:
            return s
    # token overlap
    ntoks = set(n.split())
    best, best_score = None, 0
    for s in spots:
        stoks = set(_norm(s["name"]).split())
        if not stoks:
            continue
        score = len(ntoks & stoks) / max(len(ntoks | stoks), 1)
        if score > best_score:
            best, best_score = s, score
    if best and best_score >= 0.45:
        return best
    return None


def _default_field_challenge(mood: str, language: str) -> list[str]:
    m = (mood or "").lower()
    es = language.lower().startswith("es")
    if "bird" in m or "ave" in m:
        return (
            ["Marca 3 aves distintas", "Escucha 1 canto sin grabar", "Siéntate 2 min sin mirar el celular"]
            if es
            else ["Spot 3 different birds", "Hear 1 call without recording", "Sit 2 min without checking your phone"]
        )
    if "bike" in m or "bici" in m or "cicl" in m:
        return (
            ["Cuenta 5 árboles en la ruta", "Saluda a un ciclista", "Para 2 min y mira el cielo"]
            if es
            else ["Count 5 trees on the route", "Wave to another cyclist", "Stop 2 min and look at the sky"]
        )
    if "tianguis" in m or "mercado" in m or "market" in m:
        return (
            ["Prueba un olor nuevo (fruta/flor)", "Habla con un puesto (precio o tip)", "Camina 5 min sin auriculares"]
            if es
            else ["Notice one new smell (fruit/flower)", "Ask a stall one question", "Walk 5 min without earbuds"]
        )
    return (
        ["Señala 3 árboles distintos", "Escucha 1 sonido natural", "Siéntate 2 min sin celular"]
        if es
        else ["Spot 3 different trees", "Hear 1 natural sound", "Sit 2 min phone-down"]
    )


def _default_bring(weather: dict[str, Any], language: str) -> list[str]:
    es = language.lower().startswith("es")
    items = []
    label = (weather.get("label") or "").lower()
    advice = (weather.get("advice") or "").lower()
    if "rain" in label or "rain" in advice or "lluv" in advice:
        items.append("Paraguas compacto" if es else "Compact umbrella")
    temp = weather.get("temp_c")
    if isinstance(temp, (int, float)) and temp >= 26:
        items.append("Agua + bloqueador" if es else "Water + sunscreen")
    elif isinstance(temp, (int, float)) and temp <= 14:
        items.append("Chamarra ligera" if es else "Light jacket")
    else:
        items.append("Botella de agua" if es else "Water bottle")
    items.append("Zapatos cómodos" if es else "Comfortable shoes")
    if len(items) < 3:
        items.append("Efectivo chico" if es else "Small cash")
    return items[:3]


def _fallback_plan(
    *,
    neighborhood: str,
    minutes: int,
    mood: str,
    language: str,
    weather: dict[str, Any],
    spots: list[dict[str, Any]],
) -> dict[str, Any]:
    es = language.lower().startswith("es")
    primary = spots[0] if spots else {"name": neighborhood, "walk_min": 5, "distance_km": 0.3}
    secondary = spots[1] if len(spots) > 1 else primary
    walk = int(primary.get("walk_min") or 5)
    remain = max(15, minutes - walk)
    t1 = max(10, min(remain // 2, remain - 10))
    t2 = max(10, remain - t1)
    title = (
        f"{neighborhood}: {mood}" if not es else f"{neighborhood}: {mood}"
    )
    steps = [
        {
            "place": primary["name"],
            "minutes": t1,
            "why": (
                f"A ~{walk} min caminando; encaja con tu mood."
                if es
                else f"About {walk} min walk; fits your mood."
            ),
        }
    ]
    if minutes >= 40 and secondary["name"] != primary["name"]:
        steps.append(
            {
                "place": secondary["name"],
                "minutes": t2,
                "why": (
                    "Segundo tramo cercano para variar el paisaje."
                    if es
                    else "Nearby second stop for a change of scene."
                ),
            }
        )
    else:
        steps[0]["minutes"] = max(15, minutes - walk)
    rain = (
        f"Si llueve: quédate bajo los árboles/pérgola en {primary['name']} o acorta a 20 min."
        if es
        else f"If rain: stay under trees/pergola at {primary['name']} or shorten to 20 min."
    )
    tip = (
        "Pon el teléfono en modo avión al llegar al primer parque."
        if es
        else "Flip airplane mode when you reach the first park."
    )
    return {
        "title": title[:60],
        "steps": steps,
        "rain_backup": rain,
        "what_to_bring": _default_bring(weather, language),
        "leave_the_phone_tip": tip,
        "field_challenge": _default_field_challenge(mood, language),
        "phone_down_minutes": max(10, int(round(minutes * 0.7))),
        "_repaired": True,
        "_repair_notes": ["fallback_plan"],
    }


def validate_and_repair(
    raw: dict[str, Any] | None,
    *,
    neighborhood: str,
    minutes: int,
    mood: str,
    language: str,
    weather: dict[str, Any],
    spots: list[dict[str, Any]],
) -> dict[str, Any]:
    notes: list[str] = []
    if not isinstance(raw, dict):
        plan = _fallback_plan(
            neighborhood=neighborhood,
            minutes=minutes,
            mood=mood,
            language=language,
            weather=weather,
            spots=spots,
        )
        notes.append("non_json_fallback")
        plan["_repair_notes"] = notes
        return plan

    plan = dict(raw)
    # Title
    title = str(plan.get("title") or "").strip() or f"{neighborhood} · {mood}"
    title = re.sub(r"\s+", " ", title)[:80]
    # common typo fixes from tiny models
    title = title.replace("Peseado", "Paseo").replace("peseado", "paseo")
    plan["title"] = title

    # Steps
    steps_in = plan.get("steps") or []
    if not isinstance(steps_in, list):
        steps_in = []
    fixed_steps = []
    used: set[str] = set()
    for st in steps_in[:5]:
        if not isinstance(st, dict):
            continue
        matched = _match_place(str(st.get("place") or ""), spots)
        if not matched:
            notes.append(f"dropped_unknown_place:{st.get('place')}")
            continue
        if matched["name"] in used:
            notes.append(f"dropped_duplicate:{matched['name']}")
            continue
        used.add(matched["name"])
        try:
            mins = int(st.get("minutes") or 15)
        except (TypeError, ValueError):
            mins = 15
        mins = max(5, min(mins, minutes))
        why = str(st.get("why") or "").strip()
        if len(why) > 140:
            why = why[:137] + "..."
        if not why:
            why = (
                f"A ~{matched.get('walk_min', '?')} min a pie."
                if language.lower().startswith("es")
                else f"About {matched.get('walk_min', '?')} min on foot."
            )
        fixed_steps.append({"place": matched["name"], "minutes": mins, "why": why})

    if not fixed_steps:
        fb = _fallback_plan(
            neighborhood=neighborhood,
            minutes=minutes,
            mood=mood,
            language=language,
            weather=weather,
            spots=spots,
        )
        notes.append("no_valid_steps")
        fb["_repair_notes"] = notes + fb.get("_repair_notes", [])
        return fb

    # Fit total minutes into budget (cap or stretch)
    total = sum(s["minutes"] for s in fixed_steps)
    if total > minutes or (total < minutes * 0.7 and total > 0):
        target = minutes if total > minutes else max(total, int(minutes * 0.85))
        scale = target / total
        for s in fixed_steps:
            s["minutes"] = max(5, int(round(s["minutes"] * scale)))
        notes.append("scaled_minutes")
        drift = (minutes if total > minutes else target) - sum(s["minutes"] for s in fixed_steps)
        fixed_steps[0]["minutes"] = max(5, fixed_steps[0]["minutes"] + drift)

    plan["steps"] = fixed_steps

    # Rain backup — ground any place names mentioned
    rain = str(plan.get("rain_backup") or "").strip()
    if not rain:
        rain = (
            f"Si llueve: acorta y quédate en {fixed_steps[0]['place']}."
            if language.lower().startswith("es")
            else f"If rain: shorten and stay at {fixed_steps[0]['place']}."
        )
        notes.append("default_rain")
    plan["rain_backup"] = rain[:220]

    bring = plan.get("what_to_bring") or []
    if not isinstance(bring, list) or len(bring) < 2:
        bring = _default_bring(weather, language)
        notes.append("default_bring")
    plan["what_to_bring"] = [str(x).strip()[:40] for x in bring[:5] if str(x).strip()]

    tip = str(plan.get("leave_the_phone_tip") or "").strip()
    if not tip:
        tip = (
            "Modo avión al llegar; revisa el mapa solo si te pierdes."
            if language.lower().startswith("es")
            else "Airplane mode on arrival; check the map only if lost."
        )
        notes.append("default_tip")
    plan["leave_the_phone_tip"] = tip[:200]

    fc = plan.get("field_challenge") or []
    if not isinstance(fc, list) or len(fc) < 2:
        fc = _default_field_challenge(mood, language)
        notes.append("default_field_challenge")
    plan["field_challenge"] = [str(x).strip()[:80] for x in fc[:3] if str(x).strip()]

    try:
        pdm = int(plan.get("phone_down_minutes") or round(minutes * 0.7))
    except (TypeError, ValueError):
        pdm = int(round(minutes * 0.7))
    plan["phone_down_minutes"] = max(10, min(pdm, minutes))

    plan["_repaired"] = bool(notes)
    plan["_repair_notes"] = notes
    return plan


def osm_route_url(origin: dict[str, Any], places: list[dict[str, Any]]) -> str:
    """Build an OpenStreetMap directions URL (walking) through the chosen places."""
    coords = []
    # start near neighborhood centroid
    if origin.get("lat") is not None:
        coords.append((origin["lat"], origin["lon"]))
    for p in places:
        if p.get("lat") is not None:
            coords.append((p["lat"], p["lon"]))
    if len(coords) < 2:
        # single point map
        lat = origin.get("lat", 19.43)
        lon = origin.get("lon", -99.13)
        return f"https://www.openstreetmap.org/?mlat={lat}&mlon={lon}#map=16/{lat}/{lon}"
    # OSM directions: route/foot/lat,lon;lat,lon
    path = ";".join(f"{lat},{lon}" for lat, lon in coords)
    return f"https://www.openstreetmap.org/directions?engine=fossgis_osrm_foot&route={quote(path, safe=';,')}"


def plan_centroid(places: list[dict[str, Any]], origin: dict[str, Any]) -> tuple[float, float]:
    pts = [(p["lat"], p["lon"]) for p in places if p.get("lat") is not None]
    if not pts:
        return float(origin["lat"]), float(origin["lon"])
    return (
        sum(p[0] for p in pts) / len(pts),
        sum(p[1] for p in pts) / len(pts),
    )


def tiny_route_svg(
    origin: dict[str, Any],
    places: list[dict[str, Any]],
    size: int = 180,
) -> str:
    """Tiny schematic SVG map (no tiles) for the printable card."""
    pts = []
    if origin.get("lat") is not None:
        pts.append(("Tú", float(origin["lat"]), float(origin["lon"]), "#2f6b3a"))
    for i, p in enumerate(places[:4]):
        if p.get("lat") is None:
            continue
        pts.append((str(i + 1), float(p["lat"]), float(p["lon"]), "#c45c26"))
    if len(pts) < 1:
        return ""
    lats = [p[1] for p in pts]
    lons = [p[2] for p in pts]
    pad = 0.002
    min_lat, max_lat = min(lats) - pad, max(lats) + pad
    min_lon, max_lon = min(lons) - pad, max(lons) + pad
    # avoid zero span
    if abs(max_lat - min_lat) < 1e-6:
        max_lat += 0.01
        min_lat -= 0.01
    if abs(max_lon - min_lon) < 1e-6:
        max_lon += 0.01
        min_lon -= 0.01

    def xy(lat: float, lon: float) -> tuple[float, float]:
        x = (lon - min_lon) / (max_lon - min_lon) * (size - 24) + 12
        y = (1 - (lat - min_lat) / (max_lat - min_lat)) * (size - 24) + 12
        return x, y

    circles = []
    lines = []
    prev = None
    for label, lat, lon, color in pts:
        x, y = xy(lat, lon)
        if prev:
            lines.append(
                f'<line x1="{prev[0]:.1f}" y1="{prev[1]:.1f}" x2="{x:.1f}" y2="{y:.1f}" '
                f'stroke="#8fbf8f" stroke-width="2" stroke-dasharray="4 3"/>'
            )
        circles.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" fill="{color}"/>'
            f'<text x="{x:.1f}" y="{y + 3.5:.1f}" text-anchor="middle" '
            f'font-size="8" fill="#fff" font-family="sans-serif">{label}</text>'
        )
        prev = (x, y)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
        f'viewBox="0 0 {size} {size}">'
        f'<rect width="100%" height="100%" rx="12" fill="#eef6ea" stroke="#2f6b3a"/>'
        + "".join(lines)
        + "".join(circles)
        + "</svg>"
    )
