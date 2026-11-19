"""Known localities with approximate centre coordinates.

In production you would geocode with Google Maps / Mapbox / Nominatim.
For the MVP a lookup table keeps it free, fast and deterministic.
"""
import difflib
import math

LOCALITIES: dict[str, dict[str, tuple[float, float]]] = {
    "bengaluru": {
        "Koramangala": (12.9352, 77.6245),
        "Indiranagar": (12.9719, 77.6412),
        "HSR Layout": (12.9116, 77.6474),
        "Whitefield": (12.9698, 77.7500),
        "Electronic City": (12.8452, 77.6602),
        "Marathahalli": (12.9591, 77.6974),
        "BTM Layout": (12.9166, 77.6101),
        "Jayanagar": (12.9250, 77.5938),
        "JP Nagar": (12.9063, 77.5857),
        "Bellandur": (12.9304, 77.6784),
        "Hebbal": (13.0358, 77.5970),
        "Yelahanka": (13.1007, 77.5963),
        "Malleshwaram": (13.0031, 77.5643),
        "Banashankari": (12.9255, 77.5468),
        "Sarjapur Road": (12.9010, 77.6860),
        "MG Road": (12.9756, 77.6050),
    }
}

CITY_ALIASES = {"bangalore": "bengaluru", "blr": "bengaluru", "bengaluru": "bengaluru"}


def normalize_city(city: str | None) -> str:
    c = (city or "").strip().lower()
    return CITY_ALIASES.get(c, c)


def resolve_locality(city: str | None, spoken: str | None) -> tuple[str, tuple[float, float]] | None:
    """Map what the caller said ("koramangla 5th block") to a known locality."""
    if not spoken:
        return None
    table = LOCALITIES.get(normalize_city(city), {})
    if not table:
        return None
    text = spoken.strip().lower()
    for name, coords in table.items():
        if name.lower() in text or text in name.lower():
            return name, coords
    lowered = {n.lower(): n for n in table}
    hit = difflib.get_close_matches(text, list(lowered), n=1, cutoff=0.6)
    if hit:
        name = lowered[hit[0]]
        return name, table[name]
    return None


def haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    d = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(d))
