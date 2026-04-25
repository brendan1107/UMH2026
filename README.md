# F&B Genie 🍜
### AI-Powered Business Feasibility Investigator for Malaysian F&B MSMEs
 
> *"Don't burn your capital on a bad idea. Let the Genie investigate first."*
 
F&B Genie is a **Decision Intelligence Agent** built for UMHackathon 2026. It acts as a cynical, data-driven business auditor that helps small food & beverage owners decide whether to **GO**, **PIVOT**, or **STOP** — before they commit their life savings.
 
🌐 **Live App:** https://fbgenie.vercel.app/login
🔧 **API Docs:** https://umh2026-production.up.railway.app/docs
 
---
 
## The Problem
 
In Malaysia, thousands of F&B MSMEs launch every year based on gut feeling — wrong location, wrong price point, wrong format. Traditional business consulting costs RM5,000–20,000 and is out of reach for micro-entrepreneurs. The result: an extremely high first-year failure rate and lost capital that families cannot afford to lose.
 
---
 
## The Solution
 
F&B Genie democratises high-level business intelligence. Instead of passively answering questions, the Genie **takes control of the investigation**:
 
1. Pulls live competitor data from Google Places
2. Calculates break-even covers per day from real financials
3. Assigns physical field tasks when data cannot be fetched by API
4. Runs a two-pass AI analysis — one optimistic, one adversarial
5. Delivers a hard **GO / PIVOT / STOP** verdict with a confidence score
6. Generates a downloadable PDF feasibility report
---
 
## Team
 
| Name | Role |
|---|---|
| Wei Yi | AI Engineer |
| Louis | Frontend + Backend  |
| LiangYao | Backend |
| FangYee | AI Engineer |
| Brendan (Leader)| Backend |
 
---
 
## Tech Stack
 
### Frontend
- **Next.js** with TypeScript — responsive web application
- **React Google Maps API** — location selection and competitor visualisation
- **Firebase Auth** — user authentication
- **Tailwind CSS + shadcn/ui** — UI components
### Backend
- **FastAPI** (Python) — REST API with async support
- **Firebase Firestore** — case data, chat sessions, task state
- **Firebase Storage** — field evidence file uploads
- **Google Places API** — live competitor scanning within 1km radius
- **Google Geocoding API** — location string → lat/lng conversion
- **Google Calendar API** — schedule field investigation tasks
- **Gemini (gemini-2.5-flash)** — core AI reasoning engine
- **fpdf2** — PDF feasibility report generation
### Infrastructure
- **Vercel** — frontend deployment
- **Railway** — backend deployment
---
 
## AI Agent Architecture
 
The AI layer lives in `backend/app/ai/` and runs a **state-driven ReAct (Reason + Act) loop**.
 
```
User message
     │
     ▼
orchestrator.py — run_agent_turn()
     │
     ▼
context_builder.py — assemble fact sheet + conversation history
     │
     ▼
prompts_templates.py — build_agent_prompt() with current phase + known facts
     │
     ▼
glm_client.py — Z.AI Gemini API call with retry logic
     │
     ▼
response_parser.py — parse + validate JSON output
     │
     ├── tool_call   → tools.py (fetch_competitors / estimate_footfall / calculate_breakeven)
     │                     │
     │                     └── Google Places API → fact_sheet updated → loop continues
     │
     ├── field_task  → saved to Firestore → user completes real-world task → loop continues
     │
     ├── clarify     → question sent to user → answer appended → loop continues
     │
     └── verdict     → GO / PIVOT / STOP + confidence score
                           │
                           ▼
                  review_layer.py — adversarial audit (Pass 2)
                  3 critical failure risks with severity + mitigation
                           │
                           ▼
                  pdf_generator.py — downloadable PDF feasibility report
```
 
### Phase State Machine
 
The agent progresses through 5 phases. It cannot skip ahead or issue a verdict until all required facts are collected.
 
```
INTAKE → MARKET_SCAN → TASK_ASSIGNMENT → EVIDENCE → VERDICT
```
 
| Phase | What happens |
|---|---|
| INTAKE | Agent reads the business idea and starts the investigation |
| MARKET_SCAN | Calls Google Places to fetch competitor count, ratings, proximity |
| TASK_ASSIGNMENT | Emits field tasks for data that APIs cannot provide (footfall, rent) |
| EVIDENCE | Waits for user to complete and submit field tasks |
| VERDICT | All facts collected — agent issues GO / PIVOT / STOP |
 
