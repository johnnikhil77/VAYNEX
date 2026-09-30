"""OpenAI-backed provider (optional).

Uses the Chat Completions REST API through ``httpx`` so no extra SDK is
required. Any failure (network, quota, invalid JSON) falls back to the
deterministic mock provider so the operator workflow never breaks.
"""

from __future__ import annotations

import json
import logging

import httpx
from pydantic import ValidationError

from packages.intelligence.interface import AIProvider
from packages.intelligence.mock_provider import MockAIProvider
from packages.intelligence.prompts import SYSTEM_PROMPT, build_user_prompt
from packages.intelligence.schemas import AIAnalysis, IncidentContext

logger = logging.getLogger("vaynex.intelligence.openai")

OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"


class OpenAIProvider(AIProvider):
    name = "openai"

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        *,
        timeout_seconds: float = 20.0,
        base_url: str = OPENAI_CHAT_URL,
        fallback: AIProvider | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("OpenAIProvider requires an API key")
        self._api_key = api_key
        self.model = model
        self._timeout = timeout_seconds
        self._url = base_url
        self._fallback = fallback or MockAIProvider()
        self._transport = transport

    def __repr__(self) -> str:  # never expose the key
        return f"OpenAIProvider(model={self.model!r})"

    async def analyze_incident(self, context: IncidentContext) -> AIAnalysis:
        try:
            return await self._call(context)
        except (httpx.HTTPError, ValueError, KeyError, ValidationError, json.JSONDecodeError) as exc:
            logger.warning("OpenAI analysis failed (%s); using deterministic fallback", type(exc).__name__)
            analysis = await self._fallback.analyze_incident(context)
            return analysis.model_copy(update={"provider": f"{analysis.provider}-fallback"})

    async def _call(self, context: IncidentContext) -> AIAnalysis:
        body = {
            "model": self.model,
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_prompt(context)},
            ],
        }
        headers = {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=self._timeout, transport=self._transport) as client:
            response = await client.post(self._url, json=body, headers=headers)
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
        data = json.loads(content)
        data.setdefault("confidence", 0.7)
        data["confidence"] = max(0.0, min(1.0, float(data["confidence"])))
        data["recommended_actions"] = list(data.get("recommended_actions") or [])[:5]
        analysis = AIAnalysis.model_validate({**data, "provider": self.name, "model": self.model})
        return analysis
