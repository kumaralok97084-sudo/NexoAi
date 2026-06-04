from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path

import discord
from discord.app_commands import CommandTree
from discord.ext import commands, tasks


class UnlimitedTree(CommandTree):
    def add_command(self, command, /, *, guild=None, guilds=None, override=False):
        import discord.app_commands as ac
        from discord.utils import MISSING
        has_guild = guild is not None and guild is not MISSING
        has_guilds = guilds is not None and guilds is not MISSING
        if has_guild or has_guilds:
            gids = [guild.id] if has_guild else [s.id for s in guilds]
            return self._add_guild_command(command, gids, override)
        return self._add_global_command(command, override)

    def _add_guild_command(self, command, gids, override):
        import discord.app_commands as ac
        if isinstance(command, ac.ContextMenu):
            return super().add_command(command, guild=discord.Object(id=gids[0]), override=override)
        if not isinstance(command, (ac.Command, ac.Group)):
            raise TypeError(f"Expected Command or Group, got {command.__class__.__name__}")
        root = command.root_parent or command
        name = root.name
        for gid in gids:
            cmds = self._guild_commands.setdefault(gid, {})
            if name in cmds and not override:
                raise ac.CommandAlreadyRegistered(name, gid)
            cmds[name] = root

    def _add_global_command(self, command, override):
        import discord.app_commands as ac
        if isinstance(command, ac.ContextMenu):
            return super().add_command(command, override=override)
        if not isinstance(command, (ac.Command, ac.Group)):
            raise TypeError(f"Expected Command or Group, got {command.__class__.__name__}")
        root = command.root_parent or command
        name = root.name
        if name in self._global_commands and not override:
            raise ac.CommandAlreadyRegistered(name, None)
        self._global_commands[name] = root

    def copy_global_to(self, *, guild):
        mapping = self._guild_commands.get(guild.id, {}).copy()
        mapping.update(self._global_commands)
        self._guild_commands[guild.id] = mapping

from config import PRESENCE_TYPES, load_settings
from database import Database
from file_ingest import ingest_attachments
from llm_client import LLMClient
from memory_manager import MemoryManager
from search_client import SearchClient
from image_gen import ImageGenerator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)

settings = load_settings()
database = Database(settings.database_path)
llm = LLMClient(
    openrouter_api_key=settings.openrouter_api_key,
    openrouter_model=settings.openrouter_model,
    groq_api_key=settings.groq_api_key,
    groq_model=settings.groq_model,
    cerebras_api_key=settings.cerebras_api_key,
    cerebras_model=settings.cerebras_model,
    nvidia_api_key=settings.nvidia_api_key,
    nvidia_model=settings.nvidia_model,
    vllm_base_url=settings.vllm_base_url,
    vllm_api_key=settings.vllm_api_key,
    vllm_model=settings.vllm_model,
    fallback_order=settings.llm_fallback_order,
)
memory_mgr = MemoryManager(database, llm=llm, enabled=settings.memory_enabled, max_facts=settings.memory_max_facts)
search = SearchClient(api_key=settings.google_search_api_key, cse_id=settings.google_search_cse_id)
image_gen = ImageGenerator(
    api_key=settings.openrouter_api_key,
    model=settings.image_gen_model,
    provider=settings.image_gen_provider,
)
start_time = time.time()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix=settings.bot_prefix, intents=intents, tree_cls=UnlimitedTree)
bot.db = database  # type: ignore[attr-defined]
bot.llm = llm  # type: ignore[attr-defined]
bot.memory = memory_mgr  # type: ignore[attr-defined]
bot.search = search  # type: ignore[attr-defined]
bot.image_gen = image_gen  # type: ignore[attr-defined]
bot.settings = settings  # type: ignore[attr-defined]
bot.start_time = start_time  # type: ignore[attr-defined]
bot.status_index = 0  # type: ignore[attr-defined]


