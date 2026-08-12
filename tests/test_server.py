"""Tests for the FastAPI server endpoints."""

import pytest
from fastapi.testclient import TestClient

from server.main import app, _load_plugins
from config.settings import AppSettings


@pytest.fixture(autouse=True)
def setup_registry():
    """Initialize the plugin registry for all server tests."""
    import server.main as srv
    settings = AppSettings()
    srv._registry = _load_plugins(settings)
    yield
    srv._registry = None


@pytest.fixture
def client():
    return TestClient(app)


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["plugin"] == "stm32_hal"


def test_list_plugins(client):
    response = client.get("/api/plugins/")
    assert response.status_code == 200
    data = response.json()
    assert data["active"] == "stm32_hal"
    assert len(data["plugins"]) >= 1


def test_list_boards(client):
    response = client.get("/api/plugins/boards")
    assert response.status_code == 200
    boards = response.json()
    assert len(boards) >= 1
    assert boards[0]["name"] == "NUCLEO-F446RE"
    assert boards[0]["mcu"] == "STM32F446RET6"


def test_list_peripherals(client):
    response = client.get("/api/plugins/peripherals")
    assert response.status_code == 200
    peripherals = response.json()
    assert "PWM" in peripherals
    assert "GPIO" in peripherals


def test_list_drivers(client):
    response = client.get("/api/plugins/drivers/PWM")
    assert response.status_code == 200
    drivers = response.json()
    assert len(drivers) >= 2
    names = [d["name"] for d in drivers]
    assert "HAL_TIM_PWM" in names


def test_start_workflow(client):
    response = client.post("/api/workflow/start", json={
        "user_input": "Blink LED on PA5 at 1Hz",
        "board_name": "NUCLEO-F446RE",
    })
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert data["stage"] in ("clarifier", "hardware")


def test_get_state(client):
    # Start a session first
    start = client.post("/api/workflow/start", json={
        "user_input": "PWM at 10kHz",
        "board_name": "NUCLEO-F446RE",
    })
    session_id = start.json()["session_id"]

    # Get state
    response = client.get(f"/api/workflow/{session_id}/state")
    assert response.status_code == 200
    state = response.json()
    assert state["session_id"] == session_id
    assert state["user_input"] == "PWM at 10kHz"
    assert state["board_name"] == "NUCLEO-F446RE"


def test_session_not_found(client):
    response = client.get("/api/workflow/nonexistent/state")
    assert response.status_code == 404
