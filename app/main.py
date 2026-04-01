import logging
from fastapi import FastAPI
from app.routes.health import router as health_router
from app.routes.vapi_webhook import router as vapi_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = FastAPI(
    title="Observe Insurance Voice Agent",
    description="VAPI webhook server for AI Claims Support Assistant",
    version="1.0.0",
)

app.include_router(health_router)
app.include_router(vapi_router)


@app.get("/")
async def root():
    return {
        "service": "Observe Insurance Voice Agent",
        "docs": "/docs",
        "health": "/health",
    }
