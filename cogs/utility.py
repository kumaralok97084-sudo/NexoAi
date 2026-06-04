from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands

from cogs.emojis import CHECK_OK, CROSS_NO, COUNTDOWN, NOTE_SAVE, POLL_BAR, REMINDER

POLL_EMOJIS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]


class UtilityCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="poll", description="Create a poll with up to 10 options.")
    async def create_poll(
        self, interaction: discord.Interaction,
        question: str,
        option1: str, option2: str,
        option3: str | None = None, option4: str | None = None,
        option5: str | None = None, option6: str | None = None,
        option7: str | None = None, option8: str | None = None,
        option9: str | None = None, option10: str | None = None,
    ) -> None:
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message(f"{CROSS_NO} Use in a text channel.", ephemeral=True)
            return
        options = [o for o in [option1, option2, option3, option4, option5, option6, option7, option8, option9, option10] if o]
        if len(options) < 2:
            await interaction.response.send_message(f"{CROSS_NO} Need at least 2 options.", ephemeral=True)
            return

        lines = []
        for i, opt in enumerate(options[:10]):
            lines.append(f"{POLL_EMOJIS[i]} {opt}")
        embed = discord.Embed(title=f"{POLL_BAR} {question}", description="\n".join(lines), color=discord.Color.blue())
        embed.set_footer(text=f"Poll by {interaction.user}")

        await interaction.response.send_message(embed=embed)
        msg = await interaction.original_response()
        for i in range(len(options[:10])):
            await msg.add_reaction(POLL_EMOJIS[i])

        await self.bot.db.create_poll(
            interaction.guild_id or 0, interaction.channel.id, msg.id,
            question, json.dumps(options[:10]), interaction.user.id,
        )

    # --- Reaction Roles ---
    @app_commands.command(name="rolemenu", description="Set up a reaction role message.")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def role_menu(
        self, interaction: discord.Interaction,
        channel: discord.TextChannel,
        message_id: str,
        role: discord.Role,
        emoji: str,
    ) -> None:
        if role >= interaction.guild.me.top_role:
            await interaction.response.send_message(f"{CROSS_NO} Role is above my highest role.", ephemeral=True)
            return
        try:
            msg_id = int(message_id)
        except ValueError:
            await interaction.response.send_message(f"{CROSS_NO} Invalid message ID.", ephemeral=True)
            return

        await self.bot.db.add_reaction_role(interaction.guild.id, channel.id, msg_id, role.id, emoji)
        msg = await channel.fetch_message(msg_id)
        await msg.add_reaction(emoji)
        await interaction.response.send_message(f"{CHECK_OK} Reaction role set: {emoji} -> {role.mention}", ephemeral=True)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        if payload.user_id == self.bot.user.id:
            return
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        rows = await self.bot.db.get_reaction_roles(payload.guild_id, payload.channel_id, payload.message_id)
        for row in rows:
            if str(payload.emoji) == row["emoji"]:
                role = guild.get_role(int(row["role_id"]))
                member = guild.get_member(payload.user_id)
                if role and member and role < guild.me.top_role:
                    try:
                        await member.add_roles(role, reason="Reaction role")
                    except discord.Forbidden:
                        pass

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent) -> None:
        if payload.user_id == self.bot.user.id:
            return
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        rows = await self.bot.db.get_reaction_roles(payload.guild_id, payload.channel_id, payload.message_id)
        for row in rows:
            if str(payload.emoji) == row["emoji"]:
                role = guild.get_role(int(row["role_id"]))
                member = guild.get_member(payload.user_id)
                if role and member:
                    try:
                        await member.remove_roles(role, reason="Reaction role removed")
                    except discord.Forbidden:
                        pass

    # --- Reminders ---
    @app_commands.command(name="remind", description="Set a reminder.")
    async def remind(
        self, interaction: discord.Interaction,
        minutes: app_commands.Range[int, 1, 10080],
        message: str,
    ) -> None:
        remind_at = (datetime.utcnow() + timedelta(minutes=minutes)).strftime("%Y-%m-%d %H:%M:%S")
        rid = await self.bot.db.add_reminder(
            interaction.user.id, interaction.channel_id, interaction.guild_id or 0, message, remind_at
        )
        await interaction.response.send_message(f"{REMINDER} Reminder set for {minutes} minute(s) (ID: {rid}).", ephemeral=True)

    # --- Notes ---
    @app_commands.command(name="note", description="Save a personal note.")
    async def add_note(self, interaction: discord.Interaction, title: str, content: str) -> None:
        nid = await self.bot.db.add_note(interaction.user.id, interaction.guild_id or 0, title, content)
        await interaction.response.send_message(f"{NOTE_SAVE} Note saved (ID: {nid}).", ephemeral=True)

    @app_commands.command(name="notes", description="List your saved notes.")
    async def list_notes(self, interaction: discord.Interaction) -> None:
        notes = await self.bot.db.get_notes(interaction.user.id, interaction.guild_id or 0)
        if not notes:
            await interaction.response.send_message(f"{CROSS_NO} No notes saved.", ephemeral=True)
            return
        lines = [f"`#{n['id']}` **{n['title']}**" for n in notes[:20]]
        await interaction.response.send_message(f"{NOTE_SAVE} **Your Notes**\n" + "\n".join(lines), ephemeral=True)

    # --- Quick Utilities ---
    @app_commands.command(name="color", description="Show a color preview.")
    async def color_picker(self, interaction: discord.Interaction, hex_color: str) -> None:
        hex_color = hex_color.lstrip("#")
        if len(hex_color) != 6:
            await interaction.response.send_message(f"{CROSS_NO} Invalid hex color. Use format: FF00AA", ephemeral=True)
            return
        try:
            r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        except ValueError:
            await interaction.response.send_message(f"{CROSS_NO} Invalid hex color.", ephemeral=True)
            return
        embed = discord.Embed(
            title=f"{POLL_BAR} Color #{hex_color.upper()}",
            description=f"RGB: ({r}, {g}, {b})",
            color=discord.Color.from_rgb(r, g, b),
        )
        embed.set_thumbnail(url=f"https://singlecolorimage.com/get/{hex_color}/200x200")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="define", description="Look up a word definition.")
    async def define(self, interaction: discord.Interaction, word: str) -> None:
        await interaction.response.defer()
        import httpx
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}")
                if resp.status_code != 200:
                    await interaction.followup.send(f"{CROSS_NO} No definition found for `{word}`.")
                    return
                data = resp.json()[0]
                meaning = data.get("meanings", [{}])[0]
                defn = meaning.get("definitions", [{}])[0]
                embed = discord.Embed(title=f"{NOTE_SAVE} {word}", color=discord.Color.blue())
                embed.add_field(name="Definition", value=defn.get("definition", "N/A")[:1000], inline=False)
                if defn.get("example"):
                    embed.add_field(name="Example", value=defn["example"], inline=False)
                await interaction.followup.send(embed=embed)
        except Exception as exc:
            await interaction.followup.send(f"{CROSS_NO} Lookup failed: `{exc}`")

    @app_commands.command(name="weather", description="Get weather for a city.")
    async def weather(self, interaction: discord.Interaction, city: str) -> None:
        await interaction.response.defer()
        import httpx
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"https://wttr.in/{city}?format=%l:+%t+%h+%w+%C")
                if resp.status_code == 200:
                    await interaction.followup.send(f"{CHECK_OK} **{city}**\n```\n{resp.text.strip()}\n```")
                else:
                    await interaction.followup.send(f"{CROSS_NO} Could not get weather for `{city}`.")
        except Exception as exc:
            await interaction.followup.send(f"{CROSS_NO} Weather lookup failed: `{exc}`")

    @app_commands.command(name="timer", description="Start a visual countdown timer.")
    async def timer(self, interaction: discord.Interaction, seconds: app_commands.Range[int, 1, 3600]) -> None:
        await interaction.response.send_message(f"{COUNTDOWN} Timer set for {seconds}s...")
        msg = await interaction.original_response()
        start = datetime.utcnow()
        for remaining in range(seconds, 0, -1):
            elapsed = seconds - remaining
            frac = elapsed / max(seconds, 1)
            bar_len = 20
            filled = int(bar_len * frac)
            bar = "🟩" * filled + "⬜" * (bar_len - filled)
            mins, secs = divmod(remaining, 60)
            time_str = f"{mins:02d}:{secs:02d}"
            await msg.edit(content=f"{COUNTDOWN} **{time_str}**\n{bar}")
            await asyncio.sleep(1)
        await msg.edit(content=f"{COUNTDOWN} **Done!** {interaction.user.mention} Your {seconds}s timer is finished! 🔔")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(UtilityCog(bot))
