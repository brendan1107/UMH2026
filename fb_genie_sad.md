SYSTEM ANALYSIS DOCUMENTATION (SAD)
UMHackathon 2026
F&B Genie
Version 1.0
# 1. Introduction
F&B Genie is an agentic AI business investigation system that helps small F&B business owners decide whether to open, improve, pivot, or stop a business by combining iterative questioning, real-world validation tasks, uploaded evidence, and external location intelligence.
This document defines the technical architecture, data flow, AI service design, integrations, MVP scope, and implementation decisions behind F&B Genie.
# 2. Background
Many small F&B business owners make decisions too quickly based on instinct, trends, or incomplete assumptions. They may fail to investigate competitors, local demand, parking, surrounding landmarks, or financial viability deeply enough before opening.
F&B Genie addresses this by acting as an investigative AI partner. It asks follow-up questions, identifies evidence gaps, requests real-world validation, and updates recommendations as new data is collected.
# 3. Target Stakeholders

# 4. System Architecture & Design
## 4.1 High Level Architecture

F&B Genie adopts a modular client-server architecture consisting of a web-based frontend, a FastAPI backend orchestration layer, a PostgreSQL persistence layer, a GLM-powered AI reasoning service layer, and external integrations including Google Places, Google Maps, and Google Calendar.
## 4.2 Main Components

# 5. LLM as Service Layer
GLM is treated as a service layer rather than a generic AI module. It is responsible for reasoning, not only text generation.
## Main AI responsibilities:
- ask follow-up questions
- identify missing evidence
- challenge weak assumptions
- generate investigation tasks
- analyze location suitability and business viability
- draft a realistic business report
- produce a final or provisional recommendation
## Model flow:

Context window includes latest user input, structured business facts, conversation summary, Google Places / Maps results, uploaded evidence summaries, generated tasks and status, and prior recommendation state.
Because GLM has a shorter context window, the backend summarizes older turns, stores structured memory, and truncates low-priority raw history.
# 6. User Interaction Flow
## Main demo flow:
- User logs in and creates a new business case.
- User enters a business idea, such as opening a western food restaurant near Li Villas.
- Frontend sends input to backend; backend stores the session.
- Backend calls Google Places and Maps for nearby context.
- AI asks follow-up questions and updates the report iteratively.
- AI generates investigation tasks when evidence is weak or missing.
- User can add selected tasks to Google Calendar.
- User uploads photos or evidence; backend processes them through AI.
- AI re-analyzes the case and returns a report plus recommendation.
- User ends the session and downloads the report as PDF.
# 7. Dependency Diagram Description
- Frontend -> FastAPI Backend -> AI Orchestration Module -> GLM API
- Backend -> Google Places / Maps API
- Backend -> Google Calendar flow
- Backend -> PostgreSQL / Supabase Storage
The backend builds the prompt from latest input, stored facts, summary, external results, and relevant uploads. Token limits are handled by summarization, structured memory, and filtering to decision-relevant fields only.
# 8. Sequence Diagram Description

# 9. Technological Stack

# 10. Key Data Flows
- user input flow
- AI reasoning flow
- location intelligence flow
- task generation flow
- evidence upload flow
- report generation flow
High-level flow: user submits idea, backend stores case and queries external APIs, AI orchestration prepares structured context, GLM produces questions and recommendation state, backend stores results, user responds and uploads evidence, backend reprocesses evidence and updates report.
# 11. Normalized Database Schema

## Relationship logic:
- one user can have many business cases
- one business case can have many chat sessions
- one business case can have many extracted facts
- one business case can have many recommendations over time
- one recommendation cycle can have many investigation tasks
- one business case can have many evidence uploads
Suggested task statuses: pending, scheduled, completed, skipped.
Final verdict values: proceed, reconsider, do_not_open, improve, pivot, shut_down.
# 12. Functional Requirements & Scope

Demo-critical features: iterative AI questioning, location competitor analysis, task generation, evidence upload, re-analysis, report output, and PDF download.
Existing business recovery mode can be treated as a partial MVP or future enhancement if time becomes constrained.
# 13. Non-Functional Requirements (NFRs)

