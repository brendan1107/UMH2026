# AGENTS.md

## Working style

- Give the answer immediately.
- Be direct, practical, and concise.
- Do not give vague high-level advice when the user asks for a fix.
- If asked to fix code, inspect the relevant files and provide actual code changes.
- If asked to explain, explain the actual project code and behavior, not generic theory.
- Prefer concrete commands, file paths, code snippets, and exact next steps.
- Suggest better solutions when obvious, including options the user may not have considered.
- Be accurate and thorough, but avoid unnecessary filler.
- If speculation is needed, clearly label it as speculation.
- Do not moralize.
- Discuss safety/security only when it is relevant, crucial, or non-obvious.

## Code editing rules

- Respect existing code comments.
- Remove comments only if they are clearly obsolete after the change.
- Do not rewrite whole files unnecessarily.
- For small code changes, show only the relevant before/after snippets.
- Do not modify unrelated files.
- Do not touch frontend files when the task says backend only.
- Do not touch backend files when the task says frontend only.
- Do not commit secrets.
- Never commit:
  - backend/.env
  - backend/env.backend
  - backend/firebase-service-account.json
  - backend/.venv/
  - frontend/.env
  - frontend/.env.local
  - node_modules/
  - .next/

## Project structure

This is a monorepo:

- frontend/ = Next.js app, user interface, Firebase Client Auth, dashboard, case workspace, interactive tasks, recommendation UI.
- backend/ = FastAPI app, Firebase Admin, Firestore, Firebase Storage, AI/GLM integration, Google APIs.
- docs/ = project documentation and planning files.

## Frontend commands

Run from `frontend/`:

```bash
npm install
npm run dev
npm run build