@bot.event
async def on_ready() -> None:
    await set_presence_from_config()
    if settings.rotating_statuses and not rotate_status.is_running():
        rotate_status.start()
    logging.info("Logged in as %s (%s)", bot.user, bot.user.id if bot.user else "n/a")
    guilds = bot.guilds
    if guilds:
        for g in guilds[:1]:
            try:
                bot.tree.copy_global_to(guild=g)
                synced = await bot.tree.sync(guild=g)
                logging.info("Synced %d slash commands to guild %s.", len(synced), g.name)
            except Exception as e:
                logging.warning("Per-guild sync failed: %s", e)
    else:
        synced = await bot.tree.sync()
        logging.info("Synced %d slash commands globally.", len(synced))


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError) -> None:
    logging.error("Command %s error: %s", interaction.command, error, exc_info=True)
    if not interaction.response.is_done():
        try:
            await interaction.response.send_message(f"Error: {error}", ephemeral=True)
        except Exception as exc2:
            logging.error("Failed to send error response: %s", exc2)
    else:
        try:
            await interaction.followup.send(f"Error: {error}", ephemeral=True)
        except Exception as exc2:
            logging.error("Failed to send followup error: %s", exc2)


@bot.listen()
async def on_interaction(interaction: discord.Interaction) -> None:
    if interaction.type == discord.InteractionType.application_command:
        logging.info("Interaction: cmd=%s id=%s guild=%s user=%s",
                     interaction.command, interaction.id, interaction.guild_id, interaction.user.id)





@bot.event
async def setup_hook() -> None:
    await bot.db.init()
    await bot.db.init_stocks()

    for extension in (
        "cogs.ai", "cogs.admin", "cogs.general", "cogs.moderation", "cogs.moderation_ext",
        "cogs.hosting", "cogs.utility",
        "cogs.economy",
        "cogs.utility_ext",
        "cogs.features_ext",
    ):
        await bot.load_extension(extension)
        logging.info("Loaded extension: %s", extension)
    if not cleanup_old_data.is_running():
        cleanup_old_data.start()
    if not check_reminders.is_running():
        check_reminders.start()


@bot.event
async def on_member_join(member: discord.Member) -> None:
    guild = member.guild
    welcome_channel_id = await bot.db.get_guild_setting(guild.id, "welcome_channel")
    welcome_message = await bot.db.get_guild_setting(guild.id, "welcome_message")
    autorole_id = await bot.db.get_guild_setting(guild.id, "autorole_id")

    if autorole_id:
        try:
            role = guild.get_role(int(autorole_id))
            if role and role < guild.me.top_role:
                await member.add_roles(role, reason="Auto-role on join")
        except (discord.Forbidden, discord.HTTPException, ValueError):
            pass

    if welcome_channel_id and welcome_message:
        channel = guild.get_channel(int(welcome_channel_id))
        if isinstance(channel, discord.TextChannel):
            try:
                msg = str(welcome_message).replace("{user}", member.mention)
                msg = msg.replace("{username}", str(member))
                msg = msg.replace("{server}", guild.name)
                msg = msg.replace("{count}", str(guild.member_count))
                await channel.send(msg)
            except discord.Forbidden:
                pass


@bot.event
async def on_member_remove(member: discord.Member) -> None:
    guild = member.guild
    leave_channel_id = await bot.db.get_guild_setting(guild.id, "leave_channel")
    leave_message = await bot.db.get_guild_setting(guild.id, "leave_message")

    if leave_channel_id and leave_message:
        channel = guild.get_channel(int(leave_channel_id))
        if isinstance(channel, discord.TextChannel):
            try:
                msg = str(leave_message).replace("{user}", member.mention)
                msg = msg.replace("{username}", str(member))
                msg = msg.replace("{server}", guild.name)
                msg = msg.replace("{count}", str(guild.member_count))
                await channel.send(msg)
            except discord.Forbidden:
                pass


@bot.command(name="sync")
@commands.is_owner()
async def sync_commands(ctx: commands.Context) -> None:
    synced = await bot.tree.sync()
    await ctx.send(f"Synced {len(synced)} commands.")


