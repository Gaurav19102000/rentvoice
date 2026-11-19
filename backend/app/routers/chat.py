from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import llm
from ..database import get_db
from ..models import ChatMessage, Property, RentalRequest
from ..schemas import ChatIn, PropertyFull, SelectIn
from ..services import to_out

router = APIRouter(prefix="/api/chat", tags=["chat"])


def _by_token(db: Session, token: str) -> RentalRequest:
    req = db.scalar(select(RentalRequest).where(RentalRequest.chat_token == token))
    if not req:
        raise HTTPException(404, "This chat link is invalid or has expired")
    return req


def _messages(db: Session, req: RentalRequest) -> list[dict]:
    rows = db.scalars(
        select(ChatMessage).where(ChatMessage.request_id == req.id).order_by(ChatMessage.id)
    )
    return [{"role": m.role, "content": m.content, "created_at": m.created_at} for m in rows]


def _selected(db: Session, req: RentalRequest):
    if not req.selected_property_id:
        return None
    return PropertyFull.model_validate(db.get(Property, req.selected_property_id))


@router.get("/{token}")
def get_chat(token: str, db: Session = Depends(get_db)):
    req = _by_token(db, token)
    msgs = _messages(db, req)
    if not msgs and req.matches:
        greeting = (f"Hi {req.name.split()[0]}! Here are the {len(req.matches)} homes from your call. "
                    "Ask me anything about them, or select one to get the owner's contact.")
        db.add(ChatMessage(request_id=req.id, role="assistant", content=greeting))
        db.commit()
        msgs = _messages(db, req)
    return {"request": to_out(req), "messages": msgs, "selected": _selected(db, req)}


@router.post("/{token}/messages")
def send_message(token: str, body: ChatIn, db: Session = Depends(get_db)):
    req = _by_token(db, token)
    history = [{"role": m["role"], "content": m["content"]} for m in _messages(db, req)]
    # Anthropic requires the first message to be from the user
    while history and history[0]["role"] == "assistant":
        history.pop(0)
    answer = llm.reply(req, history, body.content)
    db.add_all([
        ChatMessage(request_id=req.id, role="user", content=body.content),
        ChatMessage(request_id=req.id, role="assistant", content=answer),
    ])
    db.commit()
    return {"messages": _messages(db, req)}


@router.post("/{token}/select")
def select_property(token: str, body: SelectIn, db: Session = Depends(get_db)):
    req = _by_token(db, token)
    if body.property_id not in {m.property_id for m in req.matches}:
        raise HTTPException(400, "You can only select a home from your shortlist")
    req.selected_property_id = body.property_id
    req.status = "completed"
    p = db.get(Property, body.property_id)
    db.add(ChatMessage(
        request_id=req.id, role="assistant",
        content=f"Great choice. You can reach {p.owner_name} at {p.owner_phone} about {p.title}. "
                "Mention RentVoice when you call.",
    ))
    db.commit()
    return {"selected": PropertyFull.model_validate(p), "messages": _messages(db, req)}
