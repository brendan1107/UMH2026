# F&B Genie Backend

AI-powered business investigation partner for small F&B owners in Malaysia.

## Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your actual API keys

# Add Firebase service account key
# Download from Firebase Console > Project Settings > Service Accounts
# Save as firebase-service-account.json in the backend/ directory

# Start development server
uvicorn app.main:app --reload --port 8000
```

## Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI entry point
│   ├── config.py             # Environment configuration
│   ├── dependencies.py       # Dependency injection (Firebase Auth)
│   ├── api/
│   │   ├── routes/           # API endpoint modules
│   │   │   ├── auth.py       # Authentication (Firebase Auth)
│   │   │   ├── cases.py      # Business case CRUD
│   │   │   ├── chat.py       # Chat sessions & AI interaction
│   │   │   ├── tasks.py      # Investigation tasks
│   │   │   ├── uploads.py    # Evidence uploads
│   │   │   ├── reports.py    # Report generation & PDF export
│   │   │   └── calendar.py   # Google Calendar integration
│   │   └── middleware/       # Auth middleware
│   ├── models/               # Firestore document schemas (dataclasses)
│   ├── schemas/              # Pydantic request/response DTOs
│   ├── services/             # Business logic layer
│   ├── ai/                   # AI Orchestration Module
│   │   ├── orchestrator.py   # Main AI pipeline
│   │   ├── context_builder.py # Prompt context assembly
│   │   ├── prompt_templates.py # System prompts
│   │   ├── response_parser.py # Structured output parser
│   │   ├── memory_manager.py # Conversation summarization
│   │   └── review_layer.py   # Sanity-check layer
│   ├── integrations/         # External API clients
│   │   ├── glm_client.py     # GLM AI model
│   │   ├── google_places.py  # Competitor lookup
│   │   ├── google_maps.py    # Geocoding
│   │   ├── google_calendar.py # Task scheduling
│   │   └── firebase_storage.py # File storage
│   ├── db/                   # Firebase initialization
│   └── utils/                # Helpers (PDF, file processing, validators)
├── tests/                    # Test suite
├── firebase-service-account.json  # Firebase credentials (DO NOT COMMIT)
├── .env.example              # Environment template
├── requirements.txt          # Python dependencies
└── README.md
```

## Firestore Collection Structure

```
users/{uid}
business_cases/{case_id}
  ├── /chat_sessions/{session_id}
  │     └── /messages/{msg_id}
  ├── /extracted_facts/{fact_id}
  ├── /recommendations/{rec_id}
  │     └── /tasks/{task_id}
  ├── /evidence_uploads/{upload_id}
  └── /place_results/{place_id}
report_exports/{export_id}
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | FastAPI |
| Database | Firebase Firestore |
| Storage | Firebase Storage |
| Auth | Firebase Auth |
| AI Model | Z AI GLM |
| Frontend Hosting | Vercel |
| Backend Hosting | Render / Railway |
