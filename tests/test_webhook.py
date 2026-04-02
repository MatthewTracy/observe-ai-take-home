"""Tests for the VAPI webhook handler."""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.models.schemas import CallerRecord

client = TestClient(app)


# --- Health Check ---


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "observe-insurance-voice-agent"}


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "Observe Insurance" in response.text


# --- Tool Calls: lookup_caller ---


@patch("app.routes.vapi_webhook.lookup_caller")
def test_lookup_caller_found(mock_lookup):
    """Happy path: caller found in Airtable."""
    mock_lookup.return_value = CallerRecord(
        first_name="Sarah",
        last_name="Johnson",
        phone="(555) 123-4567",
        claim_status="Approved",
        claim_id="CLM-2024-001",
        policy_number="POL-88210",
    )

    response = client.post("/vapi/webhook", json={
        "message": {
            "type": "tool-calls",
            "call": {"id": "test-call-1"},
            "toolCallList": [
                {
                    "id": "tc_001",
                    "type": "function",
                    "function": {
                        "name": "lookup_caller",
                        "arguments": {"phone_number": "5551234567"},
                    },
                }
            ],
        }
    })

    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 1
    assert data["results"][0]["toolCallId"] == "tc_001"
    assert "Sarah Johnson" in data["results"][0]["result"]
    assert "Approved" in data["results"][0]["result"]
    assert "CLM-2024-001" in data["results"][0]["result"]


@patch("app.routes.vapi_webhook.lookup_caller")
def test_lookup_caller_not_found(mock_lookup):
    """Error path: phone number not in Airtable."""
    mock_lookup.return_value = None

    response = client.post("/vapi/webhook", json={
        "message": {
            "type": "tool-calls",
            "call": {"id": "test-call-2"},
            "toolCallList": [
                {
                    "id": "tc_002",
                    "type": "function",
                    "function": {
                        "name": "lookup_caller",
                        "arguments": {"phone_number": "5559990000"},
                    },
                }
            ],
        }
    })

    assert response.status_code == 200
    data = response.json()
    assert "No account found" in data["results"][0]["result"]


@patch("app.routes.vapi_webhook.lookup_caller")
def test_lookup_caller_no_phone(mock_lookup):
    """Error path: no phone number provided."""
    response = client.post("/vapi/webhook", json={
        "message": {
            "type": "tool-calls",
            "call": {"id": "test-call-3"},
            "toolCallList": [
                {
                    "id": "tc_003",
                    "type": "function",
                    "function": {
                        "name": "lookup_caller",
                        "arguments": {"phone_number": ""},
                    },
                }
            ],
        }
    })

    assert response.status_code == 200
    assert "No phone number provided" in response.json()["results"][0]["result"]
    mock_lookup.assert_not_called()


# --- Tool Calls: log_interaction ---


@patch("app.routes.vapi_webhook.log_interaction")
def test_log_interaction(mock_log):
    """Happy path: log interaction at end of call."""
    mock_log.return_value = "rec_test_123"

    response = client.post("/vapi/webhook", json={
        "message": {
            "type": "tool-calls",
            "call": {"id": "test-call-4"},
            "toolCallList": [
                {
                    "id": "tc_004",
                    "type": "function",
                    "function": {
                        "name": "log_interaction",
                        "arguments": {
                            "caller_name": "Sarah Johnson",
                            "summary": "Caller checked claim status, claim approved.",
                            "sentiment": "positive",
                        },
                    },
                }
            ],
        }
    })

    assert response.status_code == 200
    assert "logged successfully" in response.json()["results"][0]["result"]
    mock_log.assert_called_once()


@patch("app.routes.vapi_webhook.log_interaction")
def test_log_interaction_invalid_sentiment(mock_log):
    """Edge case: invalid sentiment defaults to neutral."""
    mock_log.return_value = "rec_test_456"

    response = client.post("/vapi/webhook", json={
        "message": {
            "type": "tool-calls",
            "call": {"id": "test-call-5"},
            "toolCallList": [
                {
                    "id": "tc_005",
                    "type": "function",
                    "function": {
                        "name": "log_interaction",
                        "arguments": {
                            "caller_name": "Unknown Caller",
                            "summary": "Call ended early.",
                            "sentiment": "angry",
                        },
                    },
                }
            ],
        }
    })

    assert response.status_code == 200
    assert "logged successfully" in response.json()["results"][0]["result"]


# --- Other Message Types ---


def test_status_update():
    """Status update messages return ok."""
    response = client.post("/vapi/webhook", json={
        "message": {
            "type": "status-update",
            "status": "in-progress",
            "call": {"id": "test-call-6"},
        }
    })

    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_unknown_message_type():
    """Unknown message types return ok (don't crash)."""
    response = client.post("/vapi/webhook", json={
        "message": {
            "type": "speech-update",
            "call": {"id": "test-call-7"},
        }
    })

    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_unknown_function():
    """Unknown function name returns error message."""
    response = client.post("/vapi/webhook", json={
        "message": {
            "type": "tool-calls",
            "call": {"id": "test-call-8"},
            "toolCallList": [
                {
                    "id": "tc_008",
                    "type": "function",
                    "function": {
                        "name": "nonexistent_function",
                        "arguments": {},
                    },
                }
            ],
        }
    })

    assert response.status_code == 200
    assert "Unknown function" in response.json()["results"][0]["result"]


# --- End of Call Fallback ---


@patch("app.routes.vapi_webhook.log_interaction")
@patch("app.routes.vapi_webhook.lookup_caller")
def test_end_of_call_fallback_logging(mock_lookup, mock_log):
    """If assistant doesn't call log_interaction, end-of-call-report logs it."""
    mock_lookup.return_value = CallerRecord(
        first_name="Michael",
        last_name="Chen",
        phone="(555) 234-5678",
        claim_status="Pending",
        claim_id="CLM-2024-002",
        policy_number="POL-77432",
    )
    mock_log.return_value = "rec_fallback"

    # First: trigger a lookup to populate call state
    client.post("/vapi/webhook", json={
        "message": {
            "type": "tool-calls",
            "call": {"id": "test-call-9"},
            "toolCallList": [
                {
                    "id": "tc_009",
                    "type": "function",
                    "function": {
                        "name": "lookup_caller",
                        "arguments": {"phone_number": "5552345678"},
                    },
                }
            ],
        }
    })

    # Then: end-of-call without log_interaction being called
    response = client.post("/vapi/webhook", json={
        "message": {
            "type": "end-of-call-report",
            "call": {"id": "test-call-9"},
            "summary": "Caller asked about pending claim.",
            "endedReason": "customer-ended-call",
        }
    })

    assert response.status_code == 200
    mock_log.assert_called_once()
