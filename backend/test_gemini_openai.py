import os
import httpx
import asyncio
import json

# Manually load from .env.backend or env.backend
# Since I can't easily use the app's settings here without setup, I'll just hardcode or read the file.

def get_env_val(key):
    paths = ["env.backend", ".env.backend", "../.env.backend"]
    for path in paths:
        if os.path.exists(path):
            with open(path, "r") as f:
                for line in f:
                    if line.startswith(f"{key}="):
                        return line.split("=", 1)[1].strip()
    return os.environ.get(key)

async def test_gemini():
    api_key = get_env_val("GLM_API_KEY")
    base_url = get_env_val("GLM_API_BASE_URL").rstrip("/")
    model = get_env_val("GLM_MODEL_NAME") or "gemini-2.5-flash"
    
    print(f"Testing URL: {base_url}/chat/completions")
    print(f"Model: {model}")
    print(f"API Key exists: {bool(api_key)}")
    
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": "Hello, respond with a JSON object: {\"type\": \"text\", \"content\": \"Success\"}"}
        ],
        "temperature": 0.2,
    }
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=payload
            )
            print(f"Status: {resp.status_code}")
            print(f"Body: {resp.text[:500]}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_gemini())
