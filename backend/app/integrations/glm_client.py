"""
GLM API Client

Client for Z AI GLM model — the core reasoning engine (SAD Section 9).
Handles API calls, retries, and fallback behavior (SAD Section 13).
"""

import json
import httpx
from app.config import settings

# What is this glm_client.py file for?
# The glm_client.py file defines a client for interacting with the Z AI GLM model, which serves as the core reasoning engine for our application. This client will handle API calls to the GLM model, including sending chat completion requests and performing health checks. It will also implement retry logic and fallback behavior to ensure that our application can gracefully handle any issues with the GLM API, such as downtime or rate limits. By encapsulating the GLM interactions in this client, we can keep our code organized and make it easier to manage our AI model interactions across our application.
class GLMClient:
    """Client for interacting with the GLM API."""

    def __init__(self):
        self.api_key = settings.GLM_API_KEY
        self.base_url = settings.GLM_API_BASE_URL
        self.model = settings.GLM_MODEL_NAME
        self.max_tokens = settings.GLM_MAX_TOKENS

    async def chat_completion(
        self,
        messages: list[dict],
        system: str,
        temperature: float = 0.2,
    ) -> str:
        """Send a chat completion request and return raw content string."""
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                *messages,
            ],
            "temperature": temperature,
            "max_tokens": self.max_tokens,
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
            )
            resp.raise_for_status()

        content = resp.json()["choices"][0]["message"]["content"]

        # Strip markdown fences if model wraps in ```json
        content = content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        return content.strip()

    async def health_check(self) -> bool:
        """Check if GLM API is available."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{self.base_url}/models",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
            return resp.status_code == 200
        except Exception:
            return False


# Singleton — import this everywhere
glm_client = GLMClient()
