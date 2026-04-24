"""
GLM API Client

Client for Z AI GLM model — the core reasoning engine (SAD Section 9).
Handles API calls, retries, and fallback behavior (SAD Section 13).
"""

import httpx
from fastapi import HTTPException, status

from app.config import settings

# What is this glm_client.py file for?
# The glm_client.py file defines a client for interacting with the Z AI GLM model, which serves as the core reasoning engine for our application. This client will handle API calls to the GLM model, including sending chat completion requests and performing health checks. It will also implement retry logic and fallback behavior to ensure that our application can gracefully handle any issues with the GLM API, such as downtime or rate limits. By encapsulating the GLM interactions in this client, we can keep our code organized and make it easier to manage our AI model interactions across our application.
class GLMClient:
    """Client for interacting with the GLM API."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        http_client_factory=None,
    ):
        self.api_key = api_key if api_key is not None else settings.GLM_API_KEY
        self.base_url = (
            base_url if base_url is not None else settings.GLM_API_BASE_URL
        ).rstrip("/")
        self.model = settings.GLM_MODEL_NAME
        if model is not None:
            self.model = model
        self.max_tokens = settings.GLM_MAX_TOKENS
        self.http_client_factory = http_client_factory or httpx.AsyncClient

    async def chat_completion(self, messages: list, temperature: float = 0.7) -> str:
        """Send a chat completion request to GLM."""
        if not self.api_key or not self.base_url:
            return (
                "AI model is not configured. Your message was recorded, but no "
                "model-backed analysis was generated."
            )

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": self.max_tokens,
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        last_error = None

        for _ in range(2):
            try:
                async with self.http_client_factory(timeout=30.0) as client:
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                    )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
            except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
                last_error = exc

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"GLM request failed: {last_error}",
        )

    async def health_check(self) -> bool:
        """Check if GLM API is available."""
        if not self.api_key or not self.base_url:
            return False
        try:
            async with self.http_client_factory(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/models",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
            return response.status_code < 500
        except httpx.HTTPError:
            return False
