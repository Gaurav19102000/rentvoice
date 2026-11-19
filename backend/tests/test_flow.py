"""End-to-end: form -> voice tool call -> chat -> select -> owner contact revealed."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_full_flow():
    r = client.post("/api/requests", json={"name": "Riya Sharma", "phone": "98765 43210",
                                           "city": "Bengaluru", "call_mode": "web", "consent": True})
    assert r.status_code == 201, r.text
    req = r.json()
    assert req["status"] == "submitted"

    # Simulate exactly what Vapi POSTs when the agent calls the tool
    payload = {"message": {
        "type": "tool-calls",
        "call": {"id": "call_123", "metadata": {"request_id": req["id"]}},
        "toolCallList": [{"id": "tc_1", "type": "function", "function": {
            "name": "search_properties",
            "arguments": {"request_id": req["id"], "city": "Bengaluru", "locality": "Koramangala",
                          "budget_max": 40000, "bhk": 2}}}],
    }}
    r = client.post("/api/vapi/webhook", json=payload)
    assert r.status_code == 200
    result = r.json()["results"][0]
    assert result["toolCallId"] == "tc_1" and "Option 1" in result["result"]

    # Details tool, arguments as a JSON string (Vapi sometimes sends that)
    payload["message"]["toolCallList"] = [{"id": "tc_2", "name": "get_property_details",
                                           "arguments": '{"option_number": 2}'}]
    r = client.post("/api/vapi/webhook", json=payload)
    assert "square feet" in r.json()["results"][0]["result"]

    # End of call
    client.post("/api/vapi/webhook", json={"message": {
        "type": "end-of-call-report", "call": {"id": "call_123", "metadata": {"request_id": req["id"]}},
        "artifact": {"transcript": "AI: Hi... User: 2BHK in Koramangala"}, "analysis": {"summary": "Wants 2BHK"}}})

    status = client.get(f"/api/requests/{req['id']}").json()
    assert status["status"] == "matched" and status["matches"]
    assert "owner_phone" not in status["matches"][0]["property"]   # contact hidden until selection

    token = status["chat_token"]
    chat = client.get(f"/api/chat/{token}").json()
    assert chat["messages"][0]["role"] == "assistant"

    r = client.post(f"/api/chat/{token}/messages", json={"content": "which is cheapest?"})
    assert "₹" in r.json()["messages"][-1]["content"]

    pid = status["matches"][0]["property"]["id"]
    r = client.post(f"/api/chat/{token}/select", json={"property_id": pid})
    assert r.json()["selected"]["owner_phone"].startswith("+91")

    assert client.post(f"/api/chat/{token}/select", json={"property_id": 999999}).status_code == 400


def test_consent_required():
    r = client.post("/api/requests", json={"name": "A B", "phone": "9876543210", "consent": False})
    assert r.status_code == 422


def test_admin_requires_token():
    assert client.get("/api/admin/properties").status_code == 401
    assert client.get("/api/admin/properties", headers={"x-admin-token": "test-admin"}).status_code == 200
