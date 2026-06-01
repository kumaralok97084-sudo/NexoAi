from __future__ import annotations

from datetime import datetime, timezone

import aiosqlite
import discord
from discord import app_commands
from discord.ext import commands


from cogs.emojis import AFK_ICON, BIRTHDAY_CAKE, CHECK_OK

class UtilityExtCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    # ---- AFK ----

    @app_commands.command(name="afk", description="Set yourself as AFK.")
    async def afk(self, interaction: discord.Interaction, reason: str = "") -> None:
        if not interaction.guild:
            await interaction.response.send_message("Server only.", ephemeral=True)
            return
        async with aiosqlite.connect(self.bot.db.db_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO afk_status (user_id, guild_id, reason, since) VALUES (?, ?, ?, datetime('now'))",
                (interaction.user.id, interaction.guild.id, reason[:200]),
            )
            await db.commit()

        msg = f"{CHECK_OK} Set AFK. Reason: {reason}" if reaf"{CHECK_OK} Set AFK."Set AFK."
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
                    await message.channel.send(f"Welcome back {message.author.mention}! Removed your AFK.", delete_after=5)
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

    @app_commands.command(name="setbirthday", description="Set your birthday.")
    @app_commands.describe(month="Month (1-12)", day="Day (1-31)")
    async def set_birthday(self, interaction: discord.Interaction, month: app_commands.Range[int, 1, 12], day: app_commands.Range[int, 1, 31]) -> None:
        async with aiosqlite.connect(self.bot.db.db_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO birthdays (user_id, month, day) VALUES (?, ?, ?)",
                (interaction.user.id, month, day),
            )
            await db.commit()
        await interaction.response.send_message(f"{CHECK_OK} Birthday set to **{month}/{day}**.", ephemeral=True)

    @app_commands.command(name="birthdays", description="Show upcoming birthdays this month.")
    async def birthdays(self, interaction: discord.Interaction) -> None:
        now = datetime.now(timezone.utc)
        month = now.month
        async with aiosqlite.connect(self.bot.db.db_path) as db:
            async with db.execute(
                "SELECT user_id, day FROM birthdays WHERE month = ? ORDER BY day", (month,)
            ) as cursor:
                rows = await cursor.fetchall()

        if not rows:
            await interaction.response.send_message("No birthdays this month.", ephemeral=True)
            return

        lines = []
        for uid, day in rows:
            user = self.bot.get_user(uid)
            name = user.display_name if user else f"Unknown ({uid})"
            lines.append(f"**{name}** — {month}/{day}")
        embed = discord.Embed(
            title=f"{BIRTHDAY_CAKE} Birthdays This Month ({month})",
            description="\n".join(lines),
            color=discord.Color.pink(),
        )
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(UtilityExtCog(bot))
