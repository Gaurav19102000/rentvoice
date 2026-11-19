from datetime import date

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import Property, RentalRequest, utcnow
from ..schemas import PropertyFull, PropertyIn


def require_admin(x_admin_token: str | None = Header(default=None)):
    if x_admin_token != settings.admin_token:
        raise HTTPException(401, "Admin token is missing or wrong")


router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.get("/properties", response_model=list[PropertyFull])
def list_properties(db: Session = Depends(get_db)):
    return db.scalars(select(Property).order_by(Property.id.desc())).all()


@router.post("/properties", response_model=PropertyFull, status_code=201)
def create_property(body: PropertyIn, db: Session = Depends(get_db)):
    data = body.model_dump()
    data["available_from"] = data["available_from"] or date.today()
    p = Property(**data)
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


@router.post("/properties/{pid}/verify", response_model=PropertyFull)
def verify_property(pid: int, db: Session = Depends(get_db)):
    """Owner confirmed it's still available -> refresh freshness timestamp."""
    p = db.get(Property, pid)
    if not p:
        raise HTTPException(404, "Property not found")
    p.last_verified_at = utcnow()
    p.is_active = True
    db.commit()
    return p


@router.post("/properties/{pid}/toggle", response_model=PropertyFull)
def toggle_property(pid: int, db: Session = Depends(get_db)):
    p = db.get(Property, pid)
    if not p:
        raise HTTPException(404, "Property not found")
    p.is_active = not p.is_active
    db.commit()
    return p


@router.get("/requests")
def list_requests(db: Session = Depends(get_db)):
    rows = db.scalars(select(RentalRequest).order_by(RentalRequest.created_at.desc()).limit(100))
    return [
        {"id": r.id, "name": r.name, "phone": r.phone, "status": r.status, "call_mode": r.call_mode,
         "preferences": r.preferences, "matches": len(r.matches), "created_at": r.created_at,
         "selected_property_id": r.selected_property_id}
        for r in rows
    ]
