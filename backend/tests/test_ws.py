import json
import pytest
from fastapi.testclient import TestClient

from app.main import app


def test_websocket_accepts_connection():
    with TestClient(app) as client:
        with client.websocket_connect("/ws/transcribe") as ws:
            ws.send_text(json.dumps({"type": "stop_session"}))
            data = ws.receive_text()
            msg = json.loads(data)
            assert msg["type"] == "session_stopped"


def test_health_endpoint():
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
