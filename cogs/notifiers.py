from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

import aiosqlite
import discord
from discord import app_commands
from discord.ext import commands

from cogs.emojis import CHECK_OK

logger = logging.getLogger(__name__)

POLL_INTERVAL = 300

try:
    import feedparser
except ImportError:
    feedparser = None  # type: ignore[assignment]


class NotifiersCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._poll_task: asyncio.Task | None = None

    async def cog_load(self) -> None:
        self._poll_task = asyncio.create_task(self._poll_feeds())

    async def cog_unload(self) -> None:
        if self._poll_task:
            self._poll_task.cancel()

    async def _poll_feeds(self) -> None:
        if feedparser is None:
            return
        while True:
            try:
                await asyncio.sleep(POLL_INTERVAL)
                async with aiosqlite.connect(self.bot.db.db_path) as db:
                    async with db.execute("SELECT id, guild_id, channel_id, platform, target, last_checked FROM subscriptions") as cursor:
                        subs = await cursor.fetchall()

                for sid, guild_id, channel_id, platform, target, last_checked in subs:
                    try:
                        guild = self.bot.get_guild(guild_id)
                        channel = guild.get_channel(channel_id) if guild else None
                        if not channel:
                            continue

                        if platform == "youtube":
                            feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={target}"
                        elif platform == "rss":
                            feed_url = target
                        else:
                            continue

                        feed = feedparser.parse(feed_url)
                        if not feed.entries:
                            continue

                        latest = feed.entries[0]
                        published = latest.get("published", latest.get("updated", ""))
                        if not last_checked or published > last_checked:
                            video_id = latest.get("yt_videoid", latest.get("id", ""))
                            link = latest.get("link", f"https://youtube.com/watch?v={video_id}")
                            title = latest.get("title", "New video")
                            author = latest.get("author", "")

                            embed = discord.Embed(
                                title=title[:256],
                                url=link,
                                color=discord.Color.red() if platform == "youtube" else discord.Color.blue(),
                            )
                            embed.set_author(name=author)
                            if platform == "youtube" and video_id:
                                embed.set_image(url=f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg")

                            await channel.send(embed=embed)

                        async with aiosqlite.connect(self.bot.db.db_path) as db2:
                            await db2.execute(
                                "UPDATE subscriptions SET last_checked = ? WHERE id = ?",
                                (published or datetime.now(timezone.utc).isoformat(), sid),
                            )
                            await db2.commit()
                    except Exception as exc:
                        logger.debug("Feed check error for sub %s: %s", sid, exc)

            except asyncio.CancelledError:
                break
            except Exception:
                pass

    # ---- Commands ----

    subscribe = app_commands.Group(name="subscribe", description="Subscribe to notifications.")

    @subscribe.command(name="youtube", description="Get notified when a YouTube channel uploads.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def sub_youtube(self, interaction: discord.Interaction, channel_id: str, channel: discord.TextChannel) -> None:
        if feedparser is None:
            await interaction.response.send_message("`feedparser` is not installed. Run `pip install feedparser`.", ephemeral=True)
            return
        if not interaction.guild:
            await interaction.response.send_message("Server only.", ephemeral=True)
            return
        try:
            async with aiosqlite.connect(self.bot.db.db_path) as db:
                await db.execute(
                    "INSERT OR REPLACE INTO subscriptions (guild_id, channel_id, platform, target) VALUES (?, ?, 'youtube', ?)",
                    (interaction.guild.id, channel.id, channel_id),
                )
                await db.commit()
            await interaction.response.send_message(f"{CHECK_OK} Notifications for YouTube channel `{channel_id}` will post in {channel.mention}.", ephemeral=True)
        except aiosqlite.IntegrityError:
            await interaction.response.send_message("Already subscribed.", ephemeral=True)

    @subscribe.command(name="rss", description="Get notified from an RSS feed.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def sub_rss(self, interaction: discord.Interaction, feed_url: str, channel: discord.TextChannel) -> None:
        if feedparser is None:
            await interaction.response.send_message("`feedparser` is not installed. Run `pip install feedparser`.", ephemeral=True)
            return
        if not interaction.guild:
            await interaction.response.send_message("Server only.", ephemeral=True)
            return
        try:
            async with aiosqlite.connect(self.bot.db.db_path) as db:
                await db.execute(
                    "INSERT OR REPLACE INTO subscriptions (guild_id, channel_id, platform, target) VALUES (?, ?, 'rss', ?)",
                    (interaction.guild.id, channel.id, feed_url),
                )
                await db.commit()
            await interaction.response.send_message(f"{CHECK_OK} RSS feed `{feed_url}` will post updates in {channel.mention}.", ephemeral=True)
        except aiosqlite.IntegrityError:
            await interaction.response.send_message("Already subscribed.", ephemeral=True)

    @subscribe.command(name="list", description="List all subscriptions.")
    async def sub_list(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Server only.", ephemeral=True)
            return
        async with aiosqlite.connect(self.bot.db.db_path) as db:
            async with db.execute(
                "SELECT id, channel_id, platform, target FROM subscriptions WHERE guild_id = ?",
                (interaction.guild.id,),
            ) as cursor:
                rows = await cursor.fetchall()
        if not rows:
            await interaction.response.send_message("No subscriptions.", ephemeral=True)
            return
        lines = [f"`#{s[0]}` {s[2]}: `{s[3]}` → <#{s[1]}>" for s in rows]
        await interaction.response.send_message("**Subscriptions**\n" + "\n".join(lines), ephemeral=True)

    @app_commands.command(name="unsubscribe", description="Remove a subscription by ID.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def unsubscribe(self, interaction: discord.Interaction, subscription_id: int) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Server only.", ephemeral=True)
            return
        async with aiosqlite.connect(self.bot.db.db_path) as db:
            await db.execute(
                "DELETE FROM subscriptions WHERE id = ? AND guild_id = ?",
                (subscription_id, interaction.guild.id),
            )
            await db.commit()
        await interaction.response.send_message(f"{CHECK_OK} Removed subscription `#{subscription_id}`.", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(NotifiersCog(bot))
