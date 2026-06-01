from __future__ import annotations

import asyncio
import logging

import aiosqlite
import discord
from discord import app_commands
from discord.ext import commands

from cogs.emojis import CHECK_OK, ONLINE_DOT, POLL_BAR, STAT_BOTS, STAT_CHANNELS, STAT_HUMANS, STAT_MEMBERS, STAT_ROLES

logger = logging.getLogger(__name__)

STAT_TYPES = ("members", "humans", "bots", "channels", "roles", "online")


class ServerStatsCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._update_task: asyncio.Task | None = None

    async def cog_load(self) -> None:
        self._update_task = asyncio.create_task(self._periodic_update())

    async def cog_unload(self) -> None:
        if self._update_task:
            self._update_task.cancel()

    async def _periodic_update(self) -> None:
        while True:
            try:
                await asyncio.sleep(300)
                await self._update_all()
            except asyncio.CancelledError:
                break
            except Exception:
                pass

    async def _update_all(self) -> None:
        async with aiosqlite.connect(self.bot.db.db_path) as db:
            async with db.execute("SELECT guild_id, channel_id, stat_type FROM server_stats") as cursor:
                rows = await cursor.fetchall()

        for guild_id, channel_id, stat_type in rows:
            guild = self.bot.get_guild(guild_id)
            if not guild:
                continue
            channel = guild.get_channel(channel_id)
            if not isinstance(channel, discord.VoiceChannel):
                continue

            value = self._get_stat(guild, stat_type)
            name = self._format_name(stat_type, value)
            try:
                await channel.edit(name=name)
            except (discord.Forbidden, discord.HTTPException) as exc:
                logger.warning("Failed to update stats channel %s: %s", channel_id, exc)

    @staticmethod
    def _get_stat(guild: discord.Guild, stat_type: str) -> int:
        if stat_type == "members":
            return guild.member_count or 0
        elif stat_type == "humans":
            return sum(1 for m in guild.members if not m.bot)
        elif stat_type == "bots":
            return sum(1 for m in guild.members if m.bot)
        elif stat_type == "channels":
            return len(guild.channels)
        elif stat_type == "roles":
            return len(guild.roles)
        elif stat_type == "online":
            return sum(1 for m in guild.members if m.status != discord.Status.offline)
        return 0

    @staticmethod
    def _format_name(stat_type: str, value: int) -> str:
        emoji = {
            "members": f"{STAT_MEMBERSf"{STAT_HUMANf"{STAT_BOTS}" "humans": "👤", "bots": "🤖",
            "channels": f"{STAT_CHANNEf"{STAT_ROLES}"f"{ONLINE_DOT}""roles": "🎭", "online": "🟢",
        }
        labels = {
            "members": "Members", "humans": "Humans", "bots": "Bots",
            "channels": "Channels", "roles": "Roles", "online": "Online",
        }
        return f"{emoji.get(stat_type, '{POLL_BAR}')} {labels.get(stat_type, stat_type)}: {value}"

    statschannel = app_commands.Group(name="statschannel", description="Manage auto-updating stats channels.")

    @statschannel.command(name="set", description="Set a voice channel to auto-update with server stats.")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.choices(stat_type=[
        app_commands.Choice(name="Total Members", value="members"),
        app_commands.Choice(name="Humans", value="humans"),
        app_commands.Choice(name="Bots", value="bots"),
        app_commands.Choice(name="Total Channels", value="channels"),
        app_commands.Choice(name="Total Roles", value="roles"),
        app_commands.Choice(name="Online Members", value="online"),
    ])
    async def set_stats_channel(
        self, interaction: discord.Interaction,
        channel: discord.VoiceChannel,
        stat_type: str,
    ) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Server only.", ephemeral=True)
            return
        try:
            async with aiosqlite.connect(self.bot.db.db_path) as db:
                await db.execute(
                    "INSERT OR REPLACE INTO server_stats (guild_id, channel_id, stat_type) VALUES (?, ?, ?)",
                    (interaction.guild.id, channel.id, stat_type),
                )
                await db.commit()
        except aiosqlite.IntegrityError:
            async with aiosqlite.connect(self.bot.db.db_path) as db:
                await db.execute(
                    "UPDATE server_stats SET channel_id = ? WHERE guild_id = ? AND stat_type = ?",
                    (channel.id, interaction.guild.id, stat_type),
                )
                await db.commit()

        value = self._get_stat(interaction.guild, stat_type)
        name = self._format_name(stat_type, value)
        try:
            await channel.edit(name=name)
        except discord.Forbidden:
            await interaction.response.send_message("I can't edit that channel.", ephemeral=True)
            return

        await interaction.response.send_message(f"{CHECK_OK} `{stat_type}` stats will update in {channel.mention}.", ephemeral=True)

    @statschannel.command(name="remove", description="Remove a stats channel.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def remove_stats_channel(self, interaction: discord.Interaction, stat_type: str) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Server only.", ephemeral=True)
            return
        async with aiosqlite.connect(self.bot.db.db_path) as db:
            await db.execute(
                "DELETE FROM server_stats WHERE guild_id = ? AND stat_type = ?",
                (interaction.guild.id, stat_type),
            )
            await db.commit()
        await interaction.response.send_message(f"Removed `{stat_type}` stats channel.", ephemeral=True)

    @statschannel.command(name="list", description="List all stats channels.")
    async def list_stats_channels(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Server only.", ephemeral=True)
            return
        async with aiosqlite.connect(self.bot.db.db_path) as db:
            async with db.execute(
                "SELECT channel_id, stat_type FROM server_stats WHERE guild_id = ?",
                (interaction.guild.id,),
            ) as cursor:
                rows = await cursor.fetchall()
        if not rows:
            await interaction.response.send_message("No stats channels configured.", ephemeral=True)
            return
        lines = [f"<#{cid}> → `{st}`" for cid, st in rows]
        await interaction.response.send_message("**Stats Channels**\n" + "\n".join(lines), ephemeral=True)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        await self._update_all()

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        await self._update_all()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ServerStatsCog(bot))
