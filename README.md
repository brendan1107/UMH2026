# UMH2026
# F&B Genie 🍜

An AI-powered business feasibility investigator for Malaysian F&B MSMEs. F&B Genie acts as a cynical, data-driven auditor that helps small food & beverage business owners decide whether to **GO**, **PIVOT**, or **STOP** before committing their capital.

---

## What It Does

F&B Genie runs a multi-turn investigation loop that:

1. Asks the user about their F&B idea, location, and budget
2. Scans competitor data using Google Places API
3. Assigns field tasks to collect real-world evidence (footfall counts, photos, ratings)
4. Calculates break-even covers per day
5. Issues a final verdict with confidence score and risk analysis
6. Generates a downloadable PDF feasibility report

---

## Tech Stack

### Frontend
- Next.js 16 with TypeScript
- Google Maps / React Google Maps API
- Firebase Auth

### Backend
- FastAPI (Python)
- Firebase Firestore (database)
- Firebase Storage (file uploads)
- Google Places API (competitor scanning)
- Google Gemini (AI reasoning engine)
- ReportLab (PDF generation)

---

## AI Agent Pipeline

The AI layer lives in `backend/app/ai/` and runs a ReAct loop powered by Google Gemini:
User message
↓
orchestrator.py — run_agent_turn()
↓
prompts_templates.py — build_agent_prompt()
↓
glm_client.py — Gemini API call
↓
One of four output types:
• tool_call   → fetch_competitors / estimate_footfall / calculate_breakeven
• field_task  → assign real-world evidence collection to user
• clarify     → ask user a targeted question
• verdict     → GO / PIVOT / STOP with confidence score
↓
review_layer.py — adversarial audit (3 critical risks)
↓
report.py — PDF generation

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/cases/` | Create a new business case |
| GET | `/api/cases/{case_id}` | Get case details |
| POST | `/api/chat/{case_id}/sessions` | Start a chat session |
| POST | `/api/chat/{case_id}/sessions/{session_id}/messages` | Send a message |
| GET | `/api/tasks/{case_id}/tasks` | Get investigation tasks |
| POST | `/api/uploads/{case_id}` | Upload evidence file |
| GET | `/api/reports/{case_id}/report` | Get feasibility report |

---

## Frontend website:
https://fbgenie.vercel.app/login

## Backend website:
https://umh2026-production.up.railway.app/docs#/Authentication/sync_session_api_auth_session_post
