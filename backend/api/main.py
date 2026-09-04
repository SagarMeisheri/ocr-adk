"""TrulyTally AI - FastAPI Application Server."""

from __future__ import annotations
import os
from pathlib import Path

# Load environment variables from .env if present
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .routes import invoices, tally, websocket, banking, hitl, documents
from .storage import init_db

app = FastAPI(
    title="TrulyTally AI - Intelligent Document Processing & Sync API",
    version="2.0.0",
    description="Universal AI Document Processing for Invoices, Bank Statements, Receipts, and Bills powered by Google ADK 2.0 & Gemini 3.8 Flash.",
)

# CORS configuration for Vite frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount uploaded files directory for side-by-side document preview
uploads_dir = Path("uploads")
uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")

# Include Routers
app.include_router(documents.router)
app.include_router(invoices.router)
app.include_router(banking.router)
app.include_router(hitl.router)
app.include_router(tally.router)
app.include_router(websocket.router)


@app.get("/api/tally-status")
def tally_status_alias():
    """Compatibility alias for tally status to prevent 404 logs."""
    from .storage import TallyConnectorStore

    return TallyConnectorStore.get_latest_connector_status()


@app.on_event("startup")
def startup_event():
    init_db()


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "TrulyTally AI OCR Engine",
        "adk_version": "2.0",
        "gemini_model": os.environ.get(
            "GEMINI_MODEL", "gemini-2.5-flash / gemini-3.8-flash"
        ),
    }
