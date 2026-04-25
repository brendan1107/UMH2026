# debug_glm.py — async version with longer timeout
# Run: python debug_glm.py
 
import asyncio, httpx, os, json, sys
from pathlib import Path
 
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv
load_dotenv(dotenv_path=ROOT / ".env")
 
base  = os.getenv("GLM_API_BASE_URL", "").rstrip("/")
key   = os.getenv("GLM_API_KEY", "")
model = os.getenv("GLM_MODEL_NAME", "ilmu-glm-5.1")
 
print(f"Calling : {base}/chat/completions")
print(f"Model   : {model}")
print(f"Key     : {key[:15]}...\n")
print("Waiting for response (up to 90s)...\n")
 
async def main():
    async with httpx.AsyncClient(timeout=90) as client:
        resp = await client.post(
            f"{base}/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": "Say OK"}],
                "temperature": 0.1,
                "max_tokens": 20,
            },
        )
 
    print(f"HTTP Status : {resp.status_code}")
    print(f"\nFull raw response:")
    try:
        data = resp.json()
        print(json.dumps(data, indent=2))
 
        print("\n--- Extracting content ---")
        if "choices" in data and data["choices"]:
            c = data["choices"][0]
            print(f"choices[0] keys : {list(c.keys())}")
            if "message" in c:
                print(f"message keys    : {list(c['message'].keys())}")
                print(f"content         : {c['message'].get('content')}")
            elif "text" in c:
                print(f"text            : {c['text']}")
        elif "output" in data:
            print(f"output          : {data['output']}")
        elif "result" in data:
            print(f"result          : {data['result']}")
        else:
            print(f"Top-level keys  : {list(data.keys())}")
 
    except Exception as e:
        print(f"Could not parse JSON: {e}")
        print(f"Raw text: {resp.text[:500]}")
 
asyncio.run(main())