## Failure handling:
- If GLM fails: retry once, then show graceful fallback message.
- If Maps fails: continue with manual user input or cached/mock place data.
- If Calendar fails: allow manual copy of task details.
# 14. Out of Scope / Future Enhancements
## Out of scope for hackathon MVP:
- full accounting integration
- advanced business dashboard analytics
- deep file parsing pipeline
- multi-user collaboration
- franchise multi-branch analysis
- licensed demographic datasets
- direct social media publishing
## Future enhancements:
- full ongoing business recovery mode
- automated monitoring of business trends
- direct social media publishing suggestions to channels
- deeper image and document understanding
- richer demographic and transport data integration
# 15. Monitoring, Evaluation, Assumptions & Dependencies
## Main health signals:
- GLM response success rate
- Maps / Places API success rate
- average backend latency
- task creation success rate
- upload processing success rate
## Priority matrix:

## Assumptions:
- users have stable internet access
- users provide truthful business information
- users are willing to complete field tasks
- Google location data is sufficient for rough competitor discovery
- uploaded photos or files are relevant to the case
## External dependencies:

Biggest dependency risk: GLM availability and response quality.
# 16. Project Management & Team Contributions


Main demo goal: show that the AI can iteratively ask useful questions, refine a report, and generate a realistic, actionable business plan by considering many factors rather than blindly agreeing with the user.
# 17. Recommendations
- Keep the architecture as a modular monolith for speed and clarity.
- Cache competitor lookup results to reduce repeated external API usage.
- Use structured JSON outputs from the model for easier backend parsing.
- Build graceful fallback paths for AI and external API failures.
- Prioritize one strong end-to-end demo flow rather than too many unfinished features.
- Keep the final report export simple and reliable.
# 18. Suggested Diagrams to Include
- High-Level Architecture Diagram
- Dependency Diagram showing GLM, Maps, Calendar, database, and frontend/backend interaction
- Sequence Diagram for new restaurant evaluation flow
- Data Flow Diagram (DFD)
- ERD / Normalized Database Schema Diagram
# 19. Closing Statement
F&B Genie is designed as a practical, agentic AI system for early-stage F&B business investigation. Its architecture is intentionally simple enough for a student hackathon team to implement, while still demonstrating meaningful AI orchestration, external integration, structured persistence, and iterative recommendation behavior.

| Stakeholder | Role | Expectations |
| --- | --- | --- |
| Small F&B Business Owner | Main user | Clear, realistic, actionable business guidance |
| Existing F&B Owner | Secondary user | Diagnosis, improvement, or recovery suggestions |
| Development Team | Builds and integrates system | Clear modular structure and workable scope |
| Judges / Evaluators | Assess product | Believable architecture and practical usefulness |


| Type | Details |
| --- | --- |
| System | Responsive web-based application |
| Architecture | Modular client-server architecture with modular monolith backend |
| Frontend | Next.js |
| Backend | FastAPI |
| Database | PostgreSQL |
| Deployment | Vercel for frontend, Render or Railway for backend, Supabase Postgres for database |


| Component | Responsibility |
| --- | --- |
| Next.js Frontend | Login, session creation, chat UI, upload UI, task display, report display, PDF download |
| FastAPI Backend | Receives requests, manages sessions, calls GLM and Google APIs, stores results |
| AI Orchestration Module | Builds prompts, manages context, parses structured outputs, triggers re-analysis |
| PostgreSQL Database | Stores users, cases, sessions, facts, tasks, uploads, recommendations |
| Google Places / Maps | Provides nearby competitors, review count, place context, landmarks |
| Google Calendar | Allows user to save AI-generated investigation tasks |
| Supabase Storage | Stores uploaded images and files |


| Stage | Role |
| --- | --- |
| Model 1 | Main reasoning engine that asks questions, analyzes evidence, and produces recommendation |
| Model 2 or Review Prompt | Sanity-check layer that reviews whether the output is realistic, grounded, and consistent |


| Step | Actor | Action |
| --- | --- | --- |
| 1 | User | Logs in and creates a new session |
| 2 | Frontend | Sends initial business idea to backend |
| 3 | Backend | Creates case and chat session record |
| 4 | Backend | Calls Google Geocoding / Places / Maps |
| 5 | Backend | Builds AI context and sends prompt to GLM |
| 6 | GLM | Returns questions, extracted facts, and missing evidence |
| 7 | Frontend | Displays questions and partial report |
| 8 | User | Answers follow-up questions |
| 9 | Backend | Updates structured facts and history |
| 10 | GLM | Generates tasks and updated report |
| 11 | User | Adds tasks to calendar and uploads evidence |
| 12 | Backend | Processes evidence and summarizes it |
| 13 | GLM | Re-analyzes and returns recommendation |
| 14 | Frontend | Shows report, recommendation, and PDF export option |


