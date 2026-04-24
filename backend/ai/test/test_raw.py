import httpx, os, json
from dotenv import load_dotenv
load_dotenv()

key = os.getenv("ZAI_API_KEY")
resp = httpx.post(
    "https://api.ilmu.ai/v1/chat/completions",
    headers={"Authorization": f"Bearer {key}"},
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