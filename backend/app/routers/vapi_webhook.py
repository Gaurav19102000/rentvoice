"""Single Server URL that Vapi POSTs every event to.

Docs: https://docs.vapi.ai/server-url/events
Only `tool-calls` needs a meaningful response body: {"results": [{"toolCallId", "result"}]}
"""
import json
import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import RentalRequest
from ..notify import send_chat_link
from ..services import property_details, run_search

router = APIRouter(prefix="/api/vapi", tags=["voice"])
log = logging.getLogger("rentvoice.vapi")


def _verify(x_vapi_secret: str | None, authorization: str | None):
    if not settings.vapi_webhook_secret:
        return
    bearer = (authorization or "").removeprefix("Bearer ").strip()
    if settings.vapi_webhook_secret not in {x_vapi_secret, bearer}:
        raise HTTPException(401, "Bad webhook secret")


def _find_request(db: Session, message: dict, args: dict | None = None) -> RentalRequest | None:
    call = message.get("call") or {}
    candidates = [
        (args or {}).get("request_id"),
        (call.get("metadata") or {}).get("request_id"),
        ((call.get("assistantOverrides") or {}).get("variableValues") or {}).get("request_id"),
    ]
    for rid in candidates:
        if rid and (req := db.get(RentalRequest, str(rid))):
            return req
    if call.get("id"):
        return db.scalar(select(RentalRequest).where(RentalRequest.call_id == call["id"]))
    return None


def _parse_tool_call(tc: dict) -> tuple[str, str, dict]:
    fn = tc.get("function") or {}
    name = tc.get("name") or fn.get("name", "")
    args = tc.get("arguments") or fn.get("arguments") or {}
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except json.JSONDecodeError:
            args = {}
    return tc.get("id", ""), name, args


@router.post("/webhook")
async def vapi_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_vapi_secret: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
):
    _verify(x_vapi_secret, authorization)
    body = await request.json()
    message = body.get("message", {})
    mtype = message.get("type")
    log.info("Vapi event: %s", mtype)

    if mtype == "tool-calls":
        results = []
        for tc in message.get("toolCallList", []):
            call_id, name, args = _parse_tool_call(tc)
            req = _find_request(db, message, args)
            if not req:
                results.append({"toolCallId": call_id, "error": "Unknown request. Apologise and end the call."})
                continue
            if name == "search_properties":
                result = run_search(db, req, args)
            elif name == "get_property_details":
                result = property_details(req, args.get("option_number", 1))
            else:
                results.append({"toolCallId": call_id, "error": f"Unknown tool {name}"})
                continue
            results.append({"toolCallId": call_id, "name": name, "result": result})
        return {"results": results}

    req = _find_request(db, message)
    if not req:
        return {"ok": True}

    if mtype == "status-update":
        status = message.get("status")
        if status == "in-progress" and req.status in {"submitted", "calling"}:
            req.status = "in_call"
        elif status == "ended" and req.status in {"calling", "in_call"}:
            req.status = "call_failed" if not req.matches else req.status
        db.commit()

    elif mtype == "end-of-call-report":
        artifact = message.get("artifact") or {}
        req.transcript = artifact.get("transcript") or message.get("transcript") or ""
        req.call_summary = (message.get("analysis") or {}).get("summary") or message.get("summary") or ""
        if req.status in {"calling", "in_call"}:
            req.status = "no_match" if not req.matches else "matched"
        db.commit()
        if req.matches and req.call_mode == "phone":
            send_chat_link(req.phone, req.name, req.chat_token)

    return {"ok": True}
