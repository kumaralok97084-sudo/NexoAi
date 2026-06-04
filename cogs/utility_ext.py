from __future__ import annotations

import aiosqlite
import discord
from discord import app_commands
from discord.ext import commands

from cogs.emojis import AFK_ICON, CHECK_OK, CROSS_NO

class UtilityExtCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    # ---- AFK ----

    @app_commands.command(name="afk", description="Set yourself as AFK.")
    async def afk(self, interaction: discord.Interaction, reason: str = "") -> None:
        if not interaction.guild:
            await interaction.response.send_message(f"{CROSS_NO} Server only.", ephemeral=True)
            return
        async with aiosqlite.connect(self.bot.db.db_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO afk_status (user_id, guild_id, reason, since) VALUES (?, ?, ?, datetime('now'))",
                (interaction.user.id, interaction.guild.id, reason[:200]),
            )
            await db.commit()

        msg = f"{CHECK_OK} Set AFK. Reason: {reason}" if reason else f"{CHECK_OK} Set AFK."
        await interaction.response.send_message(msg, ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or not message.guild:
            return

        # Remove AFK if the user is back
        async with aiosqlite.connect(self.bot.db.db_path) as db:
            async with db.execute(
                "SELECT reason FROM afk_status WHERE user_id = ? AND guild_id = ?",
                (message.author.id, message.guild.id),
            ) as cursor:
                row = await cursor.fetchone()
            if row:
                await db.execute(
                    "DELETE FROM afk_status WHERE user_id = ? AND guild_id = ?",
                    (message.author.id, message.guild.id),
                )
                await db.commit()
                try:
                    await message.channel.send(f"{CHECK_OK} Welcome back {message.author.mention}! Removed your AFK.", delete_after=5)
                except discord.Forbidden:
                    pass

        # Check mentions for AFK users
        for mentioned in message.mentions:
            async with aiosqlite.connect(self.bot.db.db_path) as db:
                async with db.execute(
                    "SELECT reason FROM afk_status WHERE user_id = ? AND guild_id = ?",
                    (mentioned.id, message.guild.id),
                ) as cursor:
                    row = await cursor.fetchone()
            if row:
                reason_text = f" Reason: {row[0]}" if row[0] else ""
                try:
                    await message.channel.send(
                        f"{AFK_ICON} {mentioned.display_name} is AFK.{reason_text}",
                        delete_after=10,
                        reference=message,
                    )
                except discord.Forbidden:
                    pass

    # ---- Birthday ----

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(UtilityExtCog(bot))
