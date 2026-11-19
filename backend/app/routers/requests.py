import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from ..config import settings
from ..database import SessionLocal, get_db
from ..models import RentalRequest
from ..schemas import AttachCallIn, RequestCreate, RequestOut
from ..services import run_search, to_out
from ..voice import call_variables, start_outbound_call

router = APIRouter(prefix="/api", tags=["requests"])
log = logging.getLogger("rentvoice.requests")


async def _place_call(request_id: str):
    db = SessionLocal()
    try:
        req = db.get(RentalRequest, request_id)
        req.status = "calling"
        db.commit()
        try:
            req.call_id = await start_outbound_call(req)
        except Exception as e:
            log.error("Outbound call failed: %s", e)
            req.status = "call_failed"
        db.commit()
    finally:
        db.close()


@router.get("/config")
def public_config():
    """Non-secret settings the frontend needs."""
    return {
        "phone_calls_enabled": settings.phone_calls_enabled,
        "web_calls_enabled": settings.web_calls_enabled,
        "vapi_public_key": settings.vapi_public_key,
        "vapi_assistant_id": settings.vapi_assistant_id,
        "demo_mode": settings.demo_mode,
    }


@router.post("/requests", response_model=RequestOut, status_code=201)
def create_request(body: RequestCreate, bg: BackgroundTasks, db: Session = Depends(get_db)):
    if body.call_mode == "phone" and not settings.phone_calls_enabled:
        body.call_mode = "web"  # graceful fallback: talk in the browser instead
    req = RentalRequest(**body.model_dump())
    db.add(req)
    db.commit()
    db.refresh(req)
    if req.call_mode == "phone":
        bg.add_task(_place_call, req.id)
    return to_out(req)


@router.get("/requests/{request_id}", response_model=RequestOut)
def get_request(request_id: str, db: Session = Depends(get_db)):
    req = db.get(RentalRequest, request_id)
    if not req:
        raise HTTPException(404, "Request not found")
    return to_out(req)


@router.get("/requests/{request_id}/call-variables")
def get_call_variables(request_id: str, db: Session = Depends(get_db)):
    req = db.get(RentalRequest, request_id)
    if not req:
        raise HTTPException(404, "Request not found")
    return call_variables(req)


@router.post("/requests/{request_id}/call", response_model=RequestOut)
def retry_call(request_id: str, bg: BackgroundTasks, db: Session = Depends(get_db)):
    req = db.get(RentalRequest, request_id)
    if not req:
        raise HTTPException(404, "Request not found")
    if not settings.phone_calls_enabled:
        raise HTTPException(400, "Phone calls are not configured. Use the browser call instead.")
    bg.add_task(_place_call, req.id)
    return to_out(req)


@router.post("/requests/{request_id}/web-call", response_model=RequestOut)
def attach_web_call(request_id: str, body: AttachCallIn, db: Session = Depends(get_db)):
    """The browser tells us its Vapi call id so webhooks can be linked back."""
    req = db.get(RentalRequest, request_id)
    if not req:
        raise HTTPException(404, "Request not found")
    req.call_id = body.call_id
    req.status = "in_call"
    db.commit()
    return to_out(req)


@router.post("/dev/simulate/{request_id}", response_model=RequestOut)
def simulate_call(request_id: str, prefs: dict, db: Session = Depends(get_db)):
    """Runs exactly what the voice agent's tool call would run. For demos without Vapi credits."""
    if not settings.demo_mode:
        raise HTTPException(403, "Demo mode is off")
    req = db.get(RentalRequest, request_id)
    if not req:
        raise HTTPException(404, "Request not found")
    run_search(db, req, prefs)
    req.call_summary = "Simulated call: preferences entered from the demo panel."
    db.commit()
    return to_out(req)
