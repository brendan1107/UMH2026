# Backend Technical Structure

This document describes the current backend file structure for F&B Genie. The backend is organized as a FastAPI application with Firebase Firestore, Firebase Storage, Firebase Auth, GLM AI integration, Google API integrations, and a service layer intended to hold business logic.

## Overview

The backend follows a layered structure:

```text
Client / Frontend
      |
      v
FastAPI app entry point
      |
      v
API routes
      |
      v
Services
      |
      v
Models, schemas, AI modules, integrations, database clients, utilities
```

The intended separation is:

| Layer | Purpose |
| --- | --- |
| `app/main.py` | Creates the FastAPI app, configures middleware, registers routers, exposes health check. |
| `app/api/routes/` | HTTP endpoint definitions grouped by feature area. |
| `app/services/` | Business logic layer for cases, chat, tasks, uploads, reports, and auth. |
| `app/schemas/` | Pydantic request and response DTOs used at API boundaries. |
| `app/models/` | Firestore document models represented as Python dataclasses. |
| `app/db/` | Firebase Admin initialization and Firestore/Storage client access. |
| `app/dependencies.py` | Shared FastAPI dependencies such as current-user extraction. |
| `app/ai/` | AI orchestration, context building, memory, parsing, prompts, and review layer. |
| `app/integrations/` | External service clients for GLM, Google APIs, and Firebase Storage. |
| `app/utils/` | Reusable helper functions for validation, file processing, and PDF generation. |
| `tests/` | Test suite scaffold. |

## Directory Tree

```text
backend/
├── .env.example
├── README.md
├── TECHNICAL_STRUCTURE.md
├── requirements.txt
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── dependencies.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── cases.py
│   │   │   ├── chat.py
│   │   │   ├── tasks.py
│   │   │   ├── uploads.py
│   │   │   ├── reports.py
│   │   │   └── calendar.py
│   │   └── middleware/
│   │       ├── __init__.py
│   │       └── auth.py
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── orchestrator.py
│   │   ├── context_builder.py
│   │   ├── prompt_templates.py
│   │   ├── response_parser.py
│   │   ├── memory_manager.py
│   │   └── review_layer.py
│   ├── db/
│   │   ├── __init__.py
│   │   ├── database.py
│   │   └── session.py
│   ├── integrations/
│   │   ├── __init__.py
│   │   ├── firebase_storage.py
│   │   ├── glm_client.py
│   │   ├── google_calendar.py
│   │   ├── google_maps.py
│   │   └── google_places.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── api_place_result.py
│   │   ├── business_case.py
│   │   ├── chat.py
│   │   ├── evidence_upload.py
│   │   ├── extracted_fact.py
│   │   ├── investigation_task.py
│   │   ├── recommendation.py
│   │   ├── report_export.py
│   │   └── user.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── business_case.py
│   │   ├── chat.py
│   │   ├── report.py
│   │   ├── task.py
│   │   ├── upload.py
│   │   └── user.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   ├── case_service.py
│   │   ├── chat_service.py
│   │   ├── report_service.py
│   │   ├── task_service.py
│   │   └── upload_service.py
│   └── utils/
│       ├── __init__.py
│       ├── file_processor.py
│       ├── pdf_generator.py
│       └── validators.py
└── tests/
    ├── __init__.py
    ├── test_auth.py
    ├── test_cases.py
    ├── test_chat.py
    └── test_integrations.py
```

Generated and local-only folders such as `.venv/` and `.pytest_cache/` are not part of the application architecture and should not be treated as source code.

## Application Entry Point

### `app/main.py`

`main.py` is the FastAPI composition root. It is responsible for:

- Creating the `FastAPI` application instance.
- Configuring CORS middleware using `settings.ALLOWED_ORIGINS`.
- Registering all API routers under `/api/...` prefixes.
- Exposing a lightweight `/health` endpoint.

Registered routers:

| Router module | Prefix | Domain |
| --- | --- | --- |
| `app.api.routes.auth` | `/api/auth` | Authentication |
| `app.api.routes.cases` | `/api/cases` | Business case CRUD |
| `app.api.routes.chat` | `/api/chat` | Chat sessions and messages |
| `app.api.routes.tasks` | `/api/tasks` | Investigation task operations |
| `app.api.routes.uploads` | `/api/uploads` | Evidence uploads |
| `app.api.routes.reports` | `/api/reports` | Report generation and PDF export |
| `app.api.routes.calendar` | `/api/calendar` | Google Calendar scheduling |

## Configuration

### `app/config.py`

Configuration is centralized in a Pydantic `BaseSettings` class. Values are loaded from environment variables and optionally from `.env`.

Main configuration groups:

| Group | Fields |
| --- | --- |
| Application | `APP_ENV`, `DEBUG` |
| Firebase | `FIREBASE_PROJECT_ID`, `FIREBASE_CREDENTIALS_PATH`, `FIREBASE_STORAGE_BUCKET` |
| GLM AI | `GLM_API_KEY`, `GLM_API_BASE_URL`, `GLM_MODEL_NAME`, `GLM_MAX_TOKENS` |
| Google APIs | `GOOGLE_PLACES_API_KEY`, `GOOGLE_MAPS_API_KEY`, `GOOGLE_CALENDAR_CLIENT_ID`, `GOOGLE_CALENDAR_CLIENT_SECRET` |
| Auth | `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES` |
| CORS | `ALLOWED_ORIGINS` |

