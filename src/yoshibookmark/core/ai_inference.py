"""AI provider-chain inference helpers for ingestion and agent workflows."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx

from ..models.config import AppConfig

logger = logging.getLogger(__name__)


TRANSIENT_FAILURES = {"timeout", "network", "ratelimit", "server_error"}


@dataclass
class ProviderAttemptDiagnostics:
    provider_id: str
    model_name: str
    attempted: bool
    succeeded: bool
    failure_type: Optional[str] = None
    message: Optional[str] = None


class AIProviderError(Exception):
    """Provider-specific error with failover semantics."""

    def __init__(self, provider_id: str, failure_type: str, message: str):
        super().__init__(message)
        self.provider_id = provider_id
        self.failure_type = failure_type
        self.message = message

    @property
    def is_transient(self) -> bool:
        return self.failure_type in TRANSIENT_FAILURES


class MultiProviderInferenceService:
    """Runs prompt inference against configured providers with failover."""

    def __init__(self, config: AppConfig):
        self.config = config

    async def generate_structured_metadata(
        self,
        url: str,
        page_title: str,
        page_excerpt: str,
        selected_text: str,
        user_note: str,
    ) -> tuple[Optional[dict], List[ProviderAttemptDiagnostics]]:
        prompt = self._build_prompt(url, page_title, page_excerpt, selected_text, user_note)
        attempts: List[ProviderAttemptDiagnostics] = []

        for provider_id in self._ordered_providers():
            try:
                provider_cfg = self._provider_config(provider_id)
                if provider_cfg is None or not provider_cfg["enabled"]:
                    attempts.append(
                        ProviderAttemptDiagnostics(
                            provider_id, provider_cfg["model"] if provider_cfg else "", True, False,
                            "configuration", "Provider disabled or unknown"
                        )
                    )
                    continue

                text = await self._generate_text(provider_id, prompt)
                parsed = self._parse_json_payload(text)
                attempts.append(
                    ProviderAttemptDiagnostics(provider_id, provider_cfg["model"], True, True)
                )
                return parsed, attempts
            except AIProviderError as e:
                attempts.append(
                    ProviderAttemptDiagnostics(
                        e.provider_id,
                        self._provider_config(e.provider_id)["model"]
                        if self._provider_config(e.provider_id)
                        else "",
                        True,
                        False,
                        e.failure_type,
                        e.message,
                    )
                )
                if not e.is_transient:
                    break
                continue
            except Exception as e:
                attempts.append(
                    ProviderAttemptDiagnostics(
                        provider_id,
                        self._provider_config(provider_id)["model"]
                        if self._provider_config(provider_id)
                        else "",
                        True,
                        False,
                        "unknown",
                        str(e),
                    )
                )
                continue

        return None, attempts

    def get_provider_status(self) -> list[dict]:
        """Return provider configuration status for diagnostics endpoints."""
        result: List[dict] = []
        for provider_id in self._ordered_providers():
            cfg = self._provider_config(provider_id)
            if not cfg:
                continue
            result.append(
                {
                    "provider_id": provider_id,
                    "enabled": cfg["enabled"],
                    "model": cfg["model"],
                    "has_endpoint": bool(cfg["endpoint"]),
                    "key_count": len(cfg["api_keys"]),
                }
            )
        return result

    def _ordered_providers(self) -> list[str]:
        default_order = ["openai", "azureopenai", "anthropic", "gemini"]
        configured = [p.strip().lower() for p in self.config.agent_providers if p.strip()]
        if not configured:
            configured = default_order
        seen = set()
        ordered: list[str] = []
        for provider in configured + default_order:
            if provider not in seen:
                seen.add(provider)
                ordered.append(provider)
        return ordered

    def _provider_config(self, provider_id: str) -> Optional[dict]:
        if provider_id == "openai":
            return {
                "enabled": self.config.openai_enabled,
                "endpoint": self.config.openai_endpoint,
                "model": self.config.openai_model,
                "api_keys": self.config.openai_api_keys,
            }
        if provider_id == "azureopenai":
            return {
                "enabled": self.config.azure_openai_enabled,
                "endpoint": self.config.azure_openai_endpoint,
                "model": self.config.azure_openai_model,
                "api_keys": self.config.azure_openai_api_keys,
            }
        if provider_id == "anthropic":
            return {
                "enabled": self.config.anthropic_enabled,
                "endpoint": self.config.anthropic_endpoint,
                "model": self.config.anthropic_model,
                "api_keys": self.config.anthropic_api_keys,
            }
        if provider_id == "gemini":
            return {
                "enabled": self.config.gemini_enabled,
                "endpoint": self.config.gemini_endpoint,
                "model": self.config.gemini_model,
                "api_keys": self.config.gemini_api_keys,
            }
        return None

    async def _generate_text(self, provider_id: str, prompt: str) -> str:
        cfg = self._provider_config(provider_id)
        if not cfg:
            raise AIProviderError(provider_id, "configuration", "Unknown provider")

        endpoint = cfg["endpoint"]
        model = cfg["model"]
        api_keys = cfg["api_keys"]
        if not endpoint:
            raise AIProviderError(provider_id, "configuration", "Endpoint is not configured")
        if not model:
            raise AIProviderError(provider_id, "configuration", "Model is not configured")
        if not api_keys:
            raise AIProviderError(provider_id, "configuration", "API key is not configured")

        timeout = self.config.agent_timeout_seconds

        last_error: Optional[AIProviderError] = None
        for api_key in api_keys:
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    if provider_id in {"openai", "azureopenai"}:
                        headers = {"Content-Type": "application/json"}
                        if provider_id == "openai":
                            headers["Authorization"] = f"Bearer {api_key}"
                        else:
                            headers["api-key"] = api_key
                        body = {
                            "model": model,
                            "messages": [
                                {"role": "system", "content": "You output compact JSON only."},
                                {"role": "user", "content": prompt},
                            ],
                        }
                        response = await client.post(endpoint, headers=headers, json=body)
                        self._raise_for_status(provider_id, response)
                        data = response.json()
                        return data["choices"][0]["message"]["content"]

                    if provider_id == "anthropic":
                        headers = {
                            "x-api-key": api_key,
                            "anthropic-version": "2023-06-01",
                            "content-type": "application/json",
                        }
                        body = {
                            "model": model,
                            "max_tokens": 300,
                            "messages": [{"role": "user", "content": prompt}],
                            "temperature": 0.2,
                        }
                        response = await client.post(endpoint, headers=headers, json=body)
                        self._raise_for_status(provider_id, response)
                        data = response.json()
                        chunks = data.get("content", [])
                        text_values = [
                            chunk.get("text", "") for chunk in chunks if chunk.get("type") == "text"
                        ]
                        return "\n".join(text_values).strip()

                    if provider_id == "gemini":
                        endpoint_url = endpoint.replace("{model}", model)
                        headers = {"Content-Type": "application/json"}
                        body = {
                            "contents": [{"parts": [{"text": prompt}]}],
                            "generationConfig": {"temperature": 0.2},
                        }
                        response = await client.post(
                            f"{endpoint_url}?key={api_key}",
                            headers=headers,
                            json=body,
                        )
                        self._raise_for_status(provider_id, response)
                        data = response.json()
                        return data["candidates"][0]["content"]["parts"][0]["text"]

                    raise AIProviderError(provider_id, "configuration", "Unsupported provider")
            except AIProviderError as e:
                last_error = e
                if not e.is_transient:
                    raise
                continue
            except httpx.TimeoutException:
                last_error = AIProviderError(provider_id, "timeout", "Request timed out")
                continue
            except httpx.NetworkError as e:
                last_error = AIProviderError(provider_id, "network", f"Network error: {e}")
                continue
            except Exception as e:
                last_error = AIProviderError(provider_id, "unknown", str(e))
                continue

        raise last_error or AIProviderError(provider_id, "unknown", "Provider request failed")

    def _raise_for_status(self, provider_id: str, response: httpx.Response) -> None:
        if response.status_code < 400:
            return
        message = response.text[:500]
        if response.status_code in {401, 403}:
            raise AIProviderError(provider_id, "authentication", message)
        if response.status_code == 429:
            raise AIProviderError(provider_id, "ratelimit", message)
        if response.status_code >= 500:
            raise AIProviderError(provider_id, "server_error", message)
        raise AIProviderError(provider_id, "invalid_request", message)

    def _build_prompt(
        self, url: str, page_title: str, page_excerpt: str, selected_text: str, user_note: str
    ) -> str:
        return (
            "Given page capture context, output strict JSON with keys: "
            "title (string), keywords (array up to 4), tags (array up to 6), "
            "summary (string <= 220 chars), confidence (0-1). "
            "No markdown.\n"
            f"URL: {url}\n"
            f"Page title: {page_title}\n"
            f"Page excerpt: {page_excerpt[:1500]}\n"
            f"Selected text: {selected_text[:1000]}\n"
            f"User note: {user_note[:500]}"
        )

    def _parse_json_payload(self, text: str) -> dict:
        candidate = text.strip()
        if "```" in candidate:
            candidate = candidate.replace("```json", "").replace("```", "").strip()
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            extracted = self._extract_first_json_object(candidate)
            if extracted is not None:
                return extracted
            raise

    def _extract_first_json_object(self, text: str) -> Optional[dict]:
        """Extract first valid JSON object from mixed model output."""
        decoder = json.JSONDecoder()
        for idx, char in enumerate(text):
            if char not in "{[":
                continue
            try:
                parsed, _ = decoder.raw_decode(text[idx:])
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                return parsed
        return None
