from __future__ import annotations

import math
import random
from datetime import datetime, timezone

import aiosqlite
import discord
from discord import app_commands
from discord.ext import commands

from cogs.emojis import BRONZE, GIVEAWAY, GIVEAWAY_WIN, GOLD, SILVER

XP_PER_MSG = (10, 20)
XP_COOLDOWN = 60
LEVEL_BASE = 50
LEVEL_FACTOR = 1.5


def _xp_for_level(level: int) -> int:
    return int(LEVEL_BASE * (level ** LEVEL_FACTOR))


class LevelingCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._cooldowns: dict[int, float] = {}

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or not message.guild:
            return

        now = message.created_at.timestamp()
        last = self._cooldowns.get(message.author.id, 0)
        if now - last < XP_COOLDOWN:
            return
        self._cooldowns[message.author.id] = now

        xp_min, xp_max = XP_PER_MSG[0], XP_PER_MSG[1]
        xp_gain = random.randint(xp_min, xp_max)
        async with aiosqlite.connect(self.bot.db.db_path) as db:
            async with db.execute(
                "SELECT xp_min, xp_max FROM guild_settings WHERE guild_id = ?",
                (message.guild.id,),
            ) as cursor:
                row = await cursor.fetchone()
                if row and row[0] and row[1]:
                    xp_gain = random.randint(row[0], row[1])
            async with db.execute(
                "SELECT xp, level FROM user_xp WHERE user_id = ? AND guild_id = ?",
                (message.author.id, message.guild.id),
            ) as cursor:
                row = await cursor.fetchone()

            if row:
                new_xp = row[0] + xp_gain
                new_level = row[1]
                level_up = False
                while new_xp >= _xp_for_level(new_level + 1):
                    new_level += 1
                    new_xp -= _xp_for_level(new_level)
                    level_up = True

                await db.execute(
                    "UPDATE user_xp SET xp = ?, level = ?, last_xp_time = ? WHERE user_id = ? AND guild_id = ?",
                    (new_xp, new_level, datetime.now(timezone.utc).isoformat(), message.author.id, message.guild.id),
                )

                if level_up and isinstance(message.author, discord.Member):
                    await self._handle_level_up(message.author, new_level, message.guild)
            else:
                new_xp = xp_gain
                new_level = 1
                await db.execute(
                    "INSERT INTO user_xp (user_id, guild_id, xp, level, last_xp_time) VALUES (?, ?, ?, ?, ?)",
                    (message.author.id, message.guild.id, new_xp, new_level, datetime.now(timezone.utc).isoformat()),
                )

            await db.commit()

    async def _handle_level_up(self, member: discord.Member, new_level: int, guild: discord.Guild) -> None:
        async with aiosqlite.connect(self.bot.db.db_path) as db:
            async with db.execute(
                "SELECT role_id FROM level_rewards WHERE guild_id = ? AND level = ?",
                (guild.id, new_level),
            ) as cursor:
                row = await cursor.fetchone()
        if row:
            role = guild.get_role(int(row[0]))
            if role and role < guild.me.top_role:
                try:
                    await member.add_roles(role, reason=f"Level {new_level} reward")
                except discord.Forbidden:
                    pass
        try:
            await member.send(f"{GIVEAWAY} Congrats {member.mention}! You reached **Level {new_level}** in **{guild.name}**!")
        except discord.Forbidden:
            pass

    @app_commands.command(name="rank", description="Show your or another user's XP and level.")
    async def rank(self, interaction: discord.Interaction, user: discord.User | None = None) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Server only.", ephemeral=True)
            return
        target = user or interaction.user
        async with aiosqlite.connect(self.bot.db.db_path) as db:
            async with db.execute(
                "SELECT xp, level FROM user_xp WHERE user_id = ? AND guild_id = ?",
                (target.id, interaction.guild.id),
            ) as cursor:
                row = await cursor.fetchone()

        if not row:
            await interaction.response.send_message(f"{target.display_name} has no XP yet. Start chatting!", ephemeral=True)
            return

        xp, level = row
        next_xp = _xp_for_level(level + 1)
        progress = min(xp / next_xp * 100, 100)
        bar_len = 12
        filled = int(progress / 100 * bar_len)
        bar = "▰" * filled + "▱" * (bar_len - filled)

        embed = discord.Embed(
            title=f"{target.display_name}'s Rank",
            color=discord.Color.blue(),
        )
        embed.add_field(name="Level", value=str(level), inline=True)
        embed.add_field(name="XP", value=f"{xp}/{next_xp}", inline=True)
        embed.add_field(name="Progress", value=f"{bar} {progress:.0f}%", inline=False)
        embed.set_thumbnail(url=target.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="levelleaderboard", description="Show the server XP leaderboard.")
    async def leaderboard(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Server only.", ephemeral=True)
            return
        async with aiosqlite.connect(self.bot.db.db_path) as db:
            async with db.execute(
                "SELECT user_id, level, xp FROM user_xp WHERE guild_id = ? ORDER BY level DESC, xp DESC LIMIT 10",
                (interaction.guild.id,),
            ) as cursor:
                rows = await cursor.fetchall()

        if not rows:
            await interaction.response.send_message("No XP data yet.", ephemeral=True)
            return

        lines = []
        for i, (uid, level, xp) in enumerate(rows, 1):
            user = self.bot.get_user(uid)
            name = user.display_name if user else f"Unknown ({uid})"
            medal = {1: f"{GOLD}f"{SILVEf"{BRONZE}"2: "🥈", 3: "🥉"}.get(i, f"#{i}")
            lines.append(f"{medal} **{name}** — Lv.{level} ({xp} XP)")

        embed = discord.Embed(title=f"{GIVEAWAY_WIN} Level Leaderboard", description="\n".join(lines), color=discord.Color.gold())
        await interaction.response.send_message(embed=embed)

    # ---- Admin Leveling Settings ----

    levelconfig = app_commands.Group(name="levelconfig", description="Configure leveling system.")

    @levelconfig.command(name="setxprate", description="Set XP range per message.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_xp_rate(self, interaction: discord.Interaction, min_xp: int, max_xp: int) -> None:
        if min_xp < 1 or max_xp < min_xp:
            await interaction.response.send_message("Invalid range.", ephemeral=True)
            return
        async with aiosqlite.connect(self.bot.db.db_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO guild_settings (guild_id, xp_min, xp_max) VALUES (?, ?, ?)",
                (interaction.guild.id, min_xp, max_xp),
            )
            await db.commit()
        await interaction.response.send_message(f"XP per message set to {min_xp}-{max_xp}.", ephemeral=True)

    @levelconfig.command(name="addrole", description="Assign a role at a specific level.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def add_level_role(self, interaction: discord.Interaction, level: int, role: discord.Role) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Server only.", ephemeral=True)
            return
        if role >= interaction.guild.me.top_role:
            await interaction.response.send_message("That role is above my highest role.", ephemeral=True)
            return
        try:
            async with aiosqlite.connect(self.bot.db.db_path) as db:
                await db.execute(
                    "INSERT INTO level_rewards (guild_id, level, role_id) VALUES (?, ?, ?)",
                    (interaction.guild.id, level, role.id),
                )
                await db.commit()
            await interaction.response.send_message(f"{role.mention} will be awarded at level {level}.", ephemeral=True)
        except aiosqlite.IntegrityError:
            await interaction.response.send_message("A reward for that level already exists.", ephemeral=True)

    @levelconfig.command(name="removerole", description="Remove a level role reward.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def remove_level_role(self, interaction: discord.Interaction, level: int) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Server only.", ephemeral=True)
            return
        async with aiosqlite.connect(self.bot.db.db_path) as db:
            await db.execute(
                "DELETE FROM level_rewards WHERE guild_id = ? AND level = ?",
                (interaction.guild.id, level),
            )
            await db.commit()
        await interaction.response.send_message(f"Removed reward for level {level}.", ephemeral=True)

    @levelconfig.command(name="listroles", description="List all level role rewards.")
    async def list_level_roles(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Server only.", ephemeral=True)
            return
        async with aiosqlite.connect(self.bot.db.db_path) as db:
            async with db.execute(
                "SELECT level, role_id FROM level_rewards WHERE guild_id = ? ORDER BY level",
                (interaction.guild.id,),
            ) as cursor:
                rows = await cursor.fetchall()
        if not rows:
            await interaction.response.send_message("No level rewards configured.", ephemeral=True)
            return
        lines = []
        for level, role_id in rows:
            role = interaction.guild.get_role(int(role_id))
            role_name = role.mention if role else f"Deleted ({role_id})"
            lines.append(f"Level **{level}** → {role_name}")
        await interaction.response.send_message("**Level Rewards**\n" + "\n".join(lines), ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(LevelingCog(bot))
