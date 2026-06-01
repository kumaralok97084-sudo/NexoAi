from __future__ import annotations

import asyncio
import logging
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands

from cogs.emojis import CHECK_OK, HELP_MUSIC, LEAVE_VC, PAUSE_BUTTON, QUEUE_MUSIC, RESUME_BUTTON, SKIP_TRACK, STOP_BUTTON

logger = logging.getLogger(__name__)

try:
    import yt_dlp
except ImportError:
    yt_dlp = None  # type: ignore[assignment]

YTDL_SEARCH_OPTS: dict[str, Any] = {
    "format": "bestaudio/best",
    "quiet": True,
    "no_warnings": True,
    "extract_flat": "in_playlist",
}

YTDL_PLAY_OPTS: dict[str, Any] = {
    "format": "bestaudio/best",
    "quiet": True,
    "no_warnings": True,
}

FFMPEG_OPTS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}


class MusicPlayer:
    def __init__(self, bot: commands.Bot, guild_id: int) -> None:
        self.bot = bot
        self.guild_id = guild_id
        self.queue: list[dict[str, str]] = []
        self.current: dict[str, str] | None = None
        self.voice: discord.VoiceClient | None = None
        self._playing = False

    async def play_next(self) -> None:
        if not self.queue:
            self._playing = False
            self.current = None
            return

        self.current = self.queue.pop(0)
        self._playing = True

        if not self.voice or not self.voice.is_connected():
            self._playing = False
            return

        try:
            if yt_dlp:
                with yt_dlp.YoutubeDL(YTDL_PLAY_OPTS) as ydl:
                    info = ydl.extract_info(self.current["url"], download=False)
                    url = info["url"]
            else:
                url = self.current["url"]

            self.voice.play(
                discord.FFmpegPCMAudio(url, **FFMPEG_OPTS),
                after=lambda e: asyncio.run_coroutine_threadsafe(self._after_play(e), self.bot.loop),
            )
        except Exception as exc:
            logger.error("Playback error: %s", exc)
            self._playing = False
            self.current = None
            if self.voice:
                await self.voice.disconnect()

    async def _after_play(self, error: Exception | None) -> None:
        if error:
            logger.error("FFmpeg error: %s", error)
        self.current = None
        await self.play_next()


class MusicCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.players: dict[int, MusicPlayer] = {}

    def _get_player(self, guild_id: int) -> MusicPlayer:
        if guild_id not in self.players:
            self.players[guild_id] = MusicPlayer(self.bot, guild_id)
        return self.players[guild_id]

    async def _ensure_voice(self, interaction: discord.Interaction) -> discord.VoiceClient | None:
        if not isinstance(interaction.user, discord.Member) or not interaction.user.voice:
            await interaction.followup.send("You need to be in a voice channel first.")
            return None

        player = self._get_player(interaction.guild_id)
        if player.voice and player.voice.is_connected():
            if player.voice.channel != interaction.user.voice.channel:
                await player.voice.move_to(interaction.user.voice.channel)
            return player.voice

        try:
            player.voice = await interaction.user.voice.channel.connect()
            return player.voice
        except discord.Forbidden:
            await interaction.followup.send("I don't have permission to join that voice channel.")
            return None
        except Exception as exc:
            await interaction.followup.send(f"Failed to join: {exc}")
            return None

    @app_commands.command(name="play", description="Play a song from YouTube.")
    async def play(self, interaction: discord.Interaction, query: str) -> None:
        if yt_dlp is None:
            await interaction.response.send_message("Music requires `yt-dlp`. Install it with `pip install yt-dlp`.", ephemeral=True)
            return

        await interaction.response.defer()
        voice = await self._ensure_voice(interaction)
        if not voice:
            return

        player = self._get_player(interaction.guild_id)
        player.voice = voice

        try:
            with yt_dlp.YoutubeDL(YTDL_SEARCH_OPTS) as ydl:
                info = ydl.extract_info(f"ytsearch:{query}", download=False)["entries"][0]
                title = info.get("title", "Unknown")
                url = info.get("webpage_url", info.get("url", ""))
                duration = info.get("duration", 0)
        except Exception as exc:
            await interaction.followup.send(f"Could not find: {exc}")
            return

        song = {"title": title, "url": url, "duration": str(duration)}
        player.queue.append(song)

        if not player._playing:
            await player.play_next()
            await interaction.followup.send(f"{RESUME_BUTTON} Now playing: **{title}**")
        else:
            pos = len(player.queue)
            await interaction.followup.send(f"{HELP_MUSIC} Added to queue at position #{pos}: **{title}**")

    @app_commands.command(name="skip", description="Skip the current song.")
    async def skip(self, interaction: discord.Interaction) -> None:
        player = self._get_player(interaction.guild_id)
        if player.voice and player.voice.is_playing():
            player.voice.stop()
            await interaction.response.send_message(f"{SKIP_TRACK} Skipped.")
        else:
            await interaction.response.send_message("Nothing is playing.", ephemeral=True)

    @app_commands.command(name="queue", description="Show the music queue.")
    async def queue_cmd(self, interaction: discord.Interaction) -> None:
        player = self._get_player(interaction.guild_id)
        if not player.queue:
            if player._playing and player.current:
                await interaction.response.send_message(f"{RESUME_BUTTON} Now playing: **{player.current['title']}**\nQueue is empty.")
            else:
                await interaction.response.send_message("Queue is empty.", ephemeral=True)
            return

        lines = []
        if player.current:
            lines.append(f"{RESUME_BUTTON} **Now:** {player.current['title']}")
        for i, song in enumerate(player.queue[:10], 1):
            lines.append(f"{i}. {song['title']}")
        if len(player.queue) > 10:
            lines.append(f"... and {len(player.queue) - 10} more")

        await interaction.response.send_message(f"{QUEUE_MUSIC} **Music Queue**\n" + "\n".join(lines))

    @app_commands.command(name="stop", description="Stop playback and clear the queue.")
    async def stop(self, interaction: discord.Interaction) -> None:
        player = self._get_player(interaction.guild_id)
        player.queue.clear()
        if player.voice and player.voice.is_playing():
            player.voice.stop()
        if player.voice and player.voice.is_connected():
            await player.voice.disconnect()
        player.voice = None
        player._playing = False
        player.current = None
        await interaction.response.send_message(f"{STOP_BUTTON} Stopped and left the voice channel.")

    @app_commands.command(name="pause", description="Pause the current song.")
    async def pause(self, interaction: discord.Interaction) -> None:
        player = self._get_player(interaction.guild_id)
        if player.voice and player.voice.is_playing():
            player.voice.pause()
            await interaction.response.send_message(f"{PAUSE_BUTTON} Paused.")
        else:
            await interaction.response.send_message("Nothing is playing.", ephemeral=True)

    @app_commands.command(name="resume", description="Resume the paused song.")
    async def resume(self, interaction: discord.Interaction) -> None:
        player = self._get_player(interaction.guild_id)
        if player.voice and player.voice.is_paused():
            player.voice.resume()
            await interaction.response.send_message(f"{RESUME_BUTTON} Resumed.")
        else:
            await interaction.response.send_message("Nothing is paused.", ephemeral=True)

    @app_commands.command(name="nowplaying", description="Show the currently playing song.")
    async def now_playing(self, interaction: discord.Interaction) -> None:
        player = self._get_player(interaction.guild_id)
        if player._playing and player.current:
            await interaction.response.send_message(f"{RESUME_BUTTON} Now playing: **{player.current['title']}**")
        else:
            await interaction.response.send_message("Nothing is playing.", ephemeral=True)

    @app_commands.command(name="join", description="Join your voice channel.")
    async def join(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        voice = await self._ensure_voice(interaction)
        if voice:
            await interaction.followup.send(f"{CHECK_OK} Joined {voice.channel.mention}.", ephemeral=True)

    @app_commands.command(name="leave", description="Leave the voice channel.")
    async def leave(self, interaction: discord.Interaction) -> None:
        player = self._get_player(interaction.guild_id)
        player.queue.clear()
        if player.voice and player.voice.is_connected():
            await player.voice.disconnect()
        player.voice = None
        player._playing = False
        player.current = None
        await interaction.response.send_message(f"{LEAVE_VC} Left the voice channel.")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MusicCog(bot))
