"""Open-Meteo weather helper (no API key)."""

from __future__ import annotations

import urllib.parse
import urllib.request
import json
from typing import Any


def fetch_weather(lat: float, lon: float, hours: int = 6) -> dict[str, Any]:
    """Fetch current + hourly forecast from Open-Meteo."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m",
        "hourly": "temperature_2m,precipitation_probability,weather_code",
        "timezone": "America/Mexico_City",
        "forecast_days": 1,
    }
    url = "https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=30) as resp:
        data = json.loads(resp.read().decode())
    current = data.get("current", {})
    hourly = data.get("hourly", {})
    # Pick next N hours summary
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
    }
    return summary


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
