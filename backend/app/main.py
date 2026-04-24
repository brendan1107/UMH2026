"""
F&B Genie - FastAPI Application Entry Point

Main application factory and server configuration.
Registers all route modules and middleware.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, cases, chat, tasks, uploads, reports, calendar
from app.config import settings


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="F&B Genie API",
        description="AI-powered business investigation partner for small F&B owners",
        version="1.0.0",
    )

    # CORS middleware for Next.js frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register route modules
    app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
    app.include_router(cases.router, prefix="/api/cases", tags=["Business Cases"])
    app.include_router(chat.router, prefix="/api/chat", tags=["Chat Sessions"])
    app.include_router(tasks.router, prefix="/api/tasks", tags=["Investigation Tasks"])
    app.include_router(uploads.router, prefix="/api/uploads", tags=["Evidence Uploads"])
    app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])
    app.include_router(calendar.router, prefix="/api/calendar", tags=["Google Calendar"])

    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "service": "fb-genie-api"}

    return app


app = create_app()
