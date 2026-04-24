"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, calendar, cases, chat, reports, tasks, uploads
from app.config import settings
from app.db.database import bucket, db, firebase_initialization_error


def create_app() -> FastAPI:
    app = FastAPI(
        title="F&B Genie API",
        description="Backend MVP for cases, tasks, and uploads",
        version="1.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
    app.include_router(cases.router, prefix="/api/cases", tags=["Cases"])
    app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
    app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])
    app.include_router(tasks.router, prefix="/api/tasks", tags=["Tasks"])
    app.include_router(uploads.router, prefix="/api/uploads", tags=["Uploads"])
    app.include_router(calendar.router, prefix="/api/calendar", tags=["Calendar"])

    @app.get("/health")
    async def health_check():
        return {
            "data": {
                "status": "healthy",
                "service": "fb-genie-api",
                "firestore": "available" if db is not None else "fallback",
                "storage": "available" if bucket is not None else "fallback",
                "firebaseError": (
                    str(firebase_initialization_error)
                    if firebase_initialization_error is not None
                    else None
                ),
            }
        }

    return app


app = create_app()
