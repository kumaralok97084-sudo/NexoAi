from __future__ import annotations

import re
from urllib.parse import urlparse

import aiosqlite
import discord
from discord import app_commands
from discord.ext import commands

from cogs.emojis import CHECK_OK, LINK_CHANNEL, STAT_ROLES

URL_RE = re.compile(r"https?://[^\s<>]+", re.IGNORECASE)


class LinkModCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def _is_whitelisted(self, guild_id: int, channel_id: int, member: discord.Member) -> bool:
        async with aiosqlite.connect(self.bot.db.db_path) as db:
            async with db.execute(
                "SELECT entity_id, entity_type FROM link_whitelist WHERE guild_id = ?",
                (guild_id,),
            ) as cursor:
                rows = await cursor.fetchall()
        for eid, etype in rows:
            if etype == "channel" and eid == channel_id:
                return True
            if etype == "role" and any(r.id == eid for r in member.roles):
                return True
        return False

    async def _check_domain(self, guild_id: int, domain: str) -> str | None:
        async with aiosqlite.connect(self.bot.db.db_path) as db:
            async with db.execute(
                "SELECT action FROM link_filters WHERE guild_id = ? AND domain = ?",
                (guild_id, domain),
            ) as cursor:
                row = await cursor.fetchone()
        return row[0] if row else None

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or not message.guild:
            return

        urls = URL_RE.findall(message.content)
        if not urls:
            return

        if isinstance(message.author, discord.Member) and await self._is_whitelisted(
            message.guild.id, message.channel.id, message.author
        ):
            return

        for url in urls:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            if domain.startswith("www."):
                domain = domain[4:]

            action = await self._check_domain(message.guild.id, domain)
            if action is None:
                continue

            try:
                await message.delete()
                await self.bot.db.add_moderation_log(
                    message.guild.id, message.author.id, "link_block",
                    f"Blocked domain: {domain}", message.content[:200],
                )
                if action == "warn":
                    await self.bot.db.add_warn(
                        message.guild.id, message.author.id, f"Blocked link: {domain}", self.bot.user.id if self.bot.user else 0,
                    )

                notify = f"{message.author.mention} blocked link: `{domain}`"
                if action == "warn":
                    notify += " (warned)"
                await message.channel.send(notify, delete_after=10)
            except discord.Forbidden:
                pass
            return

    # ---- Commands ----

    linkblock = app_commands.Group(name="linkblock", description="Manage blocked domains.")

    @linkblock.command(name="add", description="Block a domain.")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.choices(action=[
        app_commands.Choice(name="Delete only", value="delete"),
        app_commands.Choice(name="Delete + warn", value="warn"),
    ])
    async def add_block(
        self, interaction: discord.Interaction,
        domain: str, action: str = "delete",
    ) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Server only.", ephemeral=True)
            return
        domain = domain.lower().strip().removeprefix("http://").removeprefix("https://").removeprefix("www.")
        try:
            async with aiosqlite.connect(self.bot.db.db_path) as db:
                await db.execute(
                    "INSERT INTO link_filters (guild_id, domain, action) VALUES (?, ?, ?)",
                    (interaction.guild.id, domain, action),
                )
                await db.commit()
            await interaction.response.send_message(f"{CHECK_OK} Blocked `{domain}` (action: {action}).", ephemeral=True)
        except aiosqlite.IntegrityError:
            await interaction.response.send_message(f"`{domain}` is already blocked.", ephemeral=True)

    @linkblock.command(name="remove", description="Unblock a domain.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def remove_block(self, interaction: discord.Interaction, domain: str) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Server only.", ephemeral=True)
            return
        domain = domain.lower().strip().removeprefix("http://").removeprefix("https://").removeprefix("www.")
        async with aiosqlite.connect(self.bot.db.db_path) as db:
            await db.execute(
                "DELETE FROM link_filters WHERE guild_id = ? AND domain = ?",
                (interaction.guild.id, domain),
            )
            await db.commit()
        await interaction.response.send_message(f"{CHECK_OK} Unblocked `{domain}`.", ephemeral=True)

    @linkblock.command(name="list", description="List all blocked domains.")
    async def list_blocks(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Server only.", ephemeral=True)
            return
        async with aiosqlite.connect(self.bot.db.db_path) as db:
            async with db.execute(
                "SELECT domain, action FROM link_filters WHERE guild_id = ? ORDER BY domain",
                (interaction.guild.id,),
            ) as cursor:
                rows = await cursor.fetchall()
        if not rows:
            await interaction.response.send_message("No blocked domains.", ephemeral=True)
            return
        lines = [f"`{d}` → {a}" for d, a in rows]
        await interaction.response.send_message("**Blocked Domains**\n" + "\n".join(lines), ephemeral=True)

    linkwhitelist = app_commands.Group(name="linkwhitelist", description="Manage link filter exemptions.")

    @linkwhitelist.command(name="addchannel", description="Exempt a channel from link filtering.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def whitelist_channel(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Server only.", ephemeral=True)
            return
        async with aiosqlite.connect(self.bot.db.db_path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO link_whitelist (guild_id, entity_id, entity_type) VALUES (?, ?, 'channel')",
                (interaction.guild.id, channel.id),
            )
            await db.commit()
        await interaction.response.send_message(f"{CHECK_OK} {channel.mention} exempted from link filtering.", ephemeral=True)

    @linkwhitelist.command(name="addrole", description="Exempt a role from link filtering.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def whitelist_role(self, interaction: discord.Interaction, role: discord.Role) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Server only.", ephemeral=True)
            return
        async with aiosqlite.connect(self.bot.db.db_path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO link_whitelist (guild_id, entity_id, entity_type) VALUES (?, ?, 'role')",
                (interaction.guild.id, role.id),
            )
            await db.commit()
        await interaction.response.send_message(f"{CHECK_OK} {role.mention} exempted from link filtering.", ephemeral=True)

    @linkwhitelist.command(name="remove", description="Remove a link filter exemption.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def whitelist_remove(self, interaction: discord.Interaction, entity_id: str) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Server only.", ephemeral=True)
            return
        try:
            eid = int(entity_id)
        except ValueError:
            await interaction.response.send_message("Invalid ID.", ephemeral=True)
            return
        async with aiosqlite.connect(self.bot.db.db_path) as db:
            await db.execute(
                "DELETE FROM link_whitelist WHERE guild_id = ? AND entity_id = ?",
                (interaction.guild.id, eid),
            )
            await db.commit()
        await interaction.response.send_message(f"{CHECK_OK} Removed exemption for `{eid}`.", ephemeral=True)

    @linkwhitelist.command(name="list", description="List all link filter exemptions.")
    async def whitelist_list(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Server only.", ephemeral=True)
            return
        async with aiosqlite.connect(self.bot.db.db_path) as db:
            async with db.execute(
                "SELECT entity_id, entity_type FROM link_whitelist WHERE guild_id = ?",
                (interaction.guild.id,),
            ) as cursor:
                rows = await cursor.fetchall()
        if not rows:
            await interaction.response.send_message("No exemptions.", ephemeral=True)
            return
        lines = []
        for eid, etype in rows:
            if etype == "channel":
                obj = interaction.guild.get_channel(eid)
                lines.append(f"{LINK_CHANNEL} Channel: {obj.mention if obj else f'Unknown ({eid})'}")
            else:
                obj = interaction.guild.get_role(eid)
                lines.append(f"{STAT_ROLES} Role: {obj.mention if obj else f'Unknown ({eid})'}")
        await interaction.response.send_message("**Link Filter Exemptions**\n" + "\n".join(lines), ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(LinkModCog(bot))