| Layer | Technology | Justification |
| --- | --- | --- |
| Frontend | Next.js | Fast to build, good for interactive UI, easy deployment |
| Backend | FastAPI | Clean Python API framework, suitable for AI orchestration and API integration |
| Database | PostgreSQL | Strong relational model for sessions, tasks, uploads, and recommendations |
| DB Hosting | Supabase Postgres | Managed PostgreSQL with low operational overhead |
| Storage | Supabase Storage | Suitable for uploaded images and reports |
| AI Model | Z AI GLM | Reasoning-heavy, cost-conscious, hackathon-aligned |
| Frontend Hosting | Vercel | Easy and suitable for Next.js |
| Backend Hosting | Render / Railway | Simpler Python deployment than heavy cloud infrastructure |


| Table | Purpose |
| --- | --- |
| users | Stores login and identity information |
| business_cases | Stores each business idea or investigation case |
| chat_sessions | Stores session-level metadata |
| chat_messages | Stores user and AI messages |
| extracted_facts | Stores structured facts extracted by AI |
| recommendations | Stores report state and final recommendation |
| investigation_tasks | Stores generated tasks and status |
| evidence_uploads | Stores uploaded file metadata and analysis status |
| api_place_results | Stores cached nearby place results |
| report_exports | Stores generated PDF metadata |


| # | Feature | Description |
| --- | --- | --- |
| 1 | AI Iterative Questioning | AI asks follow-up questions to gather context and refine the report |
| 2 | Google Places Competitor Lookup | Retrieves nearby competitor and area context data |
| 3 | Investigation Task Generation | AI generates tasks when evidence is weak or missing |
| 4 | Calendar Action Support | Users can redirect generated tasks into Google Calendar |
| 5 | Report Generation and Re-analysis | AI updates the report iteratively and supports final export to PDF |


| Quality | Requirement | Implementation |
| --- | --- | --- |
| Maintainability | Codebase should remain understandable for a small student team | Use modular monolith structure with clear folder separation |
| Reliability | Core workflow should still work if one non-core integration fails | Graceful fallback for Maps and Calendar failures |
| Token Latency | Response quality is prioritized, though most responses should remain reasonably fast | Summarized context, structured prompts, limited injected data |
| Cost Efficiency | Token and API cost should be manageable | Summarization, cached place results, fixed prompt structure |
| Security | API keys and uploads should not be exposed publicly | Store keys on backend only, restrict storage access |
| Data Integrity | Sessions, tasks, uploads, and recommendation states must remain linked correctly | Use relational schema and foreign key relationships |


| Priority | Condition | Action |
| --- | --- | --- |
| P1 | Core AI unavailable | Switch to fallback demo flow and reduce model dependency |
| P2 | Maps / Places unavailable | Use cached or predefined mock location data |
| P3 | Calendar integration unavailable | Provide manual task export or copy details |
| P4 | Upload feature unavailable | Continue with text-only workflow |


| Tool | Purpose | Risk |
| --- | --- | --- |
| Z AI GLM API | Core reasoning engine for questioning, tasks, and report generation | High |
| Google Places API | Competitor and area context lookup | Medium |
| Google Maps / Geocoding API | Location normalization and display support | Medium |
| Google Calendar API | Task scheduling / redirection | Medium |
| Supabase Postgres | Managed relational database | Low |
| Supabase Storage | File upload storage | Low |
| Vercel | Frontend hosting | Low |
| Render / Railway | Backend hosting | Medium |


| Day Range | Main Activities |
| --- | --- |
| Day 1-4 | Idea exploration, product thinking, feature definition |
| Day 5 | Documentation, architecture design, and test case planning |
| Day 6-9 | Development and integration |
| Day 10 | Demo recording and final polishing |


| Member | Role | Main Responsibility |
| --- | --- | --- |
| Brendan Lee Cheng Jun | Project Manager / Software Tester / Pitch Lead | product direction, planning, documentation, testing, presentation |
| Tan Liang Yao | Backend Developer / Database Engineer | backend APIs, DB schema, integrations |
| Louis | Frontend Developer | chat UI, session UI, upload UI, report UI |
| Wong Fang Yee | AI Architecture Designer / Developer | prompt design, structured outputs, AI behavior |
| Wei Yi | AI Architecture Designer / Developer | AI logic, review prompt, evidence processing support |
