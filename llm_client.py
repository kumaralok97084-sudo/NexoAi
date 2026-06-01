from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

from litellm import acompletion

logger = logging.getLogger(__name__)

TOKEN_LIMIT_ERRORS = ("rate_limit", "rate limited", "token limit", "maximum context",
                      "too many tokens", "capacity", "insufficient_quota")

RETRYABLE_ERRORS = ("rate_limit", "rate limited", "insufficient_quota",
                    "timeout", "server error", "503", "502", "429")

MAX_RETRIES = 3
BASE_DELAY = 2.0


class LLMClient:
    def __init__(
        self,
        openrouter_api_key: str = "",
        openrouter_model: str = "openai/gpt-4o-mini",
        groq_api_key: str = "",
        groq_model: str = "groq/llama-3.1-8b-instant",
        cerebras_api_key: str = "",
        cerebras_model: str = "cerebras/llama3.1-8b",
        nvidia_api_key: str = "",
        nvidia_model: str = "nvidia/llama-3.1-nemotron-70b-instruct",
        pollinations_api_key: str = "",
        pollinations_model: str = "openai/gpt-4o-mini",
        pollinations_base_url: str = "",
        vllm_base_url: str = "",
        vllm_api_key: str = "",
        vllm_model: str = "",
        fallback_order: list[str] | None = None,
    ) -> None:
        self.providers: dict[str, dict[str, str]] = {
            "openrouter": {
                "api_key": openrouter_api_key,
                "model": openrouter_model,
            },
            "groq": {
                "api_key": groq_api_key,
                "model": groq_model,
            },
            "cerebras": {
                "api_key": cerebras_api_key,
                "model": cerebras_model,
            },
            "nvidia": {
                "api_key": nvidia_api_key,
                "model": nvidia_model,
            },
            "pollinations": {
                "api_key": pollinations_api_key,
                "model": pollinations_model,
                "api_base": pollinations_base_url,
            },
            "vllm": {
                "api_key": vllm_api_key,
                "model": vllm_model,
                "api_base": vllm_base_url,
            },
        }
        self.fallback_order = fallback_order or ["groq", "openrouter", "cerebras"]
        self._token_usage: dict[str, int] = {}
        self._rate_limited: set[str] = set()

    async def moderate_text(self, text: str) -> tuple[bool, str]:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a content moderator. Analyze the message and respond with ONLY a JSON object "
                    "with two fields: \"flagged\" (boolean) and \"reason\" (string). "
                    "Flag the message if it contains: hate speech, harassment, bullying, threats, "
                    "sexual content, NSFW, gore, violence, or abusive language. "
                    "The reason must be short like 'hate speech', 'harassment', 'NSFW', 'abusive', 'none'."
                ),
            },
            {"role": "user", "content": f"Message to moderate: {text[:1500]}"},
        ]
        try:
            resp = await self.chat(messages, temperature=0.0, max_tokens=100)
            import json
            cleaned = resp.strip().removeprefix("```json").removesuffix("```").strip()
            result = json.loads(cleaned)
            flagged = bool(result.get("flagged", False))
            reason = str(result.get("reason", "none"))
            return flagged, reason
        except Exception:
            return False, "none"

    async def moderate_image_url(self, image_url: str) -> tuple[bool, str]:
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Analyze this image for moderation. Respond with ONLY a JSON object "
                            "with two fields: \"flagged\" (boolean) and \"reason\" (string). "
                            "Flag if it contains: nudity, sexual content, gore, violence, or hate symbols. "
                            "Reason should be short: 'nudity', 'sexual', 'gore', 'violence', 'hate', 'none'."
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": image_url},
                    },
                ],
            }
        ]
        try:
            resp = await self.chat(
                messages,
                temperature=0.0,
                max_tokens=100,
                model="openai/gpt-4o-mini",
            )
            import json
            cleaned = resp.strip().removeprefix("```json").removesuffix("```").strip()
            result = json.loads(cleaned)
            flagged = bool(result.get("flagged", False))
            reason = str(result.get("reason", "none"))
            return flagged, reason
        except Exception:
            return False, "none"

    def get_usage_summary(self) -> str:
        if not self._token_usage:
            return "No token usage recorded."
        parts = [f"{name}: {count}" for name, count in self._token_usage.items()]
        limited = ", ".join(self._rate_limited) if self._rate_limited else "none"
        return " | ".join(parts) + f" | rate_limited: {limited}"

    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 800,
        model: str | None = None,
    ) -> str:
        errors: list[str] = []
        attempted: set[str] = set()
        last_exc: Exception | None = None

        for provider_name in self.fallback_order:
            provider = self.providers.get(provider_name)
            if not provider:
                continue
            if provider_name in attempted:
                continue
            if provider_name in self._rate_limited:
                continue
            attempted.add(provider_name)

            api_key = str(provider.get("api_key", "")).strip()
            api_base = str(provider.get("api_base", "")).strip()
            provider_model = model or str(provider["model"])
            litellm_kwargs: dict[str, Any] = {
                "model": provider_model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }

            if api_key:
                env_var = self._get_env_var(provider_name)
                previous = os.environ.get(env_var)
                os.environ[env_var] = api_key
            else:
                env_var = None
                previous = None

            if api_base:
                os.environ["LITELLM_API_BASE"] = api_base

            retries = 0
            success = False
            while retries < MAX_RETRIES and not success:
                try:
                    response = await acompletion(**litellm_kwargs)
                    content = response.choices[0].message.content or "Empty response."

                    usage = getattr(response, "usage", None)
                    if usage:
                        total = getattr(usage, "total_tokens", 0) or 0
                        self._token_usage[provider_name] = self._token_usage.get(provider_name, 0) + total

                    success = True
                except Exception as exc:
                    last_exc = exc
                    err_str = str(exc).lower()
                    is_retryable = any(tag in err_str for tag in RETRYABLE_ERRORS)

                    if is_retryable and retries < MAX_RETRIES - 1:
                        retries += 1
                        delay = BASE_DELAY ** retries
                        logger.warning(
                            "%s attempt %d/%d failed (%s), retrying in %.1fs",
                            provider_name, retries, MAX_RETRIES, exc, delay,
                        )
                        await asyncio.sleep(delay)
                    else:
                        if is_retryable:
                            self._rate_limited.add(provider_name)
                        retries = MAX_RETRIES

            if env_var and previous is not None:
                if previous is None:
                    os.environ.pop(env_var, None)
                else:
                    os.environ[env_var] = previous
            if api_base:
                os.environ.pop("LITELLM_API_BASE", None)

            if success:
                return content

            errors.append(f"{provider_name}: {last_exc}")
            is_token_limit = any(tag in str(last_exc).lower() for tag in TOKEN_LIMIT_ERRORS)
            if is_token_limit:
                logger.warning("Token limit hit on %s, switching provider.", provider_name)
            else:
                logger.warning("Provider %s failed: %s", provider_name, last_exc)

        if errors:
            raise RuntimeError("All providers failed. " + " | ".join(str(e) for e in errors[:3]))
        raise RuntimeError("No LLM providers configured. Add API keys in config.yaml.")

    @staticmethod
    def _get_env_var(provider_name: str) -> str:
        mapping = {
            "openrouter": "OPENROUTER_API_KEY",
            "groq": "GROQ_API_KEY",
            "cerebras": "CEREBRAS_API_KEY",
            "nvidia": "NVIDIA_API_KEY",
            "pollinations": "OPENAI_API_KEY",
            "vllm": "VLLM_API_KEY",
        }
        return mapping.get(provider_name, f"{provider_name.upper()}_API_KEY")

    def set_fallback_order(self, order: list[str]) -> None:
        self.fallback_order = order