### `.env.example`

`.env.example` documents the expected local environment variables. A local `.env` should be created from it:

```bash
cp .env.example .env
```

Sensitive files and secrets should not be committed.

## API Layer

The API layer is located in `app/api/routes/`. Each file owns one feature area and should stay thin. Route handlers should validate HTTP inputs, call service-layer methods, and return response schemas.

| File | Responsibility |
| --- | --- |
| `auth.py` | Register, login, logout, and Firebase Auth-related endpoints. |
| `cases.py` | Create, list, retrieve, update, and delete business investigation cases. |
| `chat.py` | Create chat sessions, list sessions, send messages, and retrieve message history. |
| `tasks.py` | List tasks, update status, complete tasks, and skip tasks. |
| `uploads.py` | Upload evidence files, list uploads, and delete uploads. |
| `reports.py` | Retrieve current report, generate report, export PDF. |
| `calendar.py` | Google OAuth callback and task/event scheduling endpoints. |

### Recommended Route Pattern

Routes should follow this pattern:

```python
@router.post("/", response_model=SomeResponse)
async def endpoint(
    payload: SomeRequest,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    service = SomeService(db)
    return await service.some_action(current_user["uid"], payload)
```

This keeps HTTP details in routes and business rules in services.

## Dependency Layer

### `app/dependencies.py`

This file provides FastAPI dependencies shared across route modules.

Current intended responsibility:

- Read `Authorization: Bearer <token>` from incoming requests.
- Verify the token using Firebase Admin SDK.
- Return the decoded Firebase user context.

Typical usage:

```python
current_user = Depends(get_current_user)
```

## Database Layer

### `app/db/database.py`

Initializes Firebase Admin SDK and exposes:

- Firestore client as `db`.
- Firebase Storage bucket as `bucket`.

Current behavior initializes Firebase at import time. That means importing route modules can fail if the Firebase service account file is missing.

### `app/db/session.py`

Provides dependency-friendly accessors:

| Function | Returns |
| --- | --- |
| `get_db()` | Firestore client |
| `get_storage_bucket()` | Firebase Storage bucket |

Even though the file is named `session.py`, this backend does not use SQL database sessions. It is currently used as a Firestore client provider.

## Data Model Layer

Models are located in `app/models/` and represent Firestore document shapes. They are Python dataclasses with `to_dict()` and `from_dict()` helpers where implemented.

| File | Firestore concept |
| --- | --- |
| `user.py` | User profile metadata linked to Firebase Auth UID. |
| `business_case.py` | Main business investigation case document. |
| `chat.py` | Chat session and chat message subcollection documents. |
| `extracted_fact.py` | Facts extracted from user input, uploads, or AI analysis. |
| `recommendation.py` | AI-generated business recommendation state. |
| `investigation_task.py` | Human-in-the-loop investigation tasks. |
| `evidence_upload.py` | Uploaded evidence metadata. |
| `api_place_result.py` | Cached Google Places or map result data. |
| `report_export.py` | Generated report/PDF export metadata. |

### Intended Firestore Collections

```text
users/{uid}

business_cases/{case_id}
├── chat_sessions/{session_id}
│   └── messages/{message_id}
├── extracted_facts/{fact_id}
├── recommendations/{recommendation_id}
│   └── tasks/{task_id}
├── evidence_uploads/{upload_id}
└── place_results/{place_id}

report_exports/{export_id}
```

## Schema Layer

Schemas are located in `app/schemas/` and define Pydantic request and response objects for the API layer.

| File | DTOs |
| --- | --- |
| `user.py` | `UserRegister`, `UserLogin`, `UserResponse`, `TokenResponse` |
| `business_case.py` | `CaseCreate`, `CaseResponse` |
| `chat.py` | `MessageCreate`, `MessageResponse`, `AIResponse` |
| `task.py` | `TaskResponse`, `TaskComplete`, `TaskSchedule` |
| `upload.py` | Upload-related request/response DTOs |
| `report.py` | Report and export DTOs |

Schemas should be used at the API boundary. Firestore dataclasses should be used internally for database serialization.

## Service Layer

Services are located in `app/services/`. This layer should contain application-specific business logic and coordinate between the database, AI modules, integrations, and utilities.

| File | Intended responsibility |
| --- | --- |
| `auth_service.py` | User registration/authentication helpers, token-related workflows if needed. |
| `case_service.py` | Create, read, update, delete, and aggregate business cases. |
| `chat_service.py` | Store messages, call AI pipeline, persist AI outputs, return conversation responses. |
| `task_service.py` | Manage investigation tasks and status transitions. |
| `upload_service.py` | Validate uploads, store files, create upload records, trigger analysis. |
| `report_service.py` | Compile facts, tasks, uploads, recommendations, and produce reports. |

