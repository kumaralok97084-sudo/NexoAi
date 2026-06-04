from __future__ import annotations

import json
import logging
import re
from typing import Any
from urllib.parse import quote

import httpx

logger = logging.getLogger(__name__)

POLLINATIONS_IMAGE_BASE = "https://image.pollinations.ai/prompt"
OPENROUTER_BASE = "https://openrouter.ai/api/v1"

POLLINATIONS_MODELS = frozenset({
    "flux",
    "flux-pro",
    "turbo",
    "dreamshaper",
    "realistic-vision",
})

CHAT_IMAGE_MODELS = frozenset({
    "black-forest-labs/flux-schnell",
    "black-forest-labs/flux-dev",
    "black-forest-labs/flux-pro",
    "black-forest-labs/flux-1.1-pro",
    "black-forest-labs/flux-1.1-pro-ultra",
    "stabilityai/stable-diffusion-3.5-large-turbo",
    "stabilityai/stable-diffusion-3.5-medium",
    "stabilityai/stable-diffusion-3.5-large",
    "bytedance/sdxl-lightning-4step",
    "luma/photon",
    "luma/photon-flash",
})

DEDICATED_IMAGE_MODELS = frozenset({
    "openai/dall-e-3",
    "openai/dall-e-2",
})

RECOMMENDED_MODELS = [
    "flux",
    "flux-pro",
    "turbo",
    "dreamshaper",
    "realistic-vision",
    "black-forest-labs/flux-schnell",
    "black-forest-labs/flux-dev",
    "black-forest-labs/flux-1.1-pro",
    "stabilityai/stable-diffusion-3.5-large-turbo",
    "openai/dall-e-3",
    "black-forest-labs/flux-1.1-pro-ultra",
    "luma/photon",
    "luma/photon-flash",
]

IMAGE_URL_RE = re.compile(r"https?://[^\s)]+\.(?:png|jpg|jpeg|gif|webp)(?:\?[^\s)]*)?")

PROMPT_ENHANCE_INSTRUCTION = (
    "You are an expert prompt engineer for image generation. "
    "Enhance the given prompt to be more detailed, visually descriptive, "
    "and optimized for AI image generation. Add lighting, style, composition details. "
    "Keep the original intent. Return ONLY the enhanced prompt, no explanations."
)


