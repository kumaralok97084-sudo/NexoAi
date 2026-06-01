from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import aiosqlite
import discord
from discord import app_commands
from discord.ext import commands

ANTISPAM_LIMIT = 5
ANTISPAM_WINDOW = 10
ANTISPAM_MUTE_MINUTES = 5


class ModerationExtCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._spam_tracker: dict[int, list[float]] = {}
        self._tempban_task: asyncio.Task | None = None

    async def cog_load(self) -> None:
        self._tempban_task = asyncio.create_task(self._check_temp_bans())

    async def cog_unload(self) -> None:
        if self._tempban_task:
            self._tempban_task.cancel()

    # ---- Anti-Spam ----

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or not message.guild:
            return

        guild_id = message.guild.id
        antispam_enabled = await self.bot.db.get_guild_setting(guild_id, "antispam_enabled")
        if not antispam_enabled or antispam_enabled != "1":
            return

        now = message.created_at.timestamp()
        key = message.author.id
        if key not in self._spam_tracker:
            self._spam_tracker[key] = []

        self._spam_tracker[key].append(now)
        self._spam_tracker[key] = [t for t in self._spam_tracker[key] if now - t < ANTISPAM_WINDOW]

        if len(self._spam_tracker[key]) > ANTISPAM_LIMIT:
            if isinstance(message.author, discord.Member):
                try:
                    until = discord.utils.utcnow() + timedelta(minutes=ANTISPAM_MUTE_MINUTES)
                    await message.author.timeout(until, reason=f"Anti-spam: {ANTISPAM_LIMIT}+ msgs in {ANTISPAM_WINDOW}s")
                    await self.bot.db.add_moderation_log(
                        guild_id, message.author.id, "antispam_mute",
                        f"Auto-muted for spamming ({ANTISPAM_LIMIT}+ messages in {ANTISPAM_WINDOW}s)", "",
                    )
                    await message.channel.send(
                        f"{message.author.mention} muted for **{ANTISPAM_MUTE_MINUTES}min** (spam).",
                        delete_after=10,
                    )
                except discord.Forbidden:
                    pass
            self._spam_tracker[key] = []

    # ---- Message Logs ----

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message) -> None:
        if message.author.bot or not message.guild:
            return
        await self._log_message_event(message.guild.id, message.channel.id, message.author.id, "delete", message.content)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> None:
        if after.author.bot or not after.guild:
            return
        if before.content != after.content:
            await self._log_message_event(
                after.guild.id, after.channel.id, after.author.id, "edit",
                f"Before: {before.content[:500]}\nAfter: {after.content[:500]}",
            )

    async def _log_message_event(self, guild_id: int, channel_id: int, user_id: int, action: str, content: str | None) -> None:
        async with aiosqlite.connect(self.bot.db.db_path) as db:
            await db.execute(
                "INSERT INTO message_logs (guild_id, channel_id, user_id, action, content) VALUES (?, ?, ?, ?, ?)",
                (guild_id, channel_id, user_id, action, (content or "")[:1000]),
            )
            await db.commit()

    @app_commands.command(name="messagelogs", description="Show recent message logs for a user.")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def message_logs(self, interaction: discord.Interaction, user: discord.User, limit: app_commands.Range[int, 1, 20] = 10) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Server only.", ephemeral=True)
            return
        async with aiosqlite.connect(self.bot.db.db_path) as db:
            async with db.execute(
                "SELECT action, content, created_at FROM message_logs WHERE guild_id = ? AND user_id = ? ORDER BY id DESC LIMIT ?",
                (interaction.guild.id, user.id, limit),
            ) as cursor:
                rows = await cursor.fetchall()

        if not rows:
            await interaction.response.send_message(f"No logs for {user.mention}.", ephemeral=True)
            return

        lines = [f"`{r[2]}` **{r[0]}** — {r[1][:100]}" for r in rows]
        embed = discord.Embed(
            title=f"Message Logs for {user.display_name}",
            description="\n".join(lines),
            color=discord.Color.orange(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ---- Temp-Ban ----

    async def _check_temp_bans(self) -> None:
        while True:
            try:
                await asyncio.sleep(60)
                async with aiosqlite.connect(self.bot.db.db_path) as db:
                    async with db.execute(
                        "SELECT id, guild_id, user_id FROM temp_bans WHERE ends_at <= datetime('now')"
                    ) as cursor:
                        rows = await cursor.fetchall()
                    for tid, guild_id, user_id in rows:
                        guild = self.bot.get_guild(guild_id)
                        if guild:
                            try:
                                user = await self.bot.fetch_user(user_id)
                                await guild.unban(user, reason="Temp-ban expired")
                                await self.bot.db.add_moderation_log(
                                    guild_id, user_id, "unban", "Temp-ban expired", "",
                                )
                            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                                pass
                        await db.execute("DELETE FROM temp_bans WHERE id = ?", (tid,))
                    await db.commit()
            except asyncio.CancelledError:
                break
            except Exception:
                pass

    @app_commands.command(name="tempban", description="Temporarily ban a user.")
    @app_commands.checks.has_permissions(ban_members=True)
    @app_commands.describe(
        user="User to ban",
        duration="Duration in minutes",
        reason="Reason for the ban",
    )
    async def tempban(
        self, interaction: discord.Interaction,
        user: discord.User,
        duration: app_commands.Range[int, 1, 10080],
        reason: str = "No reason provided",
    ) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Server only.", ephemeral=True)
            return

        if isinstance(user, discord.Member):
            if user.top_role >= interaction.user.top_role and interaction.user.id != interaction.guild.owner_id:
                await interaction.response.send_message("You cannot ban this member.", ephemeral=True)
                return

        ends_at = (datetime.now(timezone.utc) + timedelta(minutes=duration)).isoformat()

        try:
            await interaction.guild.ban(user, reason=f"Temp-ban: {reason}")
        except discord.Forbidden:
            await interaction.response.send_message("I don't have permission to ban that user.", ephemeral=True)
            return
        except Exception as exc:
            await interaction.response.send_message(f"Failed: {exc}", ephemeral=True)
            return

        async with aiosqlite.connect(self.bot.db.db_path) as db:
            await db.execute(
                "INSERT INTO temp_bans (guild_id, user_id, ends_at, reason) VALUES (?, ?, ?, ?)",
                (interaction.guild.id, user.id, ends_at, reason[:500]),
            )
            await db.commit()

        await self.bot.db.add_moderation_log(
            interaction.guild.id, user.id, "tempban", reason, f"Duration: {duration}min",
        )
        await interaction.response.send_message(
            f"{user} has been banned for **{duration}** minute(s). Reason: {reason}"
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ModerationExtCog(bot))
