from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

GOOGLE_SEARCH_URL = "https://www.googleapis.com/customsearch/v1"


class SearchClient:
    def __init__(self, api_key: str, cse_id: str) -> None:
        self.api_key = api_key
        self.cse_id = cse_id
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=15.0)
        return self._client

    async def search(self, query: str, num_results: int = 5) -> str:
        if not self.api_key or not self.cse_id:
            return "Google Search is not configured. Set `google_search.api_key` and `google_search.cse_id` in config.yaml."

        client = await self._get_client()
        try:
            response = await client.get(
                GOOGLE_SEARCH_URL,
                params={
                    "key": self.api_key,
                    "cx": self.cse_id,
                    "q": query,
                    "num": min(num_results, 10),
                },
            )
            response.raise_for_status()
            data: dict[str, Any] = response.json()
        except httpx.HTTPStatusError as exc:
            logger.error("Google Search API error: %s", exc)
            return f"Search failed: HTTP {exc.response.status_code}"
        except Exception as exc:
            logger.error("Google Search request failed: %s", exc)
            return f"Search failed: {exc}"

        items = data.get("items", [])
        if not items:
            return f"No results found for '{query}'."

        results: list[str] = []
        for i, item in enumerate(items[:num_results], 1):
            title = item.get("title", "No title")
            snippet = item.get("snippet", "").strip()
            link = item.get("link", "")
            results.append(f"{i}. {title}\n   {snippet}\n   {link}")

        return "Search results:\n\n" + "\n\n".join(results)

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
