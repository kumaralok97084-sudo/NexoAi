from __future__ import annotations

import asyncio
import json
import random
from datetime import datetime, timedelta, timezone

import aiosqlite
import discord
from discord import app_commands
from discord.ext import commands


from cogs.emojis import CHECK_OK, DOWNVOTE, GIVEAWAY, NOTE_SAVE, SUGGESTION, UPVOTE

class ServerMgmtCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._giveaway_task: asyncio.Task | None = None

    async def cog_load(self) -> None:
        self._giveaway_task = asyncio.create_task(self._check_giveaways())

    async def cog_unload(self) -> None:
        if self._giveaway_task:
            self._giveaway_task.cancel()

    async def _check_giveaways(self) -> None:
        while True:
            try:
                await asyncio.sleep(30)
                async with aiosqlite.connect(self.bot.db.db_path) as db:
                    async with db.execute(
                        "SELECT id, guild_id, channel_id, message_id, prize, winners FROM giveaways "
                        "WHERE ended = 0 AND ends_at <= datetime('now')"
                    ) as cursor:
                        rows = await cursor.fetchall()
                    for row in rows:
                        gid, guild_id, channel_id, msg_id, prize, winners_count = row
                        await self._end_giveaway(gid, guild_id, channel_id, prize, winners_count)
                        await db.execute("UPDATE giveaways SET ended = 1 WHERE id = ?", (gid,))
                    await db.commit()
            except asyncio.CancelledError:
                break
            except Exception:
                pass

    async def _end_giveaway(self, gid: int, guild_id: int, channel_id: int, prize: str, winners_count: int) -> None:
        guild = self.bot.get_guild(guild_id)
        channel = guild.get_channel(channel_id) if guild else None
        if not channel:
            return

        async with aiosqlite.connect(self.bot.db.db_path) as db2:
            async with db2.execute(
                "SELECT user_id FROM giveaway_entries WHERE giveaway_id = ?", (gid,)
            ) as cursor:
                entries = [row[0] for row in await cursor.fetchall()]

        if not entries:
            await channel.send(f"{GIVEAWAY} Giveaway for **{prize}** ended with no participants.")
            return

        winners = random.sample(entries, min(winners_count, len(entries)))
        mentions = ", ".join(f"<@{w}>" for w in winners)
        await channel.send(f"{GIVEAWAY} **Giveaway ended!** Winners of **{prize}**: {mentions}")

    # ---- Giveaways ----

    giveaway = app_commands.Group(name="giveaway", description="Manage giveaways.")

    @giveaway.command(name="start", description="Start a new giveaway.")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(
        prize="The prize to give away",
        duration="Duration in minutes",
        winners="Number of winners (default: 1)",
    )
    async def giveaway_start(
        self, interaction: discord.Interaction,
        prize: str, duration: app_commands.Range[int, 1, 10080],
        winners: app_commands.Range[int, 1, 10] = 1,
    ) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Server only.", ephemeral=True)
            return
        ends_at = (datetime.now(timezone.utc) + timedelta(minutes=duration)).strftime("%Y-%m-%d %H:%M:%S")

        embed = discord.Embed(
            title=f"{GIVEAWAY} Giveaway",
            description=f"**Prize:** {prize}\n**Winners:** {winners}\n**Ends:** <t:{int((datetime.now(timezone.utc) + timedelta(minutes=duration)).timestamp())}:R>",
            color=discord.Color.gold(),
        )
        embed.add_field(name="How to enter", value=f"Click the {GIVEAWAY} reaction below!", inline=False)
        embed.set_footer(text=f"Hosted by {interaction.user.display_name}")

        await interaction.response.send_message(embed=embed)
        msg = await interaction.original_response()
        await msg.add_reaction(f"{GIVEAWAY}")

        async with aiosqlite.connect(self.bot.db.db_path) as db:
            await db.execute(
                "INSERT INTO giveaways (guild_id, channel_id, message_id, prize, winners, ends_at, host_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (interaction.guild.id, interaction.channel_id, msg.id, prize[:200], winners, ends_at, interaction.user.id),
            )
            await db.commit()

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        if payload.user_id == self.bot.user.id:
            return
        if str(payload.emoji) != f"{GIVEAWAY}":
            return

        async with aiosqlite.connect(self.bot.db.db_path) as db:
            async with db.execute(
                "SELECT id FROM giveaways WHERE message_id = ? AND ended = 0", (payload.message_id,)
            ) as cursor:
                row = await cursor.fetchone()
            if not row:
                return
            try:
                await db.execute(
                    "INSERT OR IGNORE INTO giveaway_entries (giveaway_id, user_id) VALUES (?, ?)",
                    (row[0], payload.user_id),
                )
                await db.commit()
            except aiosqlite.IntegrityError:
                pass

    # ---- Suggestions ----

    @app_commands.command(name="suggest", description="Submit a suggestion.")
    async def suggest(self, interaction: discord.Interaction, suggestion: str) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Server only.", ephemeral=True)
            return

        async with aiosqlite.connect(self.bot.db.db_path) as db:
            async with db.execute(
                "SELECT channel_id FROM server_logging WHERE guild_id = ? AND log_channel_id IS NOT NULL",
                (interaction.guild.id,),
            ) as cursor:
                row = await cursor.fetchone()

        suggestion_channel = None
        if row:
            suggestion_channel = interaction.guild.get_channel(int(row[0]))

        embed = discord.Embed(
            title=f"{SUGGESTION} Suggestion",
            description=suggestion[:2000],
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow(),
        )
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        embed.add_field(name="Status", value="Pending", inline=True)

        if suggestion_channel:
            msg = await suggestion_channel.send(embed=embed)
            await msg.add_reaction(f"{UPVOTE}")
            await msg.add_reaction(f"{DOWNVOTE}")

            async with aiosqlite.connect(self.bot.db.db_path) as db:
                await db.execute(
                    "INSERT INTO suggestions (guild_id, channel_id, message_id, author_id, content) VALUES (?, ?, ?, ?, ?)",
                    (interaction.guild.id, suggestion_channel.id, msg.id, interaction.user.id, suggestion[:2000]),
                )
                await db.commit()

            await interaction.response.send_message(f"{CHECK_OK} Suggestion posted in {suggestion_channel.mention}.", ephemeral=True)
        else:
            async with aiosqlite.connect(self.bot.db.db_path) as db:
                await db.execute(
                    "INSERT INTO suggestions (guild_id, author_id, content) VALUES (?, ?, ?)",
                    (interaction.guild.id, interaction.user.id, suggestion[:2000]),
                )
                await db.commit()
            await interaction.response.send_message(f"{CHECK_OK} Suggestion submitted. An admin needs to set up a suggestion channel with `/logging channel`.", ephemeral=True)

    # ---- Custom Commands ----

    customcmd = app_commands.Group(name="customcmd", description="Manage custom text commands.")

    @customcmd.command(name="create", description="Create a custom text command.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def cc_create(self, interaction: discord.Interaction, name: str, response: str) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Server only.", ephemeral=True)
            return
        name = name.lower().strip()
        if not name or not name.isidentifier():
            await interaction.response.send_message("Name must be a valid single word.", ephemeral=True)
            return
        try:
            async with aiosqlite.connect(self.bot.db.db_path) as db:
                await db.execute(
                    "INSERT INTO custom_commands (guild_id, name, response) VALUES (?, ?, ?)",
                    (interaction.guild.id, name[:50], response[:2000]),
                )
                await db.commit()
            await interaction.response.send_message(f"{CHECK_OK} Custom command `{name}` created. Use it with `/{name}`.", ephemeral=True)
        except aiosqlite.IntegrityError:
            await interaction.response.send_message(f"Command `{name}` already exists.", ephemeral=True)

    @customcmd.command(name="delete", description="Delete a custom command.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def cc_delete(self, interaction: discord.Interaction, name: str) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Server only.", ephemeral=True)
            return
        name = name.lower().strip()
        async with aiosqlite.connect(self.bot.db.db_path) as db:
            await db.execute("DELETE FROM custom_commands WHERE guild_id = ? AND name = ?",
                             (interaction.guild.id, name))
            await db.commit()
        await interaction.response.send_message(f"{CHECK_OK} Custom command `{name}` deleted.", ephemeral=True)

    @customcmd.command(name="list", description="List all custom commands.")
    async def cc_list(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Server only.", ephemeral=True)
            return
        async with aiosqlite.connect(self.bot.db.db_path) as db:
            async with db.execute(
                "SELECT name, response FROM custom_commands WHERE guild_id = ? ORDER BY name",
                (interaction.guild.id,),
            ) as cursor:
                rows = await cursor.fetchall()
        if not rows:
            await interaction.response.send_message("No custom commands yet.", ephemeral=True)
            return
        lines = [f"`/{name}` — {resp[:60]}" for name, resp in rows]
        await interaction.response.send_message(f"{NOTE_SAVE} **Custom Commands**\n" + "\n".join(lines), ephemeral=True)

    # ---- Logging Setup ----

    @app_commands.command(name="logging", description="Set the logging/suggestions channel.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def logging_setup(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Server only.", ephemeral=True)
            return
        async with aiosqlite.connect(self.bot.db.db_path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO server_logging (guild_id) VALUES (?)", (interaction.guild.id,)
            )
            await db.execute(
                "UPDATE server_logging SET log_channel_id = ? WHERE guild_id = ?",
                (channel.id, interaction.guild.id),
            )
            await db.commit()
        await interaction.response.send_message(f"{CHECK_OK} Log/suggestion channel set to {channel.mention}.", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ServerMgmtCog(bot))
