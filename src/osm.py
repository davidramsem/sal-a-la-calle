"""OpenStreetMap Overpass queries for outdoor spots near a point.

Falls back to a curated CDMX open-data seed list when Overpass is unreachable
(common on busy public instances). Fallback spots are real, well-known places;
the plan card labels their source honestly.
"""

from __future__ import annotations

import json
import math
import urllib.request
from typing import Any

OVERPASS_URLS = [
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]

# Curated seed list (public landmarks) used only if Overpass fails.
# Coordinates approximate centroids — good enough for neighborhood matching.
CDMX_SEED: list[dict[str, Any]] = [
    {"name": "Parque México", "kind": "park", "lat": 19.4115, "lon": -99.1695},
    {"name": "Parque España", "kind": "park", "lat": 19.4160, "lon": -99.1715},
    {"name": "Parque Hundido", "kind": "park", "lat": 19.3820, "lon": -99.1850},
    {"name": "Bosque de Chapultepec (1a sección)", "kind": "park", "lat": 19.4205, "lon": -99.1865},
    {"name": "Lago de Chapultepec", "kind": "park", "lat": 19.4220, "lon": -99.1910},
    {"name": "Viveros de Coyoacán", "kind": "park", "lat": 19.3535, "lon": -99.1735},
    {"name": "Jardín Centenario", "kind": "garden", "lat": 19.3500, "lon": -99.1630},
    {"name": "Parque Nacional Fuentes Brotantes", "kind": "nature reserve", "lat": 19.2840, "lon": -99.1800},
    {"name": "Parque La Mexicana", "kind": "park", "lat": 19.3610, "lon": -99.2700},
    {"name": "Alameda Central", "kind": "park", "lat": 19.4355, "lon": -99.1440},
    {"name": "Plaza de la Constitución (Zócalo)", "kind": "plaza", "lat": 19.4326, "lon": -99.1332},
    {"name": "Tianguis Cultural del Chopo", "kind": "tianguis / market", "lat": 19.4480, "lon": -99.1565},
    {"name": "Mercado de Jamaica", "kind": "tianguis / market", "lat": 19.4070, "lon": -99.1230},
    {"name": "Mercado de Medellín", "kind": "tianguis / market", "lat": 19.4075, "lon": -99.1640},
    {"name": "Ciclovía Reforma", "kind": "bike route", "lat": 19.4280, "lon": -99.1670},
    {"name": "Parque Ecológico de Xochimilco", "kind": "nature reserve", "lat": 19.2930, "lon": -99.1010},
    {"name": "Embarcadero Nativitas (Xochimilco)", "kind": "birding", "lat": 19.2465, "lon": -99.0940},
    {"name": "Parque Lincoln", "kind": "park", "lat": 19.4295, "lon": -99.1935},
    {"name": "Parque de los Venados", "kind": "park", "lat": 19.3710, "lon": -99.1560},
    {"name": "Bosque de Tlalpan", "kind": "woods", "lat": 19.2950, "lon": -99.1750},
    {"name": "Pedregal / Reserva del Pedregal (UNAM area)", "kind": "nature reserve", "lat": 19.3180, "lon": -99.1850},
    {"name": "Parque México — área de aves", "kind": "birding", "lat": 19.4120, "lon": -99.1690},
    {"name": "Plaza Río de Janeiro", "kind": "plaza", "lat": 19.4198, "lon": -99.1605},
    {"name": "Jardin del Arte / Sullivan", "kind": "plaza", "lat": 19.4305, "lon": -99.1645},
    {"name": "Parque Luis G. Urbina (Ramón López Velarde)", "kind": "park", "lat": 19.4065, "lon": -99.1585},
]


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _post(query: str, timeout: int = 35) -> dict:
    data = "data=" + urllib.request.quote(query)
    last_err: Exception | None = None
    for url in OVERPASS_URLS:
        try:
            req = urllib.request.Request(
                url,
                data=data.encode("utf-8"),
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "User-Agent": "sal-a-la-calle/0.1 (Hacktoberfest; outdoor planner)",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:  # noqa: BLE001
            last_err = e
    raise RuntimeError(f"Overpass failed: {last_err}")


def _from_overpass(lat: float, lon: float, radius_m: int, limit: int) -> list[dict[str, Any]]:
    # Keep the query small so public instances respond quickly.
    q = f"""
    [out:json][timeout:25];
    (
      node["leisure"="park"](around:{radius_m},{lat},{lon});
      way["leisure"="park"](around:{radius_m},{lat},{lon});
      node["leisure"="garden"](around:{radius_m},{lat},{lon});
      node["amenity"="marketplace"](around:{radius_m},{lat},{lon});
      node["tourism"="viewpoint"](around:{radius_m},{lat},{lon});
    );
    out center tags 25;
    """
    raw = _post(q)
    elements = raw.get("elements") or []
    spots: list[dict[str, Any]] = []
    seen: set[str] = set()
    for el in elements:
        tags = el.get("tags") or {}
        name = tags.get("name") or tags.get("name:es") or tags.get("name:en")
        if not name:
            continue
        if el.get("type") == "node":
            slat, slon = el.get("lat"), el.get("lon")
        else:
            c = el.get("center") or {}
            slat, slon = c.get("lat"), c.get("lon")
        if slat is None or slon is None:
            continue
        kind = _kind(tags)
        key = f"{name}|{kind}"
        if key in seen:
            continue
        seen.add(key)
        dist = haversine_km(lat, lon, slat, slon)
        spots.append(
            {
                "name": name,
                "kind": kind,
                "lat": round(slat, 5),
                "lon": round(slon, 5),
                "distance_km": round(dist, 2),
                "source": "overpass",
                "tags": {
                    k: tags[k]
                    for k in ("leisure", "tourism", "amenity", "shop", "natural", "highway")
                    if k in tags
                },
            }
        )
    spots.sort(key=lambda s: (s["distance_km"], s["name"]))
    return spots[:limit]


def _from_seed(lat: float, lon: float, radius_m: int, limit: int) -> list[dict[str, Any]]:
    radius_km = radius_m / 1000.0
    # If nothing is within radius, expand to 5 km so the planner always has options.
    candidates = []
    for s in CDMX_SEED:
        d = haversine_km(lat, lon, s["lat"], s["lon"])
        candidates.append({**s, "distance_km": round(d, 2), "source": "cdmx_seed"})
    candidates.sort(key=lambda s: s["distance_km"])
    near = [c for c in candidates if c["distance_km"] <= max(radius_km, 3.5)]
    if len(near) < 3:
        near = candidates[: max(limit, 5)]
    return near[:limit]


def find_outdoor_spots(
    lat: float,
    lon: float,
    radius_m: int = 1800,
    limit: int = 12,
    force_seed: bool = False,
) -> list[dict[str, Any]]:
    """Find parks / markets near lat/lon. Tries Overpass, then curated seed."""
    if force_seed:
        return _from_seed(lat, lon, radius_m, limit)
    try:
        spots = _from_overpass(lat, lon, radius_m, limit)
        if spots:
            return spots
    except Exception as e:  # noqa: BLE001
        print(f"[osm] Overpass unavailable ({e}); using curated CDMX seed list.", flush=True)
    return _from_seed(lat, lon, radius_m, limit)


def _kind(tags: dict) -> str:
    if tags.get("leisure") == "park":
        return "park"
    if tags.get("leisure") == "garden":
        return "garden"
    if tags.get("leisure") == "nature_reserve":
        return "nature reserve"
    if tags.get("tourism") == "viewpoint":
        return "viewpoint"
    if tags.get("amenity") == "marketplace" or tags.get("shop") == "marketplace":
        return "tianguis / market"
    if tags.get("highway") == "cycleway":
        return "bike route"
    return "outdoor"
