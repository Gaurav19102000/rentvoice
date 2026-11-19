"""Chatbot brain. Uses Claude if ANTHROPIC_API_KEY is set, otherwise a rule-based fallback
so the demo still works offline."""
import json
import logging

from .config import settings
from .models import RentalRequest

log = logging.getLogger("rentvoice.llm")

SYSTEM = """You are RentVoice's chat assistant. The user already spoke to our voice agent.
Answer questions ONLY about the shortlisted homes below. Be concise (max 4 sentences),
compare options honestly, and use ₹ for money. If they want to proceed with a home,
tell them to press "Select this home" on its card to get the owner's contact.
Never invent facts that are not in the data. Never reveal owner contact details.

Preferences: {prefs}
Shortlist: {shortlist}"""


def _shortlist(req: RentalRequest) -> list[dict]:
    out = []
    for m in req.matches:
        p = m.property
        out.append({
            "option": m.rank, "title": p.title, "locality": p.locality, "rent": p.rent,
            "deposit": p.deposit, "bhk": p.bhk, "type": p.property_type, "furnishing": p.furnishing,
            "area_sqft": p.area_sqft, "amenities": p.amenities, "pets_allowed": p.pets_allowed,
            "available_from": str(p.available_from), "why_it_fits": m.reasons,
        })
    return out


def reply(req: RentalRequest, history: list[dict], user_text: str) -> str:
    if settings.anthropic_api_key:
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
            msgs = [{"role": h["role"], "content": h["content"]} for h in history[-10:]]
            msgs.append({"role": "user", "content": user_text})
            resp = client.messages.create(
                model=settings.llm_model,
                max_tokens=400,
                system=SYSTEM.format(prefs=json.dumps(req.preferences), shortlist=json.dumps(_shortlist(req))),
                messages=msgs,
            )
            return "".join(b.text for b in resp.content if b.type == "text").strip()
        except Exception as e:  # fall through to rules so the chat never dies in a demo
            log.warning("LLM failed, using fallback: %s", e)
    return _rule_based(req, user_text)


def _rule_based(req: RentalRequest, text: str) -> str:
    t = text.lower()
    homes = _shortlist(req)
    if not homes:
        return "You don't have a shortlist yet. Once your call finishes, your matches will appear here."
    if any(w in t for w in ["cheap", "lowest", "least", "budget"]):
        h = min(homes, key=lambda x: x["rent"])
        return f"The most affordable is option {h['option']}, {h['title']} at ₹{h['rent']:,}/month."
    if "deposit" in t:
        return " ".join(f"Option {h['option']}: ₹{h['deposit']:,} deposit." for h in homes)
    if "pet" in t:
        ok = [str(h["option"]) for h in homes if h["pets_allowed"]]
        return f"Pets are allowed in option {', '.join(ok)}." if ok else "None of these allow pets."
    if any(w in t for w in ["furnish", "furniture"]):
        return " ".join(f"Option {h['option']} is {h['furnishing']} furnished." for h in homes)
    if any(w in t for w in ["big", "size", "sqft", "area"]):
        h = max(homes, key=lambda x: x["area_sqft"])
        return f"The largest is option {h['option']} at {h['area_sqft']} sq ft."
    if any(w in t for w in ["compare", "best", "recommend", "which"]):
        h = homes[0]
        return (f"Option 1, {h['title']}, is the closest fit: {'; '.join(h['why_it_fits'][:3])}. "
                "Press \"Select this home\" when you're ready to contact the owner.")
    return ("I can compare rent, deposit, size, furnishing or pet rules across your shortlist. "
            "Try \"which is cheapest?\" or \"which allows pets?\"")
