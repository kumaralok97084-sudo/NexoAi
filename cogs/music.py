from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands

from cogs.emojis import CHECK_OK, HELP_MUSIC, LEAVE_VC, LOOP, PAUSE_BUTTON, PLAYLIST, QUEUE_MUSIC, RESUME_BUTTON, SAVE_MUSIC, SHUFFLE, SKIP_TRACK, STOP_BUTTON, VOLUME

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
        self.loop = False
        self.loopqueue = False
        self.volume = 100

    async def play_next(self) -> None:
        if self.loop and self.current:
            self.queue.insert(0, self.current)
        elif self.loopqueue and self.current:
            self.queue.append(self.current)

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

            vol = max(0.0, min(2.0, self.volume / 100.0))
            self.voice.play(
                discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(url, **FFMPEG_OPTS), volume=vol),
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

    # ── Autocomplete helpers ──

    async def _queue_pos_ac(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[int]]:
        player = self._get_player(interaction.guild_id)
        if not player.queue:
            return []
        choices = []
        for i, s in enumerate(player.queue[:25], 1):
            label = f"#{i} {s['title'][:80]}"
            if current.isdigit() and current in str(i):
                choices.append(app_commands.Choice(name=label, value=i))
        return choices[:25]

    async def _playlist_ac(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[int]]:
        pls = await self.bot.db.get_user_playlists(interaction.user.id)
        choices = []
        for p in pls:
            label = f"{p['name']} (ID: {p['id']})"
            if current.lower() in p['name'].lower() or current in str(p['id']):
                choices.append(app_commands.Choice(name=label[:100], value=p['id']))
        return choices[:25]

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

    @app_commands.command(name="volume", description="Set player volume (0-200%).")
    @app_commands.describe(percent="Volume percentage (0-200)")
    async def volume(self, interaction: discord.Interaction, percent: app_commands.Range[int, 0, 200]) -> None:
        player = self._get_player(interaction.guild_id)
        player.volume = percent
        if player.voice and player.voice.is_playing():
            src = player.voice.source
            if isinstance(src, discord.PCMVolumeTransformer):
                src.volume = max(0.0, min(2.0, percent / 100.0))
        await interaction.response.send_message(f"{VOLUME} Volume set to **{percent}%**.")

    @app_commands.command(name="loop", description="Toggle looping the current song.")
    async def loop(self, interaction: discord.Interaction) -> None:
        player = self._get_player(interaction.guild_id)
        player.loop = not player.loop
        if player.loop:
            player.loopqueue = False
        state = "enabled" if player.loop else "disabled"
        await interaction.response.send_message(f"{LOOP} Loop {state}.")

    @app_commands.command(name="loopqueue", description="Toggle looping the entire queue.")
    async def loopqueue(self, interaction: discord.Interaction) -> None:
        player = self._get_player(interaction.guild_id)
        player.loopqueue = not player.loopqueue
        if player.loopqueue:
            player.loop = False
        state = "enabled" if player.loopqueue else "disabled"
        await interaction.response.send_message(f"{LOOP} Loop queue {state}.")

    @app_commands.command(name="shuffle", description="Shuffle the queue.")
    async def shuffle(self, interaction: discord.Interaction) -> None:
        import random
        player = self._get_player(interaction.guild_id)
        if len(player.queue) < 2:
            await interaction.response.send_message("Not enough songs to shuffle.", ephemeral=True)
            return
        random.shuffle(player.queue)
        await interaction.response.send_message(f"{SHUFFLE} Shuffled {len(player.queue)} songs.")

    @app_commands.command(name="seek", description="Seek to a position in the current song.")
    @app_commands.describe(seconds="Position in seconds")
    async def seek(self, interaction: discord.Interaction, seconds: int) -> None:
        player = self._get_player(interaction.guild_id)
        if not player.voice or not player.voice.is_playing():
            await interaction.response.send_message("Nothing is playing.", ephemeral=True)
            return
        player.voice.stop()
        if player.current:
            player.current["seek"] = str(seconds)
            player.queue.insert(0, player.current)
        player.current = None
        await player.play_next()
        await interaction.response.send_message(f"⏩ Seeking to {seconds}s.")

    @app_commands.command(name="remove", description="Remove a song from the queue.")
    @app_commands.describe(index="Queue position to remove (1-based)")
    @app_commands.autocomplete(index=_queue_pos_ac)
    async def remove(self, interaction: discord.Interaction, index: int) -> None:
        player = self._get_player(interaction.guild_id)
        if not 1 <= index <= len(player.queue):
            await interaction.response.send_message("Invalid queue position.", ephemeral=True)
            return
        removed = player.queue.pop(index - 1)
        await interaction.response.send_message(f"Removed **{removed['title']}** from queue.")

    @app_commands.command(name="move", description="Move a song in the queue.")
    @app_commands.describe(from_pos="Current position", to_pos="New position")
    @app_commands.autocomplete(from_pos=_queue_pos_ac)
    @app_commands.autocomplete(to_pos=_queue_pos_ac)
    async def move(self, interaction: discord.Interaction, from_pos: int, to_pos: int) -> None:
        player = self._get_player(interaction.guild_id)
        if not 1 <= from_pos <= len(player.queue) or not 1 <= to_pos <= len(player.queue):
            await interaction.response.send_message("Invalid position.", ephemeral=True)
            return
        song = player.queue.pop(from_pos - 1)
        player.queue.insert(to_pos - 1, song)
        await interaction.response.send_message(f"Moved **{song['title']}** to position {to_pos}.")

    @app_commands.command(name="save", description="Save the current song to your DMs.")
    async def save(self, interaction: discord.Interaction) -> None:
        player = self._get_player(interaction.guild_id)
        if not player.current:
            await interaction.response.send_message("Nothing is playing.", ephemeral=True)
            return
        try:
            await interaction.user.send(f"{SAVE_MUSIC} Saved song: **{player.current['title']}**\n{player.current['url']}")
            await interaction.response.send_message(f"{SAVE_MUSIC} Song saved to your DMs!", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("I can't DM you. Enable DMs from server members.", ephemeral=True)

    # ── Playlist Commands ──

    @app_commands.command(name="playlist_create", description="Create a new playlist.")
    @app_commands.describe(name="Playlist name")
    async def playlist_create(self, interaction: discord.Interaction, name: str) -> None:
        pid = await self.bot.db.create_playlist(interaction.user.id, name)
        await interaction.response.send_message(f"{PLAYLIST} Playlist **{name}** created (ID: {pid}).", ephemeral=True)

    @app_commands.command(name="playlist_add", description="Add current song to a playlist.")
    @app_commands.describe(playlist_id="Playlist ID")
    @app_commands.autocomplete(playlist_id=_playlist_ac)
    async def playlist_add(self, interaction: discord.Interaction, playlist_id: int) -> None:
        player = self._get_player(interaction.guild_id)
        if not player.current:
            await interaction.response.send_message("Nothing is playing.", ephemeral=True)
            return
        pl = await self.bot.db.get_playlist(playlist_id)
        if not pl:
            await interaction.response.send_message("Playlist not found.", ephemeral=True)
            return
        if pl["user_id"] != interaction.user.id:
            await interaction.response.send_message("That's not your playlist.", ephemeral=True)
            return
        songs = json.loads(pl["songs"] or "[]")
        songs.append(player.current)
        await self.bot.db.update_playlist_songs(playlist_id, json.dumps(songs))
        await interaction.response.send_message(f"Added **{player.current['title']}** to **{pl['name']}**.", ephemeral=True)

    @app_commands.command(name="playlist_remove", description="Remove a song from a playlist.")
    @app_commands.describe(playlist_id="Playlist ID", index="Song index (1-based)")
    @app_commands.autocomplete(playlist_id=_playlist_ac)
    async def playlist_remove(self, interaction: discord.Interaction, playlist_id: int, index: int) -> None:
        pl = await self.bot.db.get_playlist(playlist_id)
        if not pl or pl["user_id"] != interaction.user.id:
            await interaction.response.send_message("Playlist not found or not yours.", ephemeral=True)
            return
        songs = json.loads(pl["songs"] or "[]")
        if not 1 <= index <= len(songs):
            await interaction.response.send_message("Invalid index.", ephemeral=True)
            return
        removed = songs.pop(index - 1)
        await self.bot.db.update_playlist_songs(playlist_id, json.dumps(songs))
        await interaction.response.send_message(f"Removed **{removed['title']}** from **{pl['name']}**.", ephemeral=True)

    @app_commands.command(name="playlist_view", description="View a playlist.")
    @app_commands.describe(playlist_id="Playlist ID")
    @app_commands.autocomplete(playlist_id=_playlist_ac)
    async def playlist_view(self, interaction: discord.Interaction, playlist_id: int) -> None:
        pl = await self.bot.db.get_playlist(playlist_id)
        if not pl or pl["user_id"] != interaction.user.id:
            await interaction.response.send_message("Playlist not found.", ephemeral=True)
            return
        songs = json.loads(pl["songs"] or "[]")
        lines = [f"`{i+1}.` {s['title']}" for i, s in enumerate(songs[:20])]
        if not lines:
            lines = ["(empty)"]
        embed = discord.Embed(title=f"{PLAYLIST} {pl['name']}", description="\n".join(lines), color=discord.Color.teal())
        embed.set_footer(text=f"{len(songs)} songs")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="playlist_play", description="Load a playlist into the queue.")
    @app_commands.describe(playlist_id="Playlist ID")
    @app_commands.autocomplete(playlist_id=_playlist_ac)
    async def playlist_play(self, interaction: discord.Interaction, playlist_id: int) -> None:
        pl = await self.bot.db.get_playlist(playlist_id)
        if not pl or pl["user_id"] != interaction.user.id:
            await interaction.response.send_message("Playlist not found.", ephemeral=True)
            return
        songs = json.loads(pl["songs"] or "[]")
        if not songs:
            await interaction.response.send_message("Playlist is empty.", ephemeral=True)
            return
        player = self._get_player(interaction.guild_id)
        for song in songs:
            player.queue.append(dict(song))
        if not player._playing:
            await player.play_next()
        await interaction.response.send_message(f"Loaded {len(songs)} songs from **{pl['name']}** into queue.")

    @app_commands.command(name="playlist_delete", description="Delete a playlist.")
    @app_commands.describe(playlist_id="Playlist ID")
    @app_commands.autocomplete(playlist_id=_playlist_ac)
    async def playlist_delete(self, interaction: discord.Interaction, playlist_id: int) -> None:
        pl = await self.bot.db.get_playlist(playlist_id)
        if not pl or pl["user_id"] != interaction.user.id:
            await interaction.response.send_message("Playlist not found or not yours.", ephemeral=True)
            return
        await self.bot.db.delete_playlist(playlist_id)
        await interaction.response.send_message(f"Playlist **{pl['name']}** deleted.", ephemeral=True)

    @app_commands.command(name="join", description="Join your voice channel.")
    async def join(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        voice = await self._ensure_voice(interaction)
        if voice:
            await interaction.followup.send(f"{CHECK_OK} Joined {voice.channel.mention}.", ephemeral=True)

    @app_commands.command(name="disconnect", description="Leave the voice channel.")
    async def disconnect(self, interaction: discord.Interaction) -> None:
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
