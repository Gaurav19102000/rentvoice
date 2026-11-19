"""Business logic shared by the voice webhook and the demo simulator."""
from sqlalchemy.orm import Session

from .matching import search_properties, voice_summary
from .models import Match, RentalRequest
from .schemas import MatchOut, PropertyPublic, RequestOut


def run_search(db: Session, req: RentalRequest, args: dict) -> str:
    prefs = {k: v for k, v in args.items() if k != "request_id" and v not in (None, "")}
    prefs.setdefault("city", req.city)
    results, note = search_properties(db, prefs)

    req.preferences = prefs
    req.relaxation_note = note
    req.matches.clear()
    db.flush()
    for rank, s in enumerate(results, 1):
        req.matches.append(Match(property_id=s.property.id, rank=rank, score=s.score, reasons=s.reasons))
    req.status = "matched" if results else "no_match"
    db.commit()
    db.refresh(req)
    return voice_summary(results, note)


def property_details(req: RentalRequest, option_number: int) -> str:
    m = next((m for m in req.matches if m.rank == int(option_number)), None)
    if not m:
        return "That option doesn't exist. Offer the options already listed."
    p = m.property
    return (
        f"{p.title}. {p.area_sqft} square feet, deposit {p.deposit} rupees, "
        f"available from {p.available_from:%d %B}. Amenities: {', '.join(p.amenities) or 'none listed'}. "
        f"Pets {'allowed' if p.pets_allowed else 'not allowed'}. {p.description}"
    )


def to_out(req: RentalRequest) -> RequestOut:
    return RequestOut(
        id=req.id, name=req.name, city=req.city, call_mode=req.call_mode, status=req.status,
        preferences=req.preferences or {}, relaxation_note=req.relaxation_note or "",
        call_summary=req.call_summary or "", chat_token=req.chat_token, created_at=req.created_at,
        matches=[
            MatchOut(rank=m.rank, score=m.score, reasons=m.reasons,
                     property=PropertyPublic.model_validate(m.property))
            for m in req.matches
        ],
    )
