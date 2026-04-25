"""
F&B Genie - FastAPI Application Entry Point

Main application factory and server configuration.
Registers all route modules and middleware.
"""
# What is main.py for?
# The main.py file serves as the entry point for our FastAPI application. It defines a create_app() function that initializes the FastAPI instance, configures middleware (like CORS), and registers all the API route modules (auth, cases, chat, tasks, uploads, reports, calendar). This file is responsible for setting up the overall structure of our API and ensuring that all the necessary components are included when the server starts. By centralizing this configuration in main.py, we can keep our code organized and make it easier to manage our application's setup as it grows in complexity.

# Import necessary modules and settings
# This is where we bring in the tools and configurations we need 
# to build our API.
# - We import FastAPI and CORS middleware from the fastapi package.
# FastAPI: A modern, fast web framework for building APIs with Python.
# CORS Middleware: A tool to handle Cross-Origin Resource Sharing,
# allowing our frontend (Next.js) to communicate with our backend (FastAPI).
# - We import our route modules (auth, cases, chat, tasks, uploads, reports, calendar).
# These modules contain the specific API endpoints for each feature of our application.
# Example: auth.py handles user authentication, cases.py manages business cases, etc.
# Example: chat.py contains endpoints for managing chat sessions between users and the AI.
# Example: tasks.py defines endpoints for creating and managing investigation tasks.
# Example: uploads.py handles file uploads for evidence, reports.py generates reports,
# and calendar.py integrates with Google Calendar.
# - We import our settings from the config module, which loads environment variables
# and provides typed configuration for our application.
# and provide typed settings for our application, including Firebase configuration,
# AI model settings, Google API keys, authentication settings, and CORS allowed origins.


from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

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

    # ── Add Authorize button to Swagger UI ──
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )
        schema["components"]["securitySchemes"] = {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
            }
        }
        for path in schema["paths"].values():
            for method in path.values():
                method["security"] = [{"BearerAuth": []}]
        app.openapi_schema = schema
        return schema

    app.openapi = custom_openapi

    return app


app = create_app()