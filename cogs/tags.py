from __future__ import annotations

import aiosqlite
import discord
from discord import app_commands
from discord.ext import commands


from cogs.emojis import CHECK_OK

class TagsCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    tag = app_commands.Group(name="tag", description="Manage server tags.")

    @tag.command(name="create", description="Create a new tag.")
    async def create(self, interaction: discord.Interaction, name: str, content: str) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Server only.", ephemeral=True)
            return
        name = name.lower().strip()
        if not name:
            await interaction.response.send_message("Tag name cannot be empty.", ephemeral=True)
            return
        try:
            async with aiosqlite.connect(self.bot.db.db_path) as db:
                await db.execute(
                    "INSERT INTO tags (guild_id, name, content, owner_id) VALUES (?, ?, ?, ?)",
                    (interaction.guild.id, name[:100], content[:2000], interaction.user.id),
                )
                await db.commit()
            await interaction.response.send_message(f"{CHECK_OK} Tag `{name}` created.", ephemeral=True)
        except aiosqlite.IntegrityError:
            await interaction.response.send_message(f"Tag `{name}` already exists.", ephemeral=True)

    @tag.command(name="show", description="Show a tag.")
    async def show(self, interaction: discord.Interaction, name: str) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Server only.", ephemeral=True)
            return
        name = name.lower().strip()
        async with aiosqlite.connect(self.bot.db.db_path) as db:
            async with db.execute(
                "SELECT content, uses FROM tags WHERE guild_id = ? AND name = ?",
                (interaction.guild.id, name),
            ) as cursor:
                row = await cursor.fetchone()
            if row:
                await db.execute("UPDATE tags SET uses = uses + 1 WHERE guild_id = ? AND name = ?",
                                 (interaction.guild.id, name))
                await db.commit()
        if row:
            await interaction.response.send_message(row[0])
        else:
            await interaction.response.send_message(f"Tag `{name}` not found.", ephemeral=True)

    @tag.command(name="delete", description="Delete a tag you own.")
    async def delete(self, interaction: discord.Interaction, name: str) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Server only.", ephemeral=True)
            return
        name = name.lower().strip()
        async with aiosqlite.connect(self.bot.db.db_path) as db:
            async with db.execute(
                "SELECT owner_id FROM tags WHERE guild_id = ? AND name = ?",
                (interaction.guild.id, name),
            ) as cursor:
                row = await cursor.fetchone()
            if not row:
                await interaction.response.send_message(f"Tag `{name}` not found.", ephemeral=True)
                return
            if row[0] != interaction.user.id and not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message("You don't own this tag.", ephemeral=True)
                return
            await db.execute("DELETE FROM tags WHERE guild_id = ? AND name = ?",
                             (interaction.guild.id, name))
            await db.commit()
        await interaction.response.send_message(f"{CHECK_OK} Tag `{name}` deleted.", ephemeral=True)

    @tag.command(name="list", description="List all tags in the server.")
    async def list_tags(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Server only.", ephemeral=True)
            return
        async with aiosqlite.connect(self.bot.db.db_path) as db:
            async with db.execute(
                "SELECT name, uses, owner_id FROM tags WHERE guild_id = ? ORDER BY uses DESC LIMIT 50",
                (interaction.guild.id,),
            ) as cursor:
                rows = await cursor.fetchall()
        if not rows:
            await interaction.response.send_message("No tags yet.", ephemeral=True)
            return
        lines = []
        for name, uses, owner_id in rows:
            user = self.bot.get_user(owner_id)
            owner = user.name if user else str(owner_id)
            lines.append(f"`{name}` — {uses} uses by {owner}")
        await interaction.response.send_message("📑 **Server Tags**\n" + "\n".join(lines), ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TagsCog(bot))
