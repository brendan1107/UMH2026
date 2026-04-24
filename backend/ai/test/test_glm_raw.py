# test_glm_raw.py
# Run with: python test_glm_raw.py
import httpx, os, json
from dotenv import load_dotenv

load_dotenv()

ZAI_KEY  = os.getenv("ZAI_API_KEY")
ZAI_BASE = "https://api.ilmu.ai/v1"
def test_glm_connection():
    print("── Test 1: Basic connectivity ──")

    payload = {
        "model": "ilmu-glm-5.1",
        "messages": [
            {"role": "user", "content": "Reply with exactly this JSON: {\"status\": \"alive\"}"}
        ],
        "temperature": 0.1,
        "max_tokens": 50,
    }

    resp = httpx.post(
        f"{ZAI_BASE}/chat/completions",
        headers={"Authorization": f"Bearer {ZAI_KEY}"},
        json=payload,
        timeout=15,
    )

    print(f"HTTP status : {resp.status_code}")

    if resp.status_code != 200:
        print(f"FAIL — error body: {resp.text}")
        return False

    data = resp.json()
    content = data["choices"][0]["message"]["content"]
    print(f"Raw reply   : {content}")

    # Try parsing as JSON
    try:
        parsed = json.loads(content.strip())
        print(f"Parsed JSON : {parsed}")
        print("PASS ✓ — GLM is reachable and responding\n")
        return True
    except json.JSONDecodeError:
        print("WARN — GLM responded but not pure JSON (may need prompt tuning)\n")
        return True   # connection works, prompt may need adjusting


def test_glm_model_info():
    print("── Test 2: Model list (check what models are available) ──")

    resp = httpx.get(
        f"{ZAI_BASE}/models",
        headers={"Authorization": f"Bearer {ZAI_KEY}"},
        timeout=10,
    )

    if resp.status_code == 200:
        models = [m["id"] for m in resp.json().get("data", [])]
        print(f"Available models: {models}")
        print("PASS ✓\n")
    else:
        print(f"Could not fetch models: {resp.status_code} — {resp.text}\n")


def test_glm_latency():
    print("── Test 3: Latency check ──")
    import time

    payload = {
        "model": "glm-4",
        "messages": [{"role": "user", "content": "Say OK"}],
        "max_tokens": 5,
    }

    start = time.time()
    resp = httpx.post(
        f"{ZAI_BASE}/chat/completions",
        headers={"Authorization": f"Bearer {ZAI_KEY}"},
        json=payload,
        timeout=30,
    )
    elapsed = time.time() - start

    print(f"Response time: {elapsed:.2f}s")
    if elapsed > 10:
        print("WARN — GLM is slow. Consider streaming for UX.")
    else:
        print("PASS ✓ — acceptable latency\n")


if __name__ == "__main__":
    if not ZAI_KEY:
        print("ERROR — ZAI_API_KEY not found in .env")
        exit(1)

    test_glm_connection()
    test_glm_model_info()
    test_glm_latency()