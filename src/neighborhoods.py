"""Built-in Mexico City neighborhood centroids (approx.)."""

from __future__ import annotations

NEIGHBORHOODS: dict[str, dict] = {
    "condesa": {
        "name": "Condesa",
        "lat": 19.4126,
        "lon": -99.1703,
        "alcaldia": "Cuauhtémoc",
        "tips": "Tree-lined streets, Parque México, cafés nearby.",
    },
    "roma": {
        "name": "Roma Norte",
        "lat": 19.4194,
        "lon": -99.1617,
        "alcaldia": "Cuauhtémoc",
        "tips": "Walkable, Parque México/España close, street art.",
    },
    "coyoacan": {
        "name": "Coyoacán",
        "lat": 19.3500,
        "lon": -99.1620,
        "alcaldia": "Coyoacán",
        "tips": "Jardín Centenario, Viveros, weekend vibes.",
    },
    "centro": {
        "name": "Centro Histórico",
        "lat": 19.4326,
        "lon": -99.1332,
        "alcaldia": "Cuauhtémoc",
        "tips": "Zócalo area; combine short walk + Alameda.",
    },
    "chapultepec": {
        "name": "Chapultepec / Polanco",
        "lat": 19.4205,
        "lon": -99.1860,
        "alcaldia": "Miguel Hidalgo",
        "tips": "Bosque de Chapultepec, lakes, museums nearby.",
    },
    "santa_fe": {
        "name": "Santa Fe",
        "lat": 19.3590,
        "lon": -99.2610,
        "alcaldia": "Álvaro Obregón / Cuajimalpa",
        "tips": "More car-oriented; look for Parque La Mexicana.",
    },
    "xochimilco": {
        "name": "Xochimilco",
        "lat": 19.2570,
        "lon": -99.1030,
        "alcaldia": "Xochimilco",
        "tips": "Canals, chinampas, birdwatching energy.",
    },
    "tlalpan": {
        "name": "Tlalpan Centro",
        "lat": 19.2885,
        "lon": -99.1670,
        "alcaldia": "Tlalpan",
        "tips": "Colonial plaza + nearby green edges toward Ajusco.",
    },
}


def resolve(query: str) -> dict:
    """Resolve a neighborhood key or fuzzy name to coordinates."""
    key = query.strip().lower().replace(" ", "_").replace("á", "a").replace("é", "e")
    key = key.replace("í", "i").replace("ó", "o").replace("ú", "u").replace("ñ", "n")
    if key in NEIGHBORHOODS:
        return dict(NEIGHBORHOODS[key])
    # fuzzy contains
    for k, v in NEIGHBORHOODS.items():
        if key in k or key in v["name"].lower().replace(" ", "_"):
            return dict(v)
    raise KeyError(
        f"Unknown neighborhood '{query}'. Try: {', '.join(sorted(NEIGHBORHOODS))}"
    )


def list_names() -> list[str]:
    return [v["name"] for v in NEIGHBORHOODS.values()]
