import httpx, os, json
from dotenv import load_dotenv
load_dotenv()

  # ZAI endpoint
ZAI_KEY  = os.getenv("GLM_API_KEY")
ZAI_BASE = os.getenv("GLM_API_BASE_URL")

resp = httpx.post(
    ZAI_BASE,
    headers={"Authorization": f"Bearer {ZAI_KEY}"},
    json={
        "model": "ilmu-glm-5.1",
        "messages": [
            {"role": "system", "content": "Output only valid JSON"},
            {"role": "user", "content": 'Reply with: {"status": "alive"}'},
        ],
        "temperature": 0.1,
        "max_tokens": 500,
    },
    timeout=30
)
print(resp.status_code)
print(json.dumps(resp.json(), indent=2))