class ImageGenerator:
    def __init__(self, api_key: str, model: str, provider: str = "openrouter") -> None:
        self.api_key = api_key
        self.model = model
        self.provider = provider
        self._client: httpx.AsyncClient | None = None

    def _build_pollinations_url(self, prompt: str, size: str | None = None) -> str:
        params = []
        model_lower = self.model.lower()
        if model_lower in POLLINATIONS_MODELS:
            params.append(f"model={model_lower}")
        if size:
            parts = size.lower().split("x")
            if len(parts) == 2:
                params.append(f"width={parts[0]}")
                params.append(f"height={parts[1]}")
        param_str = f"?{'&'.join(params)}" if params else ""
        return f"{POLLINATIONS_IMAGE_BASE}/{quote(prompt[:2000])}{param_str}"

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=90.0)
        return self._client

    async def enhance_prompt(self, prompt: str, llm_chat_func: Any = None) -> str:
        if not llm_chat_func:
            return prompt
        try:
            enhanced = await llm_chat_func(
                [
                    {"role": "system", "content": PROMPT_ENHANCE_INSTRUCTION},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.5,
                max_tokens=300,
            )
            result = enhanced.strip().strip('"').strip("'")
            return result if result else prompt
        except Exception as exc:
            logger.debug("Prompt enhancement failed: %s", exc)
            return prompt

    async def generate(
        self,
        prompt: str,
        negative_prompt: str = "",
        size: str | None = None,
        image_url: str | None = None,
        mode: str = "generate",
    ) -> dict[str, Any]:
        if self.provider == "pollinations":
            url = self._build_pollinations_url(prompt, size)
            return {
                "url": url,
                "revised_prompt": prompt,
                "model": self.model,
            }

        if not self.api_key:
            return {"error": "Image generation API key is not configured."}

        model_lower = self.model.lower()

        if mode == "variation" and image_url:
            return await self._generate_variation(prompt, model_lower, image_url)
        if mode == "edit" and image_url:
            return await self._generate_edit(prompt, model_lower, image_url)

        if model_lower in DEDICATED_IMAGE_MODELS:
            return await self._generate_dedicated(prompt, model_lower, size)
        if model_lower in CHAT_IMAGE_MODELS:
            return await self._generate_chat_based(prompt, model_lower, negative_prompt, image_url)
        return await self._generate_chat_based(prompt, self.model, negative_prompt, image_url)

    async def _generate_variation(self, prompt: str, model: str, image_url: str) -> dict[str, Any]:
        return await self._generate_chat_based(
            f"Generate a variation of this image with the following changes: {prompt}",
            model,
            "",
            image_url,
        )

    async def _generate_edit(self, prompt: str, model: str, image_url: str) -> dict[str, Any]:
        return await self._generate_chat_based(
            f"Edit this image: {prompt}",
            model,
            "",
            image_url,
        )

    async def _generate_dedicated(
        self, prompt: str, model: str, size: str | None = None
    ) -> dict[str, Any]:
        client = await self._get_client()
        body: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "n": 1,
        }
        if model == "openai/dall-e-3":
            body["quality"] = "hd"
            body["size"] = size or "1024x1024"
        elif model == "openai/dall-e-2":
            body["size"] = size or "512x512"

        try:
            response = await client.post(
                f"{OPENROUTER_BASE}/images/generations",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=body,
            )
            response.raise_for_status()
            data: dict[str, Any] = response.json()
        except httpx.HTTPStatusError as exc:
            logger.error("Dedicated image gen error: %s", exc)
            return {"error": f"Image generation failed: HTTP {exc.response.status_code}"}
        except Exception as exc:
            logger.error("Dedicated image gen request failed: %s", exc)
            return {"error": f"Image generation failed: {exc}"}

        image_data = data.get("data", [])
        if not image_data:
            return {"error": "No image was generated."}

        first = image_data[0]
        url = first.get("url") or first.get("b64_json", "")
        if not url:
            return {"error": "No image URL in response."}

        revised = first.get("revised_prompt", prompt)
        return {
            "url": url,
            "revised_prompt": revised,
            "model": self.model,
            "is_base64": bool(first.get("b64_json")),
        }

    async def _generate_chat_based(
        self, prompt: str, model: str, negative_prompt: str = "", image_url: str | None = None
    ) -> dict[str, Any]:
        client = await self._get_client()
        content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
        if image_url:
            content.append({"type": "image_url", "image_url": {"url": image_url}})

        body: dict[str, Any] = {
            "model": model,
            "messages": [{"role": "user", "content": content}],
            "max_tokens": 1500,
        }
        if negative_prompt:
            body["negative_prompt"] = negative_prompt

        try:
            response = await client.post(
                f"{OPENROUTER_BASE}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=body,
            )
            response.raise_for_status()
            data: dict[str, Any] = response.json()
        except httpx.HTTPStatusError as exc:
            logger.error("Chat image gen error: %s", exc)
            return {"error": f"Image generation failed: HTTP {exc.response.status_code}"}
        except Exception as exc:
            logger.error("Chat image gen request failed: %s", exc)
            return {"error": f"Image generation failed: {exc}"}

        choices = data.get("choices", [])
        if not choices:
            return {"error": "No image was generated."}

        message = choices[0].get("message", {})
        content_text = message.get("content", "")

        urls = IMAGE_URL_RE.findall(content_text)
        if urls:
            return {
                "url": urls[0],
                "revised_prompt": prompt,
                "model": self.model,
                "raw_content": content_text,
            }

        return {"error": content_text.strip() or "No image URL found in response."}

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    @staticmethod
    def get_available_models() -> list[str]:
        return list(RECOMMENDED_MODELS)
