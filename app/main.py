"""
FastAPI application entrypoint for CompareCrypt.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router as matching_router
from app.api.entity_resolution_routes import router as er_router
from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Secure Private Matching of Similar Data using established Cryptographic PSI & OPRF.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(matching_router)
app.include_router(er_router)


@app.get("/health", tags=["Health"])
async def health_check():
    """Service health and crypto parameters check."""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
        "crypto_group": settings.crypto.group_name,
    }
