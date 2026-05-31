from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from database import Database
    from llm_client import LLMClient

logger = logging.getLogger(__name__)

SUMMARIZE_TRIGGER_COUNT = 8
MAX_SUMMARIES_PER_USER = 10

AI_EXTRACT_PROMPT = (
    'Extract important facts about the user from this message. '
    'Return a JSON object with these optional fields (only include if present): '
    '"name", "role", "goal", "tech_stack", "domain", "issue", "preference". '
    'Also include a "keywords" field (array of 2-5 key terms for search). '
    'If nothing important, return {}. '
    'Return ONLY valid JSON, no other text.'
)

SUMMARIZE_PROMPT = (
    "Summarize the key points of this conversation in 2-3 sentences. "
    "Focus on: what the user wants, what problems they have, what solutions were discussed. "
    "Keep it concise and factual."
)

PREFERENCE_ANALYSIS_PROMPT = (
    "Analyze this user message for communication preferences. "
    "Return a JSON with: language (e.g. 'en', 'hi', 'hinglish'), "
    "tone (e.g. 'formal', 'casual', 'technical'), "
    "style (e.g. 'concise', 'detailed', 'conversational'), "
    "topics (array of relevant topic keywords). "
    "If unsure, use empty string for strings and empty array for topics. "
    "Return ONLY valid JSON."
)