### Required Facts Before Verdict
 
The agent **cannot issue a verdict** until all 5 facts are in the fact sheet:
 
| Fact | Source |
|---|---|
| `competitor_count` | Google Places API |
| `avg_competitor_rating` | Google Places API |
| `estimated_footfall_lunch` | Heuristic from Places data |
| `confirmed_rent_myr` | User field task |
| `break_even_covers` | `calculate_breakeven()` tool |
 
### Two-Pass AI Analysis
 
- **Pass 1 (Generator):** Agent investigates and builds a business plan
- **Pass 2 (Auditor):** Separate Gemini call with adversarial persona — finds exactly 3 critical failure risks, each citing a specific number from the fact sheet
---
 


## API Endpoints
 
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/auth/register` | Register new user |
| POST | `/api/auth/login` | Login and get JWT token |
| POST | `/api/cases/` | Create a new business case |
| GET | `/api/cases/` | List all cases for current user |
| GET | `/api/cases/{case_id}` | Get case details |
| PUT | `/api/cases/{case_id}` | Update case |
| POST | `/api/cases/{case_id}/end_session` | End investigation session |
| POST | `/api/chat/{case_id}/sessions` | Start a chat session |
| POST | `/api/chat/{case_id}/sessions/{session_id}/messages` | Send message → triggers AI agent |
| GET | `/api/chat/{case_id}/sessions/{session_id}/messages` | Get chat history |
| GET | `/api/tasks/{case_id}/tasks` | Get investigation tasks |
| POST | `/api/tasks/{task_id}/complete` | Submit field task evidence → re-triggers AI |
| POST | `/api/tasks/{task_id}/schedule` | Schedule task in Google Calendar |
| POST | `/api/uploads/{case_id}/upload` | Upload field evidence photo |
| GET | `/api/reports/{case_id}/report` | Get feasibility report data |
| POST | `/api/reports/{case_id}/verdict` | Generate AI verdict + audit |
| GET | `/api/reports/{case_id}/report/pdf` | Download PDF report |
 
---
 
## User Flow
 
```
1. Register / Login
        │
        ▼
2. Create a new business case
   (idea, location, budget, format)
        │
        ▼
3. Chat with F&B Genie
   — Genie scans competitors via Google Places
   — Genie calculates break-even
   — Genie asks clarifying questions
        │
        ▼
4. Complete field tasks assigned by Genie
   — Visit site at 1PM, count queue
   — Confirm monthly rent
   — Upload photo of shopfront
        │
        ▼
5. Genie issues verdict: GO / PIVOT / STOP
   — Confidence score
   — Executive summary
   — 3 critical risks with mitigations
   — Pivot suggestion if applicable
        │
        ▼
6. Download PDF feasibility report
   — Key numbers table
   — Risk analysis matrix
   — Data-driven, not hallucinated
```

 
## Running the Tests
 
```bash
cd backend
 
# Install dependencies
pip install -r requirements.txt
 
# Run all AI verification tests (takes ~3-5 minutes)
python app/ai/test/run_all_tests.py
```
 
### Test Stages
 
| Stage | What it verifies |
|---|---|
| Stage 0 | All environment variables present |
| Stage 1 | Gemini API key valid, server reachable |
| Stage 2 | Google Maps geocoding + Places API working |
| Stage 3 | Gemini returns correct JSON type for all 4 output scenarios |
| Stage 4 | Full agent loop with real APIs — all 5 phases complete |
| Stage 5 | Adversarial auditor returns 3 structured risk items |
 
---
 
## What Makes This Different From a Chatbot
 
| Feature | Standard Chatbot | F&B Genie |
|---|---|---|
| Data source | Training data only | Live Google Places API |
| Output | Free-form text | Strict typed JSON → validated by Pydantic |
| Decision | Suggests | GO / PIVOT / STOP with confidence score |
| Evidence | None | Human-in-the-loop field tasks |
| Report | Chat transcript | Structured PDF with real numbers |
| Critique | None | Adversarial Pass 2 auditor finds 3 failure risks |
| State | Stateless | Phase machine — cannot skip to verdict prematurely |
 
---
 
*Built for UMHackathon 2026 — Decision Intelligence track*
