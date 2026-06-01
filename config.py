from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import discord
import yaml

DEFAULT_CONFIG_PATH = Path("config.yaml")

PRESENCE_TYPES = {
    "playing": discord.ActivityType.playing,
    "streaming": discord.ActivityType.streaming,
    "listening": discord.ActivityType.listening,
    "watching": discord.ActivityType.watching,
    "competing": discord.ActivityType.competing,
    "custom": discord.ActivityType.custom,
}


@dataclass(slots=True)
class Settings:
    discord_token: str
    openrouter_api_key: str
    openrouter_model: str
    openrouter_temperature: float
    openrouter_max_tokens: int
    groq_api_key: str
    groq_model: str
    cerebras_api_key: str
    cerebras_model: str
    nvidia_api_key: str
    nvidia_model: str
    llm_fallback_order: list[str]
    bot_prefix: str
    owner_ids: set[int]
    default_system_prompt: str
    database_path: str
    history_limit: int
    mention_prefixes: list[str]
    presence_type: str
    presence_text: str
    rotating_statuses: list[tuple[str, str]]
    google_search_api_key: str
    google_search_cse_id: str
    vllm_base_url: str
    vllm_api_key: str
    vllm_model: str
    pollinations_api_key: str
    pollinations_model: str
    pollinations_base_url: str
    image_gen_provider: str
    image_gen_model: str
    memory_enabled: bool
    memory_max_facts: int
    moderation_enabled: bool
    moderation_max_warns: int
    moderation_timeout_minutes: int


def _section(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key, {})
    return value if isinstance(value, dict) else {}


def _parse_owner_ids(raw: Any) -> set[int]:
    if raw is None:
        return set()
    if isinstance(raw, int):
        return {raw}
    if isinstance(raw, str):
        raw = [part.strip() for part in raw.split(",")]
    if not isinstance(raw, list):
        return set()
    owner_ids: set[int] = set()
    for item in raw:
        if isinstance(item, int):
            owner_ids.add(item)
        elif isinstance(item, str) and item.isdigit():
            owner_ids.add(int(item))
    return owner_ids


def load_settings(path: Path | str = DEFAULT_CONFIG_PATH) -> Settings:
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(
            f"Missing {config_path}. Copy config.yaml.example to config.yaml and fill in your values."
        )

    with config_path.open(encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}

    discord_cfg = _section(data, "discord")
    openrouter_cfg = _section(data, "openrouter")
    groq_cfg = _section(data, "groq")
    cerebras_cfg = _section(data, "cerebras")
    nvidia_cfg = _section(data, "nvidia")
    llm_cfg = _section(data, "llm")
    bot_cfg = _section(data, "bot")
    presence_cfg = _section(bot_cfg, "presence")
    rotating_statuses_raw = bot_cfg.get("rotating_statuses", [])
    mention_prefixes_raw = bot_cfg.get("mention_prefixes", ["@nexoai"])
    if isinstance(mention_prefixes_raw, str):
        mention_prefixes = [mention_prefixes_raw]
    elif isinstance(mention_prefixes_raw, list):
        mention_prefixes = [str(x) for x in mention_prefixes_raw if str(x).strip()]
    else:
        mention_prefixes = ["@nexoai"]

    rotating_statuses: list[tuple[str, str]] = []
    if isinstance(rotating_statuses_raw, list):
        for item in rotating_statuses_raw:
            if not isinstance(item, dict):
                continue
            status_type = str(item.get("type", "")).strip().lower()
            status_text = str(item.get("text", "")).strip()
            if status_type and status_text:
                rotating_statuses.append((status_type, status_text))

    fallback_raw = llm_cfg.get(
        "fallback_order", ["groq", "openrouter", "cerebras"]
    )
    if isinstance(fallback_raw, str):
        llm_fallback_order = [fallback_raw.strip().lower()]
    elif isinstance(fallback_raw, list):
        llm_fallback_order = [
            str(item).strip().lower() for item in fallback_raw if str(item).strip()
        ]
    else:
        llm_fallback_order = ["groq", "openrouter", "cerebras"]

    search_cfg = _section(data, "google_search")
    vllm_cfg = _section(data, "vllm")
    pollinations_cfg = _section(data, "pollinations")
    image_gen_cfg = _section(data, "image_generation")
    memory_cfg = _section(bot_cfg, "memory")
    moderation_cfg = _section(data, "moderation")

    return Settings(
        discord_token=str(discord_cfg.get("token", "")).strip(),
        openrouter_api_key=str(openrouter_cfg.get("api_key", "")).strip(),
        openrouter_model=str(openrouter_cfg.get("model", "openai/gpt-4o-mini")),
        openrouter_temperature=float(openrouter_cfg.get("temperature", 0.7)),
        openrouter_max_tokens=int(openrouter_cfg.get("max_tokens", 800)),
        groq_api_key=str(groq_cfg.get("api_key", "")).strip(),
        groq_model=str(groq_cfg.get("model", "groq/llama-3.1-8b-instant")).strip(),
        cerebras_api_key=str(cerebras_cfg.get("api_key", "")).strip(),
        cerebras_model=str(
            cerebras_cfg.get("model", "cerebras/llama3.1-8b")
        ).strip(),
        nvidia_api_key=str(nvidia_cfg.get("api_key", "")).strip(),
        nvidia_model=str(
            nvidia_cfg.get("model", "nvidia/llama-3.1-nemotron-70b-instruct")
        ).strip(),
        llm_fallback_order=llm_fallback_order,
        bot_prefix=str(discord_cfg.get("prefix", "!")),
        owner_ids=_parse_owner_ids(discord_cfg.get("owner_ids")),
        default_system_prompt=str(
            bot_cfg.get(
                "default_system_prompt",
                "You are NexoAI, a helpful and practical hosting assistant on Discord.",
            )
        ).strip(),
        database_path=str(bot_cfg.get("database_path", "nexoai.db")),
        history_limit=int(bot_cfg.get("history_limit", 16)),
        mention_prefixes=mention_prefixes,
        presence_type=str(presence_cfg.get("type", "watching")).lower(),
        presence_text=str(presence_cfg.get("text", "hosting support | /helpme")),
        rotating_statuses=rotating_statuses,
        google_search_api_key=str(search_cfg.get("api_key", "")).strip(),
        google_search_cse_id=str(search_cfg.get("cse_id", "")).strip(),
        vllm_base_url=str(vllm_cfg.get("base_url", "")).strip(),
        vllm_api_key=str(vllm_cfg.get("api_key", "")).strip(),
        vllm_model=str(vllm_cfg.get("model", "")).strip(),
        pollinations_api_key=str(pollinations_cfg.get("api_key", "")).strip(),
        pollinations_model=str(pollinations_cfg.get("model", "openai/gpt-4o-mini")).strip(),
        pollinations_base_url=str(pollinations_cfg.get("base_url", "https://text.pollinations.ai/openai")).strip(),
        image_gen_provider=str(image_gen_cfg.get("provider", "openrouter")).strip(),
        image_gen_model=str(image_gen_cfg.get("model", "stabilityai/stable-diffusion-3.5-large-turbo")).strip(),
        memory_enabled=bool(memory_cfg.get("enabled", True)),
        memory_max_facts=int(memory_cfg.get("max_facts_per_user", 50)),
        moderation_enabled=bool(moderation_cfg.get("enabled", True)),
        moderation_max_warns=int(moderation_cfg.get("max_warns", 3)),
        moderation_timeout_minutes=int(moderation_cfg.get("timeout_minutes", 10)),
    )
