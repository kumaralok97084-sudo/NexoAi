from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from cogs.emojis import CHECK_OK

COLOR_MAP = {
    "blue": discord.Color.blue(), "blurple": discord.Color.blurple(),
    "brand_green": discord.Color.brand_green(), "brand_red": discord.Color.brand_red(),
    "dark_blue": discord.Color.dark_blue(), "dark_gold": discord.Color.dark_gold(),
    "dark_gray": discord.Color.dark_gray(), "dark_green": discord.Color.dark_green(),
    "dark_grey": discord.Color.dark_grey(), "dark_magenta": discord.Color.dark_magenta(),
    "dark_orange": discord.Color.dark_orange(), "dark_purple": discord.Color.dark_purple(),
    "dark_red": discord.Color.dark_red(), "dark_teal": discord.Color.dark_teal(),
    "dark_theme": discord.Color.dark_theme(), "gold": discord.Color.gold(),
    "green": discord.Color.green(), "greyple": discord.Color.greyple(),
    "light_gray": discord.Color.light_gray(), "light_grey": discord.Color.light_grey(),
    "magenta": discord.Color.magenta(), "orange": discord.Color.orange(),
    "pink": discord.Color.pink(), "purple": discord.Color.purple(),
    "red": discord.Color.red(), "teal": discord.Color.teal(),
    "yellow": discord.Color.yellow(),
}


class EmbedBuilderCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="embed", description="Create a custom embed.")
    @app_commands.checks.has_permissions(manage_messages=True)
    @app_commands.describe(
        title="Embed title",
        description="Embed description",
        color="Color name (e.g. blue, red, gold, purple)",
        field_name="Field name (optional)",
        field_value="Field value (required if field_name set)",
        inline="Whether the field is inline (default: False)",
        image="Image URL",
        thumbnail="Thumbnail URL",
        footer="Footer text",
        channel="Channel to send to (default: current channel)",
    )
    async def embed_cmd(
        self, interaction: discord.Interaction,
        title: str,
        description: str,
        color: str = "blurple",
        field_name: str | None = None,
        field_value: str | None = None,
        inline: bool = False,
        image: str | None = None,
        thumbnail: str | None = None,
        footer: str | None = None,
        channel: discord.TextChannel | None = None,
    ) -> None:
        embed_color = COLOR_MAP.get(color.lower().strip(), discord.Color.blurple())
        embed = discord.Embed(title=title[:256], description=description[:4096], color=embed_color)

        if field_name and field_value:
            embed.add_field(name=field_name[:256], value=field_value[:1024], inline=inline)

        if image:
            embed.set_image(url=image[:2048])

        if thumbnail:
            embed.set_thumbnail(url=thumbnail[:2048])

        if footer:
            embed.set_footer(text=footer[:2048])

        target = channel or interaction.channel
        if not isinstance(target, discord.TextChannel):
            await interaction.response.send_message("Invalid target channel.", ephemeral=True)
            return

        await target.send(embed=embed)
        await interaction.response.send_message(f"{CHECK_OK} Embed sent to {target.mention}.", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(EmbedBuilderCog(bot))
