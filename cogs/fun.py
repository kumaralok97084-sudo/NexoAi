from __future__ import annotations

import random

import discord
import httpx
from discord import app_commands
from discord.ext import commands

MEME_TEMPLATES = [
    {"id": "drake", "url": "https://api.memegen.link/images/drake/{top}/{bottom}.png", "desc": "Drake Yes/No"},
    {"id": "disastergirl", "url": "https://api.memegen.link/images/disastergirl/{top}/{bottom}.png", "desc": "Disaster Girl"},
    {"id": "doge", "url": "https://api.memegen.link/images/doge/{top}/{bottom}.png", "desc": "Doge"},
    {"id": "fry", "url": "https://api.memegen.link/images/fry/{top}/{bottom}.png", "desc": "Futurama Fry"},
    {"id": "grumpycat", "url": "https://api.memegen.link/images/grumpycat/{top}/{bottom}.png", "desc": "Grumpy Cat"},
    {"id": "guyfawkes", "url": "https://api.memegen.link/images/guyfawkes/{top}/{bottom}.png", "desc": "Anonymous Mask"},
    {"id": "monkey", "url": "https://api.memegen.link/images/monkey/{top}/{bottom}.png", "desc": "Monkey Puppet"},
    {"id": "blob", "url": "https://api.memegen.link/images/blob/{top}/{bottom}.png", "desc": "Blob"},
    {"id": "chad", "url": "https://api.memegen.link/images/chad/{top}/{bottom}.png", "desc": "Virgin vs Chad"},
    {"id": "wolverine", "url": "https://api.memegen.link/images/wolverine/{top}/{bottom}.png", "desc": "Wolverine Meme"},
]

ANIMAL_API_TIMEOUT = 10


class FunCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._http: httpx.AsyncClient | None = None

    async def _get_http(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(timeout=ANIMAL_API_TIMEOUT)
        return self._http

    async def cog_unload(self) -> None:
        if self._http:
            await self._http.aclose()

    async def _fetch_image(self, url: str) -> str | None:
        try:
            client = await self._get_http()
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list):
                return data[0].get("url") or data[0].get("src")
            return data.get("url") or data.get("message") or data.get("image")
        except Exception:
            return None

    @app_commands.command(name="cat", description="Get a random cat picture.")
    async def cat(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        url = await self._fetch_image("https://api.thecatapi.com/v1/images/search")
        if url:
            await interaction.followup.send(url)
        else:
            await interaction.followup.send("Could not fetch a cat picture right now.")

    @app_commands.command(name="dog", description="Get a random dog picture.")
    async def dog(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        url = await self._fetch_image("https://dog.ceo/api/breeds/image/random")
        if url:
            await interaction.followup.send(url)
        else:
            await interaction.followup.send("Could not fetch a dog picture right now.")

    @app_commands.command(name="fox", description="Get a random fox picture.")
    async def fox(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        url = await self._fetch_image("https://randomfox.ca/floof/")
        if url:
            await interaction.followup.send(url)
        else:
            await interaction.followup.send("Could not fetch a fox picture right now.")

    @app_commands.command(name="avatar", description="Show a user's avatar.")
    async def avatar(self, interaction: discord.Interaction, user: discord.User | None = None) -> None:
        target = user or interaction.user
        embed = discord.Embed(
            title=f"{target.display_name}'s Avatar",
            color=discord.Color.blue(),
        )
        embed.set_image(url=target.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="servericon", description="Show the server icon.")
    async def server_icon(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        if not guild or not guild.icon:
            await interaction.response.send_message("This server has no icon.", ephemeral=True)
            return
        embed = discord.Embed(title=f"{guild.name}'s Icon", color=discord.Color.blue())
        embed.set_image(url=guild.icon.url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="meme", description="Generate a custom meme.")
    @app_commands.describe(
        template="Meme template to use",
        top="Top text",
        bottom="Bottom text",
    )
    @app_commands.choices(template=[
        app_commands.Choice(name=t["desc"], value=t["id"]) for t in MEME_TEMPLATES
    ])
    async def meme(self, interaction: discord.Interaction, template: str, top: str, bottom: str) -> None:
        tpl = next((t for t in MEME_TEMPLATES if t["id"] == template), None)
        if not tpl:
            await interaction.response.send_message("Invalid template.", ephemeral=True)
            return
        import urllib.parse
        top_enc = urllib.parse.quote(top.replace("?", "~q").replace("--", "~~").replace("_", "__").replace(" ", "_"))
        bottom_enc = urllib.parse.quote(bottom.replace("?", "~q").replace("--", "~~").replace("_", "__").replace(" ", "_"))
        url = tpl["url"].format(top=top_enc or "_", bottom=bottom_enc or "_")
        embed = discord.Embed(title=f"Meme: {tpl['desc']}", color=discord.Color.green())
        embed.set_image(url=url)
        embed.set_footer(text="Powered by memegen.link")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="memetemplates", description="List available meme templates.")
    async def meme_templates(self, interaction: discord.Interaction) -> None:
        lines = [f"`{t['id']}` — {t['desc']}" for t in MEME_TEMPLATES]
        await interaction.response.send_message("**Meme Templates**\n" + "\n".join(lines), ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(FunCog(bot))