@bot.event
async def on_message(message: discord.Message) -> None:
    if message.author.bot:
        return

    is_dm = message.guild is None

    if not is_dm and bot.settings.moderation_enabled:
        mod_cog = bot.get_cog("ModerationCog")
        if mod_cog:
            await mod_cog.check_message(message)

    ai_channel_id = None
    auto_reply = None
    should_auto_reply = False

    if not is_dm and message.guild:
        ai_channel_id = await bot.db.get_guild_setting(message.guild.id, "ai_channel_id")  # type: ignore[attr-defined]
        auto_reply = await bot.db.get_guild_setting(message.guild.id, "auto_reply_enabled")  # type: ignore[attr-defined]
        should_auto_reply = (
            bool(auto_reply) and ai_channel_id and message.channel.id == int(ai_channel_id)
        )

    mentioned = bot.user and bot.user in message.mentions
    text_prefix_prompt = _extract_text_prefix_prompt(message.content, bot.settings.mention_prefixes)  # type: ignore[attr-defined]

    if is_dm:
        await handle_auto_ai_reply(message)
    elif text_prefix_prompt is not None:
        if not text_prefix_prompt.strip():
            await message.reply("Usage: `@nexoai your question here`")
        else:
            await handle_auto_ai_reply(message, prompt_override=text_prefix_prompt)
    elif should_auto_reply or mentioned:
        await handle_auto_ai_reply(message)

    await bot.process_commands(message)


def _extract_text_prefix_prompt(content: str, prefixes: list[str]) -> str | None:
    lowered = content.lstrip()
    lowered_cmp = lowered.lower()
    for prefix in prefixes:
        p = str(prefix).strip()
        if not p:
            continue
        p_cmp = p.lower()
        if lowered_cmp == p_cmp:
            return ""
        if lowered_cmp.startswith(p_cmp + " "):
            return lowered[len(p) + 1 :].lstrip()
    return None


async def build_system_prompt(
    user_id: int, guild_id: int, guild: discord.Guild | None,
    user_text: str = "",
) -> str:
    guild_prompt = None
    if guild:
        guild_prompt = await bot.db.get_guild_setting(guild.id, "system_prompt")  # type: ignore[attr-defined]
    system_prompt = guild_prompt or bot.settings.default_system_prompt  # type: ignore[attr-defined]

    profile = await bot.db.get_user_profile(user_id)  # type: ignore[attr-defined]
    persona = profile.get("persona", "").strip()
    if persona:
        system_prompt += f"\nUser persona preference: {persona}"

    memory_ctx = await bot.memory.get_user_context(user_id)  # type: ignore[attr-defined]
    if memory_ctx:
        system_prompt += f"\n\n{memory_ctx}"

    semantic_ctx = await bot.memory.get_semantic_context(user_id, user_text)  # type: ignore[attr-defined]
    if semantic_ctx:
        system_prompt += f"\n\n{semantic_ctx}"

    return system_prompt


async def handle_auto_ai_reply(message: discord.Message, prompt_override: str | None = None) -> None:
    async with message.channel.typing():
        guild_id = message.guild.id if message.guild else 0
        system_prompt = await build_system_prompt(
            message.author.id, guild_id, message.guild, message.content
        )

        history = await bot.db.get_recent_messages(  # type: ignore[attr-defined]
            guild_id, message.channel.id, limit=bot.settings.history_limit
        )

        attachment_context = ""
        if message.attachments:
            storage_root = Path("storage") / "uploads" / str(message.author.id) / str(message.channel.id)
            snippets, stored_paths = await ingest_attachments(message.attachments, storage_root)
            for attachment, path in zip(message.attachments, stored_paths):
                await bot.db.add_file_record(  # type: ignore[attr-defined]
                    guild_id,
                    message.channel.id,
                    message.author.id,
                    attachment.filename,
                    path.as_posix(),
                )
            if snippets:
                attachment_context = (
                    "\n\nAttached file content/context:\n" + "\n\n".join(snippets[:8])
                )

        messages = [{"role": "system", "content": system_prompt}, *history]
        user_content = prompt_override if prompt_override is not None else message.content
        if not user_content.strip() and message.attachments:
            user_content = "Please analyze the attached file(s)."
        user_content = user_content + attachment_context
        messages.append({"role": "user", "content": user_content})

        try:
            response = await bot.llm.chat(  # type: ignore[attr-defined]
                messages,
                temperature=bot.settings.openrouter_temperature,
                max_tokens=bot.settings.openrouter_max_tokens,
            )
            await bot.memory.store_message(  # type: ignore[attr-defined]
                message.author.id, guild_id, message.channel.id, "user", user_content
            )
            await bot.memory.store_message(  # type: ignore[attr-defined]
                message.author.id, guild_id, message.channel.id, "assistant", response
            )
            await send_chunked(message.channel, response)
        except RuntimeError as exc:
            error_text = str(exc)
            if "All providers failed" in error_text:
                await message.reply("All AI providers are currently unavailable. Please try again later.")
            else:
                await message.reply(f"AI request failed: `{error_text[:500]}`")
        except Exception as exc:
            await message.reply(f"Something went wrong. Please try again in a moment.")