class MemoryManager:
    def __init__(self, db: Database, llm: LLMClient | None = None, enabled: bool = True, max_facts: int = 50) -> None:
        self.db = db
        self.llm = llm
        self.enabled = enabled
        self.max_facts = max_facts

    async def get_user_context(self, user_id: int) -> str:
        if not self.enabled:
            return ""
        parts: list[str] = []

        memory = await self.db.get_user_memory(user_id)
        if memory:
            mem_lines = [f"- {k}: {v}" for k, v in memory.items()]
            parts.append("Known facts about this user:\n" + "\n".join(mem_lines))

        prefs = await self.db.get_user_preferences(user_id)
        pref_parts = []
        if prefs.get("preferred_language"):
            pref_parts.append(f"language: {prefs['preferred_language']}")
        if prefs.get("preferred_tone"):
            pref_parts.append(f"tone: {prefs['preferred_tone']}")
        if prefs.get("communication_style"):
            pref_parts.append(f"style: {prefs['communication_style']}")
        if pref_parts:
            parts.append("User communication preferences: " + "; ".join(pref_parts))

        return "\n\n".join(parts)

    def set_llm(self, llm: LLMClient) -> None:
        self.llm = llm

    async def store_message(
        self, user_id: int, guild_id: int, channel_id: int, role: str, content: str
    ) -> None:
        await self.db.add_message(guild_id, channel_id, user_id, role, content)
        if not self.enabled or role != "user":
            return

        await self._ai_extract_and_store(user_id, content)

        message_count = await self.db.upsert_message_count(user_id, guild_id, channel_id)
        if message_count >= SUMMARIZE_TRIGGER_COUNT:
            await self._summarize_conversation(user_id, guild_id, channel_id)

    async def _ai_extract_and_store(self, user_id: int, text: str) -> None:
        if not self.llm:
            return
        try:
            facts_json = await self.llm.chat(
                [
                    {"role": "system", "content": AI_EXTRACT_PROMPT},
                    {"role": "user", "content": text[:2000]},
                ],
                temperature=0.1,
                max_tokens=300,
            )
            cleaned = facts_json.strip().removeprefix("```json").removesuffix("```").strip()
            facts = json.loads(cleaned)
            if not isinstance(facts, dict):
                return

            keywords = facts.pop("keywords", [])
            if isinstance(keywords, list):
                keyword_str = ", ".join(str(k)[:50] for k in keywords[:10])
            else:
                keyword_str = ""

            for key, value in facts.items():
                if isinstance(value, str) and value.strip() and len(value) > 2:
                    existing = await self.db.get_user_memory(user_id)
                    if len(existing) >= self.max_facts:
                        break
                    await self.db.set_user_memory(user_id, key[:50], value[:1000])
                    if keyword_str:
                        await self.db.store_semantic_memory(
                            user_id, key[:50], value[:500], keyword_str
                        )

            if not facts and keyword_str:
                await self.db.store_semantic_memory(
                    user_id, "context", text[:500], keyword_str
                )

            await self._analyze_preferences(user_id, text)
        except Exception as exc:
            logger.debug("AI extraction failed (non-critical): %s", exc)

    async def _analyze_preferences(self, user_id: int, text: str) -> None:
        if not self.llm:
            return
        try:
            prefs_json = await self.llm.chat(
                [
                    {"role": "system", "content": PREFERENCE_ANALYSIS_PROMPT},
                    {"role": "user", "content": text[:1500]},
                ],
                temperature=0.1,
                max_tokens=200,
            )
            cleaned = prefs_json.strip().removeprefix("```json").removesuffix("```").strip()
            prefs = json.loads(cleaned)
            if not isinstance(prefs, dict):
                return

            lang = str(prefs.get("language", "")).strip()
            tone = str(prefs.get("tone", "")).strip()
            style = str(prefs.get("style", "")).strip()
            topics = prefs.get("topics", [])
            if isinstance(topics, list) and all(isinstance(t, str) for t in topics):
                pass
            else:
                topics = []

            if lang or tone or style or topics:
                await self.db.set_user_preferences(user_id, lang, tone, style, topics)
        except Exception as exc:
            logger.debug("Preference analysis failed (non-critical): %s", exc)

    async def _summarize_conversation(self, user_id: int, guild_id: int, channel_id: int) -> None:
        if not self.llm:
            return
        try:
            history = await self.db.get_recent_messages(guild_id, channel_id, limit=SUMMARIZE_TRIGGER_COUNT)
            if not history:
                return

            conversation_text = "\n".join(
                f"{m['role']}: {m['content'][:500]}" for m in history
            )
            summary = await self.llm.chat(
                [
                    {"role": "system", "content": SUMMARIZE_PROMPT},
                    {"role": "user", "content": f"Conversation:\n{conversation_text}"},
                ],
                temperature=0.3,
                max_tokens=200,
            )
            summary = summary.strip()
            if summary:
                await self.db.store_summary(user_id, guild_id, channel_id, summary, SUMMARIZE_TRIGGER_COUNT)
                await self.db.reset_message_count(user_id, guild_id, channel_id)
                logger.info("Stored conversation summary for user %s", user_id)
        except Exception as exc:
            logger.debug("Summarization failed (non-critical): %s", exc)

    async def get_semantic_context(self, user_id: int, current_message: str = "") -> str:
        if not self.enabled:
            return ""

        summary = await self.db.get_latest_summary(user_id, 0, 0)
        semantic_parts: list[str] = []

        if summary:
            semantic_parts.append(f"Conversation summary: {summary}")

        if current_message and self.llm:
            try:
                kw_json = await self.llm.chat(
                    [
                        {
                            "role": "system",
                            "content": "Extract 2-5 key search terms from this message. Return as JSON array of strings. Return ONLY valid JSON.",
                        },
                        {"role": "user", "content": current_message[:1000]},
                    ],
                    temperature=0.1,
                    max_tokens=100,
                )
                cleaned = kw_json.strip().removeprefix("```json").removesuffix("```").strip()
                terms = json.loads(cleaned)
                if isinstance(terms, list):
                    search_terms = [str(t) for t in terms[:5]]
                    relevant = await self.db.search_semantic_memory(user_id, search_terms)
                    if relevant:
                        lines = []
                        for mem in relevant[:3]:
                            lines.append(f"- {mem['category']}: {mem['content']}")
                        semantic_parts.append("Relevant memories:\n" + "\n".join(lines))
            except Exception:
                pass

        return "\n\n".join(semantic_parts)

    async def clear_user_memory(self, user_id: int) -> None:
        existing = await self.db.get_user_memory(user_id)
        for key in existing:
            await self.db.delete_user_memory(user_id, key)

    async def get_recent_with_memory(
        self, user_id: int, guild_id: int, channel_id: int, limit: int = 8
    ) -> str:
        history = await self.db.get_recent_messages(guild_id, channel_id, limit=limit)
        memory_ctx = await self.get_user_context(user_id)
        if not history and not memory_ctx:
            return ""
        parts: list[str] = []
        if memory_ctx:
            parts.append(memory_ctx)
        parts.append("Recent conversation:")
        for msg in history:
            parts.append(f"{msg['role']}: {msg['content']}")
        return "\n".join(parts)
