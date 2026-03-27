import json

from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def _init_session(user_id: str = "user_001") -> dict:
    response = client.post("/api/v1/session/init", json={"user_id": user_id})
    assert response.status_code == 200
    return response.json()


def test_session_init_returns_token_and_profile():
    payload = _init_session()

    assert payload["session_id"].startswith("sess_")
    assert payload["websocket_token"]
    assert payload["user_profile"]["user_id"] == "user_001"


def test_session_refresh_invalidates_previous_token():
    init_payload = _init_session("user_002")
    old_token = init_payload["websocket_token"]

    refresh_response = client.post(
        "/api/v1/session/refresh",
        json={"user_id": "user_002", "previous_token": old_token},
    )
    assert refresh_response.status_code == 200
    refresh_payload = refresh_response.json()
    assert refresh_payload["websocket_token"] != old_token

    try:
        with client.websocket_connect(f"/ws/chat?token={old_token}"):
            assert False, "Old token should not be accepted after refresh."
    except Exception:
        pass


def test_websocket_rejects_invalid_json_payload():
    session_payload = _init_session("user_003")
    token = session_payload["websocket_token"]

    with client.websocket_connect(f"/ws/chat?token={token}") as websocket:
        handshake = json.loads(websocket.receive_text())
        assert handshake["event"] == "connection_established"

        websocket.send_text("this-is-not-json")
        err = json.loads(websocket.receive_text())
        assert err["event"] == "error"
        assert "valid JSON" in err["data"]["message"]
