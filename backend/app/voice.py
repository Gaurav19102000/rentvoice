"""Everything that talks to Vapi (the voice-agent platform).

Vapi handles: telephony, speech-to-text, the LLM turn-taking, text-to-speech.
We handle: business logic (matching) through a webhook "tool".
"""
import httpx

from .config import settings

VAPI_BASE = "https://api.vapi.ai"

SYSTEM_PROMPT = """You are Asha, a friendly rental assistant for RentVoice in {{city}}.
You are calling {{name}}, who just asked for help finding a rental home.

Goal: collect their preferences in a natural conversation, then call the
search_properties tool and present the results.

Collect, one question at a time (skip anything they already said):
1. Preferred area / locality (or near which office or landmark)
2. Maximum monthly rent in rupees
3. Number of bedrooms (BHK), or studio / PG
4. Property type: apartment, independent house, villa, PG, or no preference
5. Furnishing: unfurnished, semi, fully, or no preference
6. Must-haves such as parking, gym, power backup, lift; and whether they have pets

Rules:
- Keep every reply under two sentences. This is a phone call, not an essay.
- Confirm numbers back ("So, up to 25 thousand a month, right?").
- As soon as you know area, budget and BHK, call search_properties.
  Always pass request_id = {{request_id}} and city = {{city}}.
- Present at most 3 options briefly: BHK, area, rent, one reason it fits.
- If they want more on an option, call get_property_details.
- Never read out owner phone numbers. Say the full details and owner contact
  are waiting in their chat link, which they will receive right after the call.
- If nothing matches, suggest one change (budget or nearby area) and search again.
- End politely once they are happy.
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_properties",
            "description": "Search verified rental listings that match the caller's preferences.",
            "parameters": {
                "type": "object",
                "properties": {
                    "request_id": {"type": "string", "description": "Always {{request_id}}"},
                    "city": {"type": "string"},
                    "locality": {"type": "string", "description": "Preferred area, e.g. Koramangala"},
                    "budget_max": {"type": "number", "description": "Max monthly rent in INR"},
                    "bhk": {"type": "number", "description": "Bedrooms; 0 for studio/PG"},
                    "property_type": {
                        "type": "string",
                        "enum": ["apartment", "independent_house", "villa", "pg", "studio", "any"],
                    },
                    "furnishing": {"type": "string", "enum": ["unfurnished", "semi", "fully", "any"]},
                    "amenities": {"type": "array", "items": {"type": "string"}},
                    "pets": {"type": "boolean"},
                },
                "required": ["request_id", "city", "budget_max"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_property_details",
            "description": "Get more detail about one of the options already presented.",
            "parameters": {
                "type": "object",
                "properties": {
                    "request_id": {"type": "string"},
                    "option_number": {"type": "number", "description": "1, 2 or 3"},
                },
                "required": ["request_id", "option_number"],
            },
        },
    },
]


def assistant_config(server_url: str) -> dict:
    """Payload for POST /assistant. Pick the voice in the Vapi dashboard afterwards."""
    tools = []
    for t in TOOLS:
        tool = dict(t)
        tool["server"] = {"url": server_url}
        tools.append(tool)
    return {
        "name": "RentVoice Agent",
        "firstMessage": "Hi {{name}}, this is Asha from RentVoice. You asked for help finding a rental. "
                        "Do you have two minutes to tell me what you're looking for?",
        "model": {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "temperature": 0.3,
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}],
            "tools": tools,
        },
        "server": {"url": server_url},
        "serverMessages": ["tool-calls", "status-update", "end-of-call-report"],
        "endCallPhrases": ["goodbye", "bye bye", "thank you bye"],
        "maxDurationSeconds": 600,
    }


def call_variables(req) -> dict:
    return {"request_id": req.id, "name": req.name.split()[0], "city": req.city}


async def start_outbound_call(req) -> str:
    """Places a real phone call. Returns the Vapi call id."""
    payload = {
        "assistantId": settings.vapi_assistant_id,
        "phoneNumberId": settings.vapi_phone_number_id,
        "customer": {"number": req.phone, "name": req.name},
        "assistantOverrides": {"variableValues": call_variables(req)},
        "metadata": {"request_id": req.id},
    }
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(
            f"{VAPI_BASE}/call",
            json=payload,
            headers={"Authorization": f"Bearer {settings.vapi_api_key}"},
        )
        r.raise_for_status()
        return r.json().get("id", "")
