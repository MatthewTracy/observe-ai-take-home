"""Server-side gate that creates a Vapi webCall using the private API key.

This exists so the browser does not need to hold the public Vapi key. The
client posts here, we mint a call locked to our single assistantId, and
return the call payload. Inline assistant overrides from the client are
ignored — a stolen endpoint URL only ever produces the same locked call.
"""

import logging
import os
import time
from collections import deque

import httpx
from fastapi import APIRouter, HTTPException, Request

from app.config import VAPI_API_KEY

logger = logging.getLogger(__name__)
router = APIRouter()

ASSISTANT_ID = "8908370d-4aab-440f-a7f5-a9ae02a7c770"
VAPI_API_BASE = "https://api.vapi.ai"

ALLOWED_ORIGINS = {
    "https://voice-claims-agent.onrender.com",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
}

# Best-effort per-IP rate limit: max 5 webcall starts per 10 minutes
_RATE_LIMIT_MAX = 5
_RATE_LIMIT_WINDOW_SECONDS = 600
_recent_starts: dict[str, deque[float]] = {}


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _rate_limited(ip: str) -> bool:
    now = time.time()
    bucket = _recent_starts.setdefault(ip, deque(maxlen=_RATE_LIMIT_MAX))
    while bucket and now - bucket[0] > _RATE_LIMIT_WINDOW_SECONDS:
        bucket.popleft()
    if len(bucket) >= _RATE_LIMIT_MAX:
        return True
    bucket.append(now)
    return False


@router.post("/api/vapi/webcall")
async def create_webcall(request: Request) -> dict:
    if not VAPI_API_KEY:
        raise HTTPException(500, "VAPI_API_KEY not configured on the server")

    origin = request.headers.get("origin", "")
    if origin and origin not in ALLOWED_ORIGINS:
        logger.warning("Rejected /api/vapi/webcall from origin=%r", origin)
        raise HTTPException(403, "origin not allowed")

    ip = _client_ip(request)
    if _rate_limited(ip):
        logger.warning("Rate limited /api/vapi/webcall ip=%s", ip)
        raise HTTPException(429, "too many call starts, try again later")

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{VAPI_API_BASE}/call",
            headers={
                "Authorization": f"Bearer {VAPI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={"type": "webCall", "assistantId": ASSISTANT_ID},
        )

    if resp.status_code >= 400:
        logger.error("Vapi /call failed: %s %s", resp.status_code, resp.text)
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    return resp.json()
