"""Open-Meteo weather helper (no API key) with offline cache fallback."""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

CACHE_PATH = Path(__file__).resolve().parents[1] / "data" / "weather_cache.json"


def fetch_weather(lat: float, lon: float, hours: int = 6, offline: bool = False) -> dict[str, Any]:
    """Fetch current + hourly forecast from Open-Meteo. Falls back to cache if offline."""
    if offline or os.environ.get("SALA_OFFLINE") == "1":
        return _from_cache(lat, lon) | {"source": "cache", "offline": True}
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m",
        "hourly": "temperature_2m,precipitation_probability,weather_code",
        "timezone": "America/Mexico_City",
        "forecast_days": 1,
    }
    url = "https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:  # noqa: BLE001
        print(f"[weather] Open-Meteo unavailable ({e}); using cache.", flush=True)
        return _from_cache(lat, lon) | {"source": "cache", "offline": True}
    current = data.get("current", {})
    hourly = data.get("hourly", {})
    temps = (hourly.get("temperature_2m") or [])[:hours]
    pops = (hourly.get("precipitation_probability") or [])[:hours]
    summary = {
        "temp_c": current.get("temperature_2m"),
        "humidity": current.get("relative_humidity_2m"),
        "precip_mm": current.get("precipitation"),
        "weather_code": current.get("weather_code"),
        "wind_kmh": current.get("wind_speed_10m"),
        "next_hours_temp_c": temps,
        "next_hours_precip_prob": pops,
        "label": _label(current.get("weather_code"), current.get("precipitation")),
        "advice": _advice(current, pops),
        "source": "open-meteo",
        "offline": False,
    }
    _save_cache(lat, lon, summary)
    return summary


def _cache_key(lat: float, lon: float) -> str:
    return f"{round(lat, 2)},{round(lon, 2)}"


def _load_cache_file() -> dict:
    if CACHE_PATH.exists():
        try:
            return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            return {}
    return {}


def _save_cache(lat: float, lon: float, summary: dict[str, Any]) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = _load_cache_file()
    data[_cache_key(lat, lon)] = summary
    data["_default"] = summary
    CACHE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _from_cache(lat: float, lon: float) -> dict[str, Any]:
    data = _load_cache_file()
    hit = data.get(_cache_key(lat, lon)) or data.get("_default")
    if hit:
        return dict(hit)
    # Hardcoded mild CDMX autumn fallback
    return {
        "temp_c": 20.0,
        "humidity": 60,
        "precip_mm": 0.0,
        "weather_code": 2,
        "wind_kmh": 8.0,
        "next_hours_temp_c": [20, 19, 18, 18, 17, 17],
        "next_hours_precip_prob": [20, 20, 15, 15, 10, 10],
        "label": "Partly cloudy",
        "advice": "Mild temps — comfortable for walking. Low rain chance in the next hours.",
    }


def _label(code: int | None, precip: float | None) -> str:
    if precip and precip > 0.2:
        return "Rainy / wet"
    mapping = {
        0: "Clear",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Foggy",
        48: "Foggy",
        51: "Light drizzle",
        53: "Drizzle",
        55: "Dense drizzle",
        61: "Rain",
        63: "Rain",
        65: "Heavy rain",
        71: "Snow",
        80: "Showers",
        95: "Thunderstorm",
    }
    return mapping.get(code or -1, f"Code {code}")


def _advice(current: dict, pops: list) -> str:
    temp = current.get("temperature_2m")
    max_pop = max(pops) if pops else 0
    bits = []
    if temp is not None:
        if temp >= 28:
            bits.append("Bring water and sun protection.")
        elif temp <= 14:
            bits.append("Bring a light jacket.")
        else:
            bits.append("Mild temps — comfortable for walking.")
    if max_pop and max_pop >= 50:
        bits.append("Rain likely — pack a compact umbrella.")
    elif max_pop and max_pop >= 30:
        bits.append("Chance of showers — check the sky before you leave.")
    else:
        bits.append("Low rain chance in the next hours.")
    return " ".join(bits)
