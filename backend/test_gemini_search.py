import os
import httpx
import asyncio
from dotenv import load_dotenv

load_dotenv()

async def test_search():
    api_key = os.getenv("GLM_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    
    payload = {
        "contents": [{
            "parts": [{"text": "What is the exact population of Kuala Lumpur in 2024? Search the web."}]
        }],
        "tools": [{"googleSearch": {}}]
    }
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=payload)
        print(resp.status_code)
        print(resp.text)

if __name__ == "__main__":
    asyncio.run(test_search())
