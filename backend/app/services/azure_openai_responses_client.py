from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import asyncio
import httpx
import json
import logging
import random

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
        fallback_responses_url: Optional[str] = None,
        fallback_api_key: Optional[str] = None,
        timeout_seconds: float = 600.0,
    ) -> None:
        self._responses_url = responses_url.rstrip("/")
        self._api_key = api_key
        self._fallback_responses_url = (fallback_responses_url or "").strip().rstrip("/") or None
        self._fallback_api_key = (fallback_api_key or "").strip() or None
        self._timeout_seconds = timeout_seconds

    async def create_text_response(
        self,
        *,
        model: str,
        fallback_model: Optional[str] = None,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        reasoning_effort: Optional[str] = None,
        text_format: Optional[dict[str, Any]] = None,
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

        # Structured outputs (Responses API):
        #   text: { format: { type: json_object | json_schema, ... } }
        if text_format:
            payload["text"] = {"format": text_format}

        headers = {"api-key": self._api_key, "content-type": "application/json"}

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

        data = await self._post_with_failover_and_retries(
            headers=headers,
            payload=payload,
            fallback_model=fallback_model,
        )

        if data.get("error"):
            raise RuntimeError(f"Azure OpenAI responses error: {data['error']}")

        text = _extract_output_text(data)

        if bool(getattr(settings, "LOG_AOAI_RESPONSE_TEXT", False)):
            # Print only the model output text (no raw JSON) for debugging.
            logger.info("AOAI返回文本(output_text):\n%s", text or "")
        usage = _extract_usage(data)

        return ResponsesTextResult(text=text, usage=usage, raw=data)

    @staticmethod
    def _safe_url_for_log(url: str) -> str:
        try:
            from urllib.parse import urlparse

            p = urlparse(url)
            if p.scheme and p.netloc:
                return f"{p.scheme}://{p.netloc}{p.path}"
        except Exception:
            pass
        return url

    async def _post_json(self, *, url: str, headers: dict[str, str], payload: dict[str, Any]) -> httpx.Response:
        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            return await client.post(url, headers=headers, json=payload)

    async def _post_with_retries(
        self,
        *,
        url: str,
        headers: dict[str, str],
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        max_retries = int(getattr(settings, "OPENAI_REQUEST_MAX_RETRIES", 0) or 0)
        base_backoff = float(getattr(settings, "OPENAI_REQUEST_RETRY_BACKOFF_SECONDS", 0.8) or 0.8)
        max_backoff = float(getattr(settings, "OPENAI_REQUEST_RETRY_MAX_BACKOFF_SECONDS", 8.0) or 8.0)

        attempt = 0
        while True:
            try:
                resp = await self._post_json(url=url, headers=headers, payload=payload)

                # Retry transient HTTP errors.
                if resp.status_code == 429 or 500 <= resp.status_code < 600:
                    if attempt >= max_retries:
                        resp.raise_for_status()

                    retry_after = resp.headers.get("retry-after")
                    if retry_after:
                        try:
                            delay = float(retry_after)
                        except Exception:
                            delay = base_backoff * (2**attempt)
                    else:
                        delay = base_backoff * (2**attempt)

                    delay = min(max_backoff, max(0.0, delay)) + random.uniform(0, 0.25)
                    logger.warning(
                        "AOAI /responses transient HTTP %s (attempt %d/%d). Retrying in %.2fs url=%s",
                        resp.status_code,
                        attempt + 1,
                        max_retries + 1,
                        delay,
                        self._safe_url_for_log(url),
                    )
                    attempt += 1
                    await asyncio.sleep(delay)
                    continue

                resp.raise_for_status()
                return resp.json()

            except (httpx.TimeoutException, httpx.NetworkError) as e:
                if attempt >= max_retries:
                    raise

                delay = base_backoff * (2**attempt)
                delay = min(max_backoff, max(0.0, delay)) + random.uniform(0, 0.25)
                logger.warning(
                    "AOAI /responses network/timeout error (%s) (attempt %d/%d). Retrying in %.2fs url=%s",
                    type(e).__name__,
                    attempt + 1,
                    max_retries + 1,
                    delay,
                    self._safe_url_for_log(url),
                )
                attempt += 1
                await asyncio.sleep(delay)

    async def _post_with_failover_and_retries(
        self,
        *,
        headers: dict[str, str],
        payload: dict[str, Any],
        fallback_model: Optional[str],
    ) -> dict[str, Any]:
        """Post with: primary -> (on recoverable error) immediate fallback -> retries.

        Recoverable:
        - httpx.TimeoutException / httpx.NetworkError
        - HTTP 429
        - HTTP 5xx
        """

        primary_url = self._responses_url
        primary_headers = headers

        fallback_url = self._fallback_responses_url
        fallback_key = self._fallback_api_key

        # 1) Try primary once.
        try:
            resp = await self._post_json(url=primary_url, headers=primary_headers, payload=payload)
            if resp.status_code == 429 or 500 <= resp.status_code < 600:
                raise httpx.HTTPStatusError(
                    f"Transient HTTP {resp.status_code}",
                    request=resp.request,
                    response=resp,
                )
            resp.raise_for_status()
            return resp.json()
        except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError) as e:
            # Attempt immediate failover only for recoverable cases.
            if not (fallback_url and fallback_key):
                # No fallback configured; continue with normal retry behavior on primary.
                if isinstance(e, httpx.HTTPStatusError):
                    # For non-transient HTTP errors, don't retry here.
                    status_code = getattr(getattr(e, "response", None), "status_code", None)
                    if status_code and status_code != 429 and not (500 <= status_code < 600):
                        raise
                return await self._post_with_retries(url=primary_url, headers=primary_headers, payload=payload)

            # For HTTPStatusError, verify it is transient (429/5xx) before failing over.
            if isinstance(e, httpx.HTTPStatusError):
                status_code = getattr(getattr(e, "response", None), "status_code", None)
                if status_code and status_code != 429 and not (500 <= status_code < 600):
                    raise

            # 2) Immediate fallback attempt.
            fallback_headers = {"api-key": fallback_key, "content-type": "application/json"}
            fallback_payload = dict(payload)
            if fallback_model and str(fallback_model).strip():
                fallback_payload["model"] = str(fallback_model).strip()

            logger.warning(
                "AOAI /responses failover: primary failed (%s). Switching to fallback url=%s",
                type(e).__name__,
                self._safe_url_for_log(fallback_url),
            )

            try:
                resp2 = await self._post_json(url=fallback_url, headers=fallback_headers, payload=fallback_payload)
                if resp2.status_code == 429 or 500 <= resp2.status_code < 600:
                    raise httpx.HTTPStatusError(
                        f"Transient HTTP {resp2.status_code}",
                        request=resp2.request,
                        response=resp2,
                    )
                resp2.raise_for_status()
                return resp2.json()
            except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError) as e2:
                # If fallback also transient-fails, continue retries on fallback.
                if isinstance(e2, httpx.HTTPStatusError):
                    status_code = getattr(getattr(e2, "response", None), "status_code", None)
                    if status_code and status_code != 429 and not (500 <= status_code < 600):
                        raise
                return await self._post_with_retries(url=fallback_url, headers=fallback_headers, payload=fallback_payload)


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
