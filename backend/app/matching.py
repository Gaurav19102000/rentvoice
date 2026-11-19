"""Matching engine: hard filters -> weighted scoring -> progressive relaxation.

Score out of 100:
  budget 35 | location 30 | bhk 15 | furnishing 10 | amenities 10
"""
from dataclasses import dataclass, field
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .config import settings
from .geo import haversine_km, normalize_city, resolve_locality
from .models import Property, utcnow


@dataclass
class Preferences:
    city: str
    budget_max: int | None = None
    locality: str | None = None
    bhk: int | None = None
    property_type: str | None = None
    furnishing: str | None = None
    amenities: list[str] = field(default_factory=list)
    pets: bool = False
    max_distance_km: float = 6.0

    @classmethod
    def from_dict(cls, d: dict) -> "Preferences":
        def _int(v):
            try:
                return int(float(v)) if v not in (None, "", "any") else None
            except (TypeError, ValueError):
                return None

        amen = d.get("amenities") or []
        if isinstance(amen, str):
            amen = [a.strip() for a in amen.split(",") if a.strip()]
        ptype = (d.get("property_type") or "").strip().lower().replace(" ", "_") or None
        furn = (d.get("furnishing") or "").strip().lower() or None
        if furn in {"any", "no preference"}:
            furn = None
        if furn == "semi-furnished":
            furn = "semi"
        if furn == "furnished":
            furn = "fully"
        return cls(
            city=d.get("city") or "",
            budget_max=_int(d.get("budget_max")),
            locality=d.get("locality") or None,
            bhk=_int(d.get("bhk")),
            property_type=None if ptype in {None, "any"} else ptype,
            furnishing=furn,
            amenities=[a.lower() for a in amen],
            pets=bool(d.get("pets")),
        )


@dataclass
class Scored:
    property: Property
    score: float
    reasons: list[str]


def _score(p: Property, prefs: Preferences, centre: tuple[float, float] | None, budget_cap: float) -> Scored | None:
    reasons: list[str] = []
    score = 0.0

    # Budget (35)
    if prefs.budget_max:
        if p.rent <= prefs.budget_max:
            score += 35
            saved = prefs.budget_max - p.rent
            reasons.append(f"Within budget" + (f", ₹{saved:,} under" if saved >= 1000 else ""))
        elif p.rent <= budget_cap:
            over = (p.rent - prefs.budget_max) / prefs.budget_max
            score += 35 * max(0.0, 1 - over / 0.2)
            reasons.append(f"₹{p.rent - prefs.budget_max:,} over budget")
        else:
            return None
    else:
        score += 20

    # Location (30)
    if centre:
        dist = haversine_km(centre, (p.lat, p.lng))
        if dist > prefs.max_distance_km:
            return None
        score += 30 * max(0.0, 1 - dist / prefs.max_distance_km)
        reasons.append(f"{dist:.1f} km from {resolve_locality(prefs.city, prefs.locality)[0]}")
    else:
        score += 15

    # BHK (15)
    if prefs.bhk is not None:
        if p.bhk == prefs.bhk:
            score += 15
            reasons.append(f"{p.bhk} BHK as requested" if p.bhk else "Studio as requested")
        else:
            score += 6
            reasons.append(f"{p.bhk} BHK instead of {prefs.bhk}")
    else:
        score += 8

    # Furnishing (10)
    if prefs.furnishing:
        if p.furnishing == prefs.furnishing:
            score += 10
            reasons.append(f"{p.furnishing.capitalize()} furnished")
    else:
        score += 5

    # Amenities (10)
    if prefs.amenities:
        have = {a.lower() for a in (p.amenities or [])}
        hit = [a for a in prefs.amenities if a in have]
        score += 10 * len(hit) / len(prefs.amenities)
        if hit:
            reasons.append("Has " + ", ".join(hit))
    else:
        score += 5

    return Scored(p, round(score, 1), reasons)


def search_properties(db: Session, raw_prefs: dict, limit: int = 3) -> tuple[list[Scored], str]:
    """Returns (top matches, relaxation note). The note is '' when nothing was relaxed."""
    prefs = Preferences.from_dict(raw_prefs)
    fresh_after = utcnow() - timedelta(days=settings.listing_ttl_days)

    stmt = select(Property).where(
        Property.is_active.is_(True),
        Property.last_verified_at >= fresh_after,
        func.lower(Property.city) == normalize_city(prefs.city),
    )
    if prefs.property_type:
        stmt = stmt.where(Property.property_type == prefs.property_type)
    if prefs.pets:
        stmt = stmt.where(Property.pets_allowed.is_(True))
    candidates = list(db.scalars(stmt))

    loc = resolve_locality(prefs.city, prefs.locality)
    centre = loc[1] if loc else None

    # Progressive relaxation: strict first, then loosen one constraint at a time.
    steps = [
        ("", 1.0, 0, prefs.max_distance_km),
        ("Included homes with one more or one fewer bedroom.", 1.0, 1, prefs.max_distance_km),
        ("Included homes up to 10% over budget.", 1.10, 1, prefs.max_distance_km),
        ("Widened the search area to 12 km.", 1.10, 1, 12.0),
    ]
    results: list[Scored] = []
    notes: list[str] = []
    for msg, budget_mult, bhk_slack, radius in steps:
        prefs.max_distance_km = radius
        cap = (prefs.budget_max or 10**9) * budget_mult
        results = []
        for p in candidates:
            if prefs.bhk is not None and abs(p.bhk - prefs.bhk) > bhk_slack:
                continue
            s = _score(p, prefs, centre, cap)
            if s:
                results.append(s)
        if msg:
            notes.append(msg)
        if len(results) >= limit:
            break

    results.sort(key=lambda s: (-s.score, s.property.rent))
    note = " ".join(notes) if results else ""
    return results[:limit], note


def voice_summary(matches: list[Scored], note: str) -> str:
    """Short, speakable text the voice agent reads out."""
    if not matches:
        return (
            "No listings match right now. Suggest raising the budget or trying a nearby area, "
            "and offer to search again."
        )
    lines = []
    if note:
        lines.append(f"Note for caller: {note}")
    for i, m in enumerate(matches, 1):
        p = m.property
        kind = "studio" if p.bhk == 0 else f"{p.bhk} BHK {p.property_type.replace('_', ' ')}"
        lines.append(
            f"Option {i}: {kind} in {p.locality}, rent {p.rent} rupees a month, "
            f"{p.furnishing} furnished. Why it fits: {'; '.join(m.reasons[:2])}."
        )
    lines.append("Tell the caller the full details and owner contact will be in their chat link.")
    return "\n".join(lines)