async def send_chunked(channel: discord.abc.Messageable, text: str) -> None:
    if not text.strip():
        await channel.send("(empty response)")
        return

    lines = text.split("\n")
    chunks: list[str] = []
    current = ""
    in_code_block = False

    for line in lines:
        if line.startswith("```"):
            in_code_block = not in_code_block

        candidate = current + ("\n" if current else "") + line
        if len(candidate) > 1800:
            if current:
                chunks.append(current)
            current = line
        else:
            current = candidate

    if current:
        chunks.append(current)

    if not chunks:
        chunks = ["(empty response)"]

    first = True
    for chunk in chunks:
        if first:
            embed = discord.Embed(
                title="NexoAI",
                description=chunk[:4096],
                color=discord.Color.blurple(),
            )
            await channel.send(embed=embed)
            first = False
        else:
            await channel.send(chunk)


async def set_presence_from_config() -> None:
    presence_key = settings.presence_type
    activity_type = PRESENCE_TYPES.get(presence_key, discord.ActivityType.watching)
    if activity_type == discord.ActivityType.custom:
        activity = discord.CustomActivity(name=settings.presence_text)
    else:
        activity = discord.Activity(type=activity_type, name=settings.presence_text)
    await bot.change_presence(activity=activity)


@tasks.loop(seconds=20)
async def rotate_status() -> None:
    statuses = settings.rotating_statuses
    if not statuses:
        return
    idx = bot.status_index % len(statuses)  # type: ignore[attr-defined]
    status_type, text = statuses[idx]
    activity_type = PRESENCE_TYPES.get(status_type, discord.ActivityType.watching)
    if activity_type == discord.ActivityType.custom:
        activity = discord.CustomActivity(name=text)
    else:
        activity = discord.Activity(type=activity_type, name=text)
    await bot.change_presence(activity=activity)
    bot.status_index += 1  # type: ignore[attr-defined]


@tasks.loop(hours=6)
async def cleanup_old_data() -> None:
    counts = await bot.db.cleanup_old_data(days=30)  # type: ignore[attr-defined]
    total = sum(counts.values())
    if total:
        logging.info("Cleaned %d old records: %s", total, counts)


@tasks.loop(minutes=1)
async def check_reminders() -> None:
    reminders = await bot.db.get_due_reminders()  # type: ignore[attr-defined]
    for r in reminders:
        try:
            channel = bot.get_channel(r["channel_id"]) or await bot.fetch_channel(r["channel_id"])
            if isinstance(channel, discord.abc.Messageable):
                user = bot.get_user(r["user_id"])
                mention = user.mention if user else f"<@{r['user_id']}>"
                await channel.send(f"⏰ {mention} Reminder: {r['message']}")
            await bot.db.delete_reminder(r["id"])  # type: ignore[attr-defined]
        except Exception:
            try:
                await bot.db.delete_reminder(r["id"])  # type: ignore[attr-defined]
            except Exception:
                pass


@rotate_status.before_loop
async def before_rotate_status() -> None:
    await bot.wait_until_ready()


def main() -> None:
    if not settings.discord_token:
        raise RuntimeError("discord.token is missing in config.yaml.")
    has_cloud = any((
        settings.groq_api_key,
        settings.openrouter_api_key,
        settings.cerebras_api_key,
        settings.nvidia_api_key,
    ))
    has_vllm = bool(settings.vllm_base_url and settings.vllm_api_key and settings.vllm_model)
    if not has_cloud and not has_vllm:
        raise RuntimeError(
            "No AI provider configured. Add at least one cloud key (groq/openrouter/cerebras/nvidia) "
            "or configure vllm in config.yaml."
        )
    bot.run(settings.discord_token)


if __name__ == "__main__":
    main()