Recommended dependency direction:

```text
routes -> services -> db/models/schemas/ai/integrations/utils
```

Services should not import route modules.

## AI Layer

The AI layer is located in `app/ai/` and is intended to coordinate the agentic investigation workflow.

| File | Responsibility |
| --- | --- |
| `orchestrator.py` | Main pipeline coordinator for user input, evidence re-analysis, and report generation. |
| `context_builder.py` | Builds prompt context from case data, facts, uploads, tasks, and external results. |
| `prompt_templates.py` | Stores system prompts and reusable prompt templates. |
| `response_parser.py` | Extracts structured JSON-like outputs from model responses. |
| `memory_manager.py` | Summarizes conversations and maintains long-term structured memory. |
| `review_layer.py` | Performs sanity checks and risk review on AI outputs. |

Intended chat flow:

```text
User message
  -> Chat route
  -> ChatService.process_message()
  -> AIOrchestrator.process_user_input()
  -> ContextBuilder
  -> GLMClient
  -> ResponseParser
  -> ReviewLayer
  -> MemoryManager / Firestore writes
  -> API response
```

## Integrations Layer

External service clients live in `app/integrations/`.

| File | External system |
| --- | --- |
| `glm_client.py` | Z AI GLM chat completion API. |
| `google_places.py` | Google Places lookup for competitors and nearby businesses. |
| `google_maps.py` | Geocoding, reverse geocoding, and directions. |
| `google_calendar.py` | OAuth and event scheduling for investigation tasks. |
| `firebase_storage.py` | Firebase Storage file upload, URL retrieval, deletion, and existence checks. |

Integration classes should hide API-specific details from services. Services should receive clean Python dictionaries or typed objects rather than raw HTTP responses where possible.

## Utility Layer

Utilities live in `app/utils/`.

| File | Responsibility |
| --- | --- |
| `validators.py` | Shared validation helpers. |
| `file_processor.py` | Extract metadata or text from uploaded files. |
| `pdf_generator.py` | Convert reports into downloadable PDF output. |

Utilities should stay stateless when possible and should not depend on FastAPI route objects.

## Test Structure

Tests live in `tests/`.

| File | Intended coverage |
| --- | --- |
| `test_auth.py` | Authentication route and service behavior. |
| `test_cases.py` | Case CRUD behavior. |
| `test_chat.py` | Chat endpoint and AI orchestration behavior. |
| `test_integrations.py` | Integration client behavior using mocks or test doubles. |

Recommended minimum test categories:

- App startup test: importing `app.main` should not require external credentials for `/health`.
- Route tests: use `fastapi.testclient.TestClient` or `httpx.AsyncClient`.
- Service tests: mock Firestore and external integrations.
- Parser tests: validate AI structured-output parsing.
- Config tests: verify `.env` parsing and default behavior.

## Runtime Dependencies

Declared dependencies are managed in `requirements.txt`.

Important packages:

| Package | Purpose |
| --- | --- |
| `fastapi` | Web framework. |
| `uvicorn[standard]` | Local ASGI server. |
| `pydantic` | Data validation and schemas. |
| `pydantic-settings` | Environment-based settings. |
| `firebase-admin` | Firebase Auth, Firestore, and Storage admin access. |
| `python-jose[cryptography]` | Optional JWT support if a custom token layer is added. |
| `python-multipart` | File upload support. |
| `httpx` | Async HTTP client for external APIs. |
| `reportlab` | PDF generation. |
| `pytest`, `pytest-asyncio` | Test framework. |
| `python-dotenv` | Local `.env` loading. |

## Current Implementation Status

The structure is technically sound as a scaffold, but several files are not fully implemented yet.

Known implementation gaps:

- Many route handlers currently contain `TODO` and `pass`.
- Several service methods currently contain `TODO` and `pass`.
- AI orchestration, response parsing, memory management, and review logic are scaffolded but not implemented.
- Some route modules still import `sqlalchemy.orm.Session`, even though the backend is Firestore-based.
- Firebase initializes at import time, so the app cannot start without credentials present.
- Current tests are placeholder tests and do not verify runtime behavior.

## Recommended Next Structural Fixes

1. Replace leftover SQLAlchemy types in route modules with Firestore-compatible types or untyped dependency injection.
2. Move Firebase initialization behind a lazy accessor so `/health` and app import can work without credentials.
3. Implement core service methods before adding more route logic.
4. Add real app startup and route tests.
5. Add `.gitignore` rules for `.venv/`, `.pytest_cache/`, `.env`, and `firebase-service-account.json`.
6. Define a consistent response/error contract for all routes.
7. Keep route modules thin and move business logic into `app/services/`.

## Ownership Guidelines

When adding new backend features:

- Add request/response DTOs in `app/schemas/`.
- Add or update Firestore document models in `app/models/`.
- Implement business logic in `app/services/`.
- Keep route handlers focused on HTTP concerns only.
- Use `app/dependencies.py` for shared request dependencies such as authentication.
- Use `app/integrations/` for external API clients.
- Add or update tests in `tests/`.

