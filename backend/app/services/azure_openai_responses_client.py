from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import httpx
import json
import logging

from app.core.config import settings

# Use the same logger name as the parsing logs so it shows up consistently in the console.
logger = logging.getLogger("app.services.universal_parsing_service")


@dataclass(frozen=True)
class ResponsesUsage:
    input_tokens: int
    output_tokens: int


@dataclass(frozen=True)
class ResponsesTextResult:
    text: str
    usage: ResponsesUsage
    raw: dict[str, Any]


class AzureOpenAIResponsesClient:
    def __init__(
        self,
        *,
        responses_url: str,
        api_key: str,
        timeout_seconds: float = 60.0,
    ) -> None:
        self._responses_url = responses_url.rstrip("/")
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def create_text_response(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        reasoning_effort: Optional[str] = None,
    ) -> ResponsesTextResult:
        payload: dict[str, Any] = {
            "model": model,
            "input": [
                {"type": "message", "role": "system", "content": system_prompt},
                {"type": "message", "role": "user", "content": user_prompt},
            ],
        }

        # Reasoning models (e.g., o4-mini / gpt-5.1) do not accept temperature.
        if reasoning_effort:
            payload["reasoning"] = {"effort": reasoning_effort}
        elif temperature is not None:
            payload["temperature"] = float(temperature)

        headers = {
            "api-key": self._api_key,
            "content-type": "application/json",
        }

        if bool(getattr(settings, "LOG_AOAI_REQUEST_BODY", False)):
            try:
                dumped = json.dumps(payload, ensure_ascii=False, indent=2)
            except Exception:
                dumped = str(payload)

            max_chars = int(getattr(settings, "LOG_AOAI_REQUEST_MAX_CHARS", 120000) or 120000)
            if max_chars > 0 and len(dumped) > max_chars:
                logger.info(
                    "发送给AOAI的 /responses request body (TRUNCATED %d -> %d chars) url=%s\n%s",
                    len(dumped),
                    max_chars,
                    self._responses_url,
                    dumped[:max_chars],
                )
            else:
                logger.info("发送给AOAI的 /responses request body url=%s\n%s", self._responses_url, dumped)

        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            resp = await client.post(self._responses_url, headers=headers, json=payload)

        resp.raise_for_status()
        data = resp.json()

        if data.get("error"):
            raise RuntimeError(f"Azure OpenAI responses error: {data['error']}")

        text = _extract_output_text(data)

        if bool(getattr(settings, "LOG_AOAI_RESPONSE_TEXT", False)):
            # Print only the model output text (no raw JSON) for debugging.
            logger.info("AOAI返回文本(output_text):\n%s", text or "")
        usage = _extract_usage(data)

        return ResponsesTextResult(text=text, usage=usage, raw=data)


def _extract_output_text(data: dict[str, Any]) -> str:
    output = data.get("output") or []
    texts: list[str] = []

    for item in output:
        if not isinstance(item, dict):
            continue
        if item.get("type") != "message":
            continue
        content = item.get("content") or []
        for content_item in content:
            if not isinstance(content_item, dict):
                continue
            if content_item.get("type") == "output_text":
                t = content_item.get("text")
                if isinstance(t, str) and t.strip():
                    texts.append(t)

    return "\n".join(texts).strip()


def _extract_usage(data: dict[str, Any]) -> ResponsesUsage:
    usage = data.get("usage") or {}
    input_tokens = int(usage.get("input_tokens") or 0)
    output_tokens = int(usage.get("output_tokens") or 0)
    return ResponsesUsage(input_tokens=input_tokens, output_tokens=output_tokens)
