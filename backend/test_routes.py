"""Quick smoke test for all backend routes.

Run with: .venv\\Scripts\\python.exe test_routes.py
Requires DEV_AUTH_BYPASS=true in .env OR a valid Firebase token.
"""
import httpx
import sys
import json

BASE = "http://127.0.0.1:8003"
HEADERS = {}  # Add {"Authorization": "Bearer <token>"} for real auth

def p(label, r):
    print(f"\n{'='*60}")
    print(f"{label}: {r.status_code}")
    try:
        data = r.json()
        print(json.dumps(data, indent=2, default=str)[:500])
    except:
        print(r.text[:200])


def main():
    c = httpx.Client(base_url=BASE, headers=HEADERS, timeout=10)

    # Health
    p("GET /health", c.get("/health"))

    # Auth
    p("GET /api/auth/me", c.get("/api/auth/me"))

    # Create case
    r = c.post("/api/cases/", json={
        "title": "Test Cafe",
        "description": "A test cafe case",
        "stage": "new",
        "business_type": "cafe",
        "target_location": "Subang Jaya"
    })
    p("POST /api/cases/", r)
    if r.status_code != 200:
        print("Cannot proceed without creating a case.")
        sys.exit(1)

    case_id = r.json()["id"]
    print(f"\n>>> Created case: {case_id}")

    # List cases
    p("GET /api/cases/", c.get("/api/cases/"))

    # Get case
    p(f"GET /api/cases/{case_id}", c.get(f"/api/cases/{case_id}"))

    # Update case
    p(f"PUT /api/cases/{case_id}", c.put(f"/api/cases/{case_id}", json={"description": "Updated description"}))

    # Create task
    r = c.post(f"/api/tasks/{case_id}", json={
        "title": "Visit competitor cafe",
        "description": "Check menu and pricing",
        "type": "analyze_competitors",
        "status": "pending"
    })
    p(f"POST /api/tasks/{case_id}", r)
    task_id = r.json().get("id", "")
    print(f">>> Created task: {task_id}")

    # List tasks
    p(f"GET /api/tasks/{case_id}", c.get(f"/api/tasks/{case_id}"))

    # List tasks (compat)
    p(f"GET /api/tasks/{case_id}/tasks", c.get(f"/api/tasks/{case_id}/tasks"))

    # Update task
    if task_id:
        p(f"PUT /api/tasks/{case_id}/{task_id}", c.put(f"/api/tasks/{case_id}/{task_id}", json={"status": "completed"}))

    # Upload (simple text file)
    files = {"file": ("test.txt", b"Hello world", "text/plain")}
    r = c.post(f"/api/uploads/{case_id}/upload", files=files)
    p(f"POST /api/uploads/{case_id}/upload", r)
    upload_id = r.json().get("id", "")

    # List uploads
    p(f"GET /api/uploads/{case_id}/uploads", c.get(f"/api/uploads/{case_id}/uploads"))

    # Schedule task
    if task_id:
        r = c.post(f"/api/calendar/tasks/{task_id}/schedule", json={
            "caseId": case_id,
            "title": "Visit competitor",
            "date": "2026-05-01",
            "time": "10:00",
            "notes": "Bring camera"
        })
        p(f"POST /api/calendar/tasks/{task_id}/schedule", r)

    # Location competitors
    p("GET /api/locations/competitors", c.get(f"/api/locations/competitors?case_id={case_id}&target_location=Kuala+Lumpur"))

    # Report
    p(f"GET /api/reports/{case_id}/report", c.get(f"/api/reports/{case_id}/report"))

    # Generate report
    p(f"POST /api/reports/{case_id}/report/generate", c.post(f"/api/reports/{case_id}/report/generate"))

    # Verdict
    p(f"POST /api/reports/{case_id}/final-verdict", c.post(f"/api/reports/{case_id}/final-verdict"))

    # Cleanup — delete upload
    if upload_id:
        p(f"DELETE /api/uploads/{case_id}/uploads/{upload_id}", c.delete(f"/api/uploads/{case_id}/uploads/{upload_id}"))

    # Delete task
    if task_id:
        p(f"DELETE /api/tasks/{case_id}/{task_id}", c.delete(f"/api/tasks/{case_id}/{task_id}"))

    # Delete case
    p(f"DELETE /api/cases/{case_id}", c.delete(f"/api/cases/{case_id}"))

    print("\n\n✅ All route tests completed!")


if __name__ == "__main__":
    main()
