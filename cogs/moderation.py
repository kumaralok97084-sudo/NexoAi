from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands

SCAM_KEYWORDS = (
    "discord.gift",
    "free nitro",
    "steamcommunity.com/gift",
    "airdrop",
    "claim reward",
)

ABUSIVE_KEYWORDS = (
    "bc", "bsdk", "mc", "madarchod", "bhenchod", "bhosdike", "chutiya", "gaand",
    "lauda", "loda", "randi", "bhadva", "kutte", "kutti", "sala", "harami",
    "fuck", "shit", "asshole", "bastard", "bitch", "motherfucker", "dick",
    "pussy", "cunt", "whore", "slut", "nigga", "nigger",
)

ATTACHMENT_TYPES_IMAGE = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif")
ATTACHMENT_TYPES_GIF = (".gif",)


class ModerationCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._moderation_queue: asyncio.Queue[discord.Message] = asyncio.Queue()
        self._moderation_task: asyncio.Task[None] | None = None

    async def cog_load(self) -> None:
        self._moderation_task = asyncio.create_task(self._process_moderation_queue())

    async def cog_unload(self) -> None:
        if self._moderation_task:
            self._moderation_task.cancel()

    async def _process_moderation_queue(self) -> None:
        while True:
            try:
                message = await self._moderation_queue.get()
                await self._check_message_ai(message)
            except asyncio.CancelledError:
                break
            except Exception:
                pass

    async def check_message(self, message: discord.Message) -> None:
        if not message.guild or message.author.bot:
            return
        content = message.content.lower()

        if any(keyword in content for keyword in SCAM_KEYWORDS):
            try:
                await message.delete()
                await message.channel.send(
                    f"{message.author.mention}, your message looked like a scam link and was removed.",
                    delete_after=5,
                )
                await self.bot.db.add_moderation_log(
                    message.guild.id, message.author.id, "scam_delete",
                    "Scam keyword detected", message.content[:200],
                )
            except discord.Forbidden:
                pass
            return

        # Custom filter check
        custom_filters = await self.bot.db.get_filters(message.guild.id)
        for cf in custom_filters:
            if cf["pattern"].lower() in content:
                try:
                    await message.delete()
                    await message.channel.send(
                        f"{message.author.mention}, your message matched a filter: `{cf['pattern']}`",
                        delete_after=5,
                    )
                    await self.bot.db.add_moderation_log(
                        message.guild.id, message.author.id, "filter",
                        f"Custom filter: {cf['pattern']}", message.content[:200],
                    )
                except discord.Forbidden:
                    pass
                return

        is_flagged_quick = any(keyword in content for keyword in ABUSIVE_KEYWORDS)
        has_attachment = bool(message.attachments)

        if is_flagged_quick or has_attachment:
            await self._moderation_queue.put(message)

    async def _check_message_ai(self, message: discord.Message) -> None:
        if not message.guild:
            return

        content = message.content.strip()
        user_id = message.author.id
        guild_id = message.guild.id
        flagged = False
        reason = "none"

        if content:
            flagged, reason = await self.bot.llm.moderate_text(content)

        if not flagged and message.attachments:
            for attachment in message.attachments:
                ext = f".{attachment.filename.lower().rsplit('.', 1)[-1]}" if "." in attachment.filename else ""
                if ext in ATTACHMENT_TYPES_IMAGE:
                    flagged, reason = await self._check_attachment_nsfw(attachment)
                    if flagged:
                        break

        if not flagged:
            return

        await self._handle_flagged(message, reason)

    async def _check_attachment_nsfw(self, attachment: discord.Attachment) -> tuple[bool, str]:
        try:
            if attachment.size > 8 * 1024 * 1024:
                return False, "too large"
            flagged, reason = await self.bot.llm.moderate_image_url(attachment.url)
            return flagged, reason
        except Exception:
            return False, "none"

    async def _handle_flagged(self, message: discord.Message, reason: str) -> None:
        if not message.guild:
            return

        user_id = message.author.id
        guild_id = message.guild.id

        try:
            await message.delete()
        except discord.Forbidden:
            pass

        await self.bot.db.add_warn(guild_id, user_id, reason, self.bot.user.id if self.bot.user else 0)
        await self.bot.db.add_moderation_log(guild_id, user_id, f"auto_{reason}", reason, message.content[:200])

        warn_count = await self.bot.db.count_warns(guild_id, user_id)
        max_warns = self.bot.settings.moderation_max_warns

        channel_notify = (
            f"{message.author.mention} **Auto-Moderated** | Reason: `{reason}` "
            f"(Warning {warn_count}/{max_warns})"
        )
        try:
            await message.channel.send(channel_notify, delete_after=10)
        except discord.Forbidden:
            pass

        try:
            await message.author.send(
                f"Your message in **{message.guild.name}** was removed.\n"
                f"Reason: `{reason}`\n"
                f"Warning: {warn_count}/{max_warns}\n"
                f"Content: `{message.content[:200]}`"
            )
        except discord.Forbidden:
            pass

        if warn_count >= max_warns:
            try:
                member = message.guild.get_member(user_id) or await message.guild.fetch_member(user_id)
                if member:
                    timeout_mins = self.bot.settings.moderation_timeout_minutes
                    until = discord.utils.utcnow() + timedelta(minutes=timeout_mins)
                    await member.timeout(until, reason=f"Auto-timeout: Reached {max_warns} warns ({reason})")
                    await self.bot.db.clear_warns(guild_id, user_id)
                    await self.bot.db.add_moderation_log(
                        guild_id, user_id, "auto_timeout",
                        f"Auto-timeout {timeout_mins}min - {reason}", "",
                    )
                    try:
                        await message.channel.send(
                            f"{member.mention} has been timed out for {timeout_mins} minutes "
                            f"(reached {max_warns} warns).",
                            delete_after=10,
                        )
                    except discord.Forbidden:
                        pass
            except (discord.Forbidden, discord.HTTPException):
                pass

    # ---- Existing Commands ----

    @app_commands.command(name="purge", description="Delete recent messages.")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def purge(self, interaction: discord.Interaction, amount: app_commands.Range[int, 1, 100]) -> None:
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("Use in a text channel.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.followup.send(f"Deleted {len(deleted)} messages.", ephemeral=True)

    @app_commands.command(name="timeout", description="Timeout a member.")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def timeout(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        minutes: app_commands.Range[int, 1, 10080],
        reason: str = "No reason provided",
    ) -> None:
        until = discord.utils.utcnow() + timedelta(minutes=minutes)
        await member.timeout(until, reason=reason)
        await self.bot.db.add_moderation_log(
            interaction.guild_id, member.id, "timeout", reason, f"Duration: {minutes}min",
        )
        await interaction.response.send_message(
            f"{member.mention} has been timed out for {minutes} minutes."
        )

    @app_commands.command(name="untimeout", description="Remove timeout from a member.")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def untimeout(
        self, interaction: discord.Interaction, member: discord.Member
    ) -> None:
        await member.timeout(None, reason=f"Removed by {interaction.user}")
        await self.bot.db.add_moderation_log(
            interaction.guild_id, member.id, "untimeout", f"Removed by {interaction.user}", "",
        )
        await interaction.response.send_message(f"Timeout removed for {member.mention}.")

    @app_commands.command(name="warn", description="Warn a member and track count.")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def warn(
        self, interaction: discord.Interaction, member: discord.Member, reason: str
    ) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Server only command.", ephemeral=True)
            return

        total_warns = await self.bot.db.count_warns(interaction.guild.id, member.id)
        await self.bot.db.add_warn(interaction.guild.id, member.id, reason, interaction.user.id)
        total_warns += 1
        max_warns = self.bot.settings.moderation_max_warns

        await interaction.response.send_message(
            f"{member.mention} warned. Reason: `{reason}` (Total warns: {total_warns}/{max_warns})"
        )
        try:
            await member.send(
                f"You were warned in **{interaction.guild.name}**: {reason}\n"
                f"Total warns: {total_warns}/{max_warns}"
            )
        except discord.Forbidden:
            pass

    @app_commands.command(name="warns", description="Check warns for a member.")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def warns(
        self, interaction: discord.Interaction, member: discord.Member
    ) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Server only command.", ephemeral=True)
            return
        warns = await self.bot.db.get_warns(interaction.guild.id, member.id)
        if not warns:
            await interaction.response.send_message(
                f"{member.mention} has no warns.", ephemeral=True
            )
            return
        lines = [f"`#{w['id']}` {w['reason']}" for w in warns[:20]]
        embed = discord.Embed(
            title=f"Warns for {member}",
            description="\n".join(lines),
            color=discord.Color.orange(),
        )
        embed.set_footer(text=f"Total: {len(warns)}")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="unwarn", description="Remove the latest warn for a member.")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def unwarn(
        self, interaction: discord.Interaction, member: discord.Member
    ) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Server only command.", ephemeral=True)
            return
        warns = await self.bot.db.get_warns(interaction.guild.id, member.id)
        if not warns:
            await interaction.response.send_message(
                f"{member.mention} has no warns to remove.", ephemeral=True
            )
            return
        latest = warns[0]
        await self.bot.db.delete_warn(latest["id"])
        await interaction.response.send_message(
            f"Removed latest warn from {member.mention}: `{latest['reason']}`", ephemeral=True
        )

    # ---- Custom Filters ----

    @app_commands.command(name="filter", description="Manage custom word filters.")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def filter_cmd(self, interaction: discord.Interaction, action: str, pattern: str | None = None) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Server only.", ephemeral=True)
            return
        gid = interaction.guild.id
        if action == "add" and pattern:
            await self.bot.db.add_filter(gid, pattern, "warn")
            await interaction.response.send_message(f"Filter added: `{pattern}`", ephemeral=True)
        elif action == "remove" and pattern:
            filters = await self.bot.db.get_filters(gid)
            for f in filters:
                if f["pattern"] == pattern:
                    await self.bot.db.remove_filter(f["id"])
                    await interaction.response.send_message(f"Filter removed: `{pattern}`", ephemeral=True)
                    return
            await interaction.response.send_message(f"Filter not found: `{pattern}`", ephemeral=True)
        elif action == "list":
            filters = await self.bot.db.get_filters(gid)
            if not filters:
                await interaction.response.send_message("No custom filters set.", ephemeral=True)
                return
            lines = [f"`#{f['id']}` `{f['pattern']}` -> {f['action']}" for f in filters]
            await interaction.response.send_message("**Custom Filters**\n" + "\n".join(lines), ephemeral=True)
        else:
            await interaction.response.send_message("Usage: add <pattern>, remove <pattern>, list", ephemeral=True)

    @app_commands.command(name="filtermode", description="Set filter strictness.")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def filter_mode(self, interaction: discord.Interaction, mode: str) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Server only.", ephemeral=True)
            return
        mode = mode.lower()
        if mode not in ("strict", "relaxed", "off"):
            await interaction.response.send_message("Mode must be: strict, relaxed, or off", ephemeral=True)
            return
        await self.bot.db.upsert_guild_setting(interaction.guild.id, "filter_mode", mode)
        await interaction.response.send_message(f"Filter mode set to `{mode}`.", ephemeral=True)

    # ---- Raid Protection ----

    @app_commands.command(name="raidmode", description="Toggle raid protection mode.")
    @app_commands.checks.has_permissions(administrator=True)
    async def raid_mode(self, interaction: discord.Interaction, enabled: bool) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Server only.", ephemeral=True)
            return
        await self.bot.db.upsert_guild_setting(interaction.guild.id, "raid_mode", str(int(enabled)))
        status = "enabled" if enabled else "disabled"
        await interaction.response.send_message(f"Raid mode {status}.", ephemeral=True)
        if enabled:
            for channel in interaction.guild.text_channels:
                try:
                    await channel.set_permissions(interaction.guild.default_role, send_messages=False)
                except discord.Forbidden:
                    pass

    @app_commands.command(name="lockdown", description="Lock all text channels in the server.")
    @app_commands.checks.has_permissions(administrator=True)
    async def lockdown(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Server only.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        count = 0
        for channel in interaction.guild.text_channels:
            try:
                await channel.set_permissions(interaction.guild.default_role, send_messages=False)
                count += 1
            except discord.Forbidden:
                pass
        await interaction.followup.send(f"🔒 Locked {count} channels.", ephemeral=True)

    @app_commands.command(name="unlockall", description="Unlock all text channels.")
    @app_commands.checks.has_permissions(administrator=True)
    async def unlock_all(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Server only.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        count = 0
        for channel in interaction.guild.text_channels:
            try:
                await channel.set_permissions(interaction.guild.default_role, send_messages=None)
                count += 1
            except discord.Forbidden:
                pass
        await interaction.followup.send(f"🔓 Unlocked {count} channels.", ephemeral=True)

    @app_commands.command(name="antispam", description="Toggle anti-spam protection.")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def antispam(self, interaction: discord.Interaction, enabled: bool) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Server only.", ephemeral=True)
            return
        await self.bot.db.upsert_guild_setting(interaction.guild.id, "antispam_enabled", str(int(enabled)))
        status = "enabled" if enabled else "disabled"
        await interaction.response.send_message(f"Anti-spam {status}.", ephemeral=True)

    @app_commands.command(name="modsettings", description="View current moderation settings.")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def mod_settings(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Server only.", ephemeral=True)
            return
        gid = interaction.guild.id
        raid = await self.bot.db.get_guild_setting(gid, "raid_mode")
        spam = await self.bot.db.get_guild_setting(gid, "antispam_enabled")
        fmode = await self.bot.db.get_guild_setting(gid, "filter_mode")
        filters = await self.bot.db.get_filters(gid)
        embed = discord.Embed(title="Moderation Settings", color=discord.Color.orange())
        embed.add_field(name="Max Warns", value=str(self.bot.settings.moderation_max_warns), inline=True)
        embed.add_field(name="Timeout Duration", value=f"{self.bot.settings.moderation_timeout_minutes}min", inline=True)
        embed.add_field(name="Raid Mode", value="✅ On" if raid == "1" else "❌ Off", inline=True)
        embed.add_field(name="Anti-Spam", value="✅ On" if spam == "1" else "❌ Off", inline=True)
        embed.add_field(name="Filter Mode", value=fmode or "relaxed", inline=True)
        embed.add_field(name="Custom Filters", value=str(len(filters)), inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="modlogs", description="View moderation logs for a member.")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def modlogs(
        self, interaction: discord.Interaction, member: discord.Member
    ) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Server only command.", ephemeral=True)
            return
        logs = await self.bot.db.get_moderation_logs(interaction.guild.id, member.id)
        if not logs:
            await interaction.response.send_message(
                f"No moderation logs for {member.mention}.", ephemeral=True
            )
            return
        lines = [f"`{l['action']}` - {l['reason']}" for l in logs[:15]]
        embed = discord.Embed(
            title=f"Mod Logs for {member}",
            description="\n".join(lines),
            color=discord.Color.red(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ---- New Moderation Commands ----

    @app_commands.command(name="slowmode", description="Set slowmode on the current channel.")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def slowmode(
        self, interaction: discord.Interaction, seconds: app_commands.Range[int, 0, 21600]
    ) -> None:
        if not isinstance(interaction.channel, (discord.TextChannel, discord.Thread)):
            await interaction.response.send_message("Use in a text channel.", ephemeral=True)
            return
        await interaction.channel.edit(slowmode_delay=seconds)
        if seconds == 0:
            await interaction.response.send_message("Slowmode removed.")
        else:
            await interaction.response.send_message(f"Slowmode set to {seconds} seconds.")

    @app_commands.command(name="lock", description="Lock a channel (deny send messages).")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def lock(self, interaction: discord.Interaction, channel: discord.TextChannel | None = None) -> None:
        target = channel or interaction.channel
        if not isinstance(target, discord.TextChannel):
            await interaction.response.send_message("Use in a text channel.", ephemeral=True)
            return
        await target.set_permissions(target.guild.default_role, send_messages=False)
        await interaction.response.send_message(f"{target.mention} has been locked.")

    @app_commands.command(name="unlock", description="Unlock a channel (allow send messages).")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def unlock(self, interaction: discord.Interaction, channel: discord.TextChannel | None = None) -> None:
        target = channel or interaction.channel
        if not isinstance(target, discord.TextChannel):
            await interaction.response.send_message("Use in a text channel.", ephemeral=True)
            return
        await target.set_permissions(target.guild.default_role, send_messages=None)
        await interaction.response.send_message(f"{target.mention} has been unlocked.")

    @app_commands.command(name="kick", description="Kick a member from the server.")
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick(
        self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"
    ) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Server only command.", ephemeral=True)
            return
        if member.top_role >= interaction.user.top_role and interaction.user.id != interaction.guild.owner_id:
            await interaction.response.send_message("You cannot kick this member.", ephemeral=True)
            return
        await member.kick(reason=reason)
        await self.bot.db.add_moderation_log(interaction.guild.id, member.id, "kick", reason, "")
        await interaction.response.send_message(f"{member} has been kicked. Reason: {reason}")

    @app_commands.command(name="ban", description="Ban a member from the server.")
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban(
        self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided",
        delete_messages: app_commands.Range[int, 0, 7] = 0,
    ) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Server only command.", ephemeral=True)
            return
        if member.top_role >= interaction.user.top_role and interaction.user.id != interaction.guild.owner_id:
            await interaction.response.send_message("You cannot ban this member.", ephemeral=True)
            return
        await member.ban(reason=reason, delete_message_days=delete_messages)
        await self.bot.db.add_moderation_log(interaction.guild.id, member.id, "ban", reason, f"delete_days:{delete_messages}")
        await interaction.response.send_message(f"{member} has been banned. Reason: {reason}")

    @app_commands.command(name="unban", description="Unban a user by ID.")
    @app_commands.checks.has_permissions(ban_members=True)
    async def unban(self, interaction: discord.Interaction, user_id: str, reason: str = "No reason provided") -> None:
        if not interaction.guild:
            await interaction.response.send_message("Server only command.", ephemeral=True)
            return
        try:
            uid = int(user_id)
        except ValueError:
            await interaction.response.send_message("Invalid user ID. Provide a numeric ID.", ephemeral=True)
            return
        try:
            user = await self.bot.fetch_user(uid)
            await interaction.guild.unban(user, reason=reason)
            await self.bot.db.add_moderation_log(interaction.guild.id, uid, "unban", reason, "")
            await interaction.response.send_message(f"{user} has been unbanned.")
        except discord.NotFound:
            await interaction.response.send_message("User not found or not banned.", ephemeral=True)
        except Exception as exc:
            await interaction.response.send_message(f"Failed to unban: {exc}", ephemeral=True)

    @app_commands.command(name="clean", description="Delete recent messages from a specific user.")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def clean(
        self, interaction: discord.Interaction, member: discord.Member, limit: app_commands.Range[int, 1, 100] = 20
    ) -> None:
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("Use in a text channel.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)

        def check(msg: discord.Message) -> bool:
            return msg.author.id == member.id

        deleted = await interaction.channel.purge(limit=limit, check=check)
        await interaction.followup.send(f"Deleted {len(deleted)} messages from {member}.", ephemeral=True)

    @app_commands.command(name="nick", description="Change a member's nickname.")
    @app_commands.checks.has_permissions(manage_nicknames=True)
    async def nick(
        self, interaction: discord.Interaction, member: discord.Member, nickname: str
    ) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Server only command.", ephemeral=True)
            return
        try:
            old = member.display_name
            await member.edit(nick=nickname[:32])
            await self.bot.db.add_moderation_log(
                interaction.guild.id, member.id, "nick", f"Changed from '{old}' to '{nickname}'", "",
            )
            await interaction.response.send_message(f"Changed {member.mention}'s nickname to `{nickname}`.")
        except discord.Forbidden:
            await interaction.response.send_message("I don't have permission to change that nickname.", ephemeral=True)

    @app_commands.command(name="softban", description="Ban and immediately unban (clears recent messages).")
    @app_commands.checks.has_permissions(ban_members=True)
    async def softban(
        self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"
    ) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Server only command.", ephemeral=True)
            return
        if member.top_role >= interaction.user.top_role and interaction.user.id != interaction.guild.owner_id:
            await interaction.response.send_message("You cannot softban this member.", ephemeral=True)
            return
        await member.ban(reason=reason, delete_message_days=1)
        await interaction.guild.unban(member, reason="Softban complete")
        await self.bot.db.add_moderation_log(interaction.guild.id, member.id, "softban", reason, "")
        await interaction.response.send_message(f"{member} has been softbanned. Reason: {reason}")

    # ---- Mod Config Group ----

    modconfig = app_commands.Group(name="modconfig", description="Toggle moderation features on/off.")

    @modconfig.command(name="antispam", description="Toggle anti-spam protection.")
    @app_commands.checks.has_permissions(administrator=True)
    async def mc_antispam(self, interaction: discord.Interaction, enabled: bool) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Server only.", ephemeral=True); return
        await self.bot.db.upsert_guild_setting(interaction.guild.id, "antispam_enabled", str(int(enabled)))
        await interaction.response.send_message(f"Anti-spam {'enabled' if enabled else 'disabled'}.", ephemeral=True)

    @modconfig.command(name="raidmode", description="Toggle raid protection mode.")
    @app_commands.checks.has_permissions(administrator=True)
    async def mc_raidmode(self, interaction: discord.Interaction, enabled: bool) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Server only.", ephemeral=True); return
        await self.bot.db.upsert_guild_setting(interaction.guild.id, "raid_mode", str(int(enabled)))
        await interaction.response.send_message(f"Raid mode {'enabled' if enabled else 'disabled'}.", ephemeral=True)

    @modconfig.command(name="filter", description="Toggle word filter.")
    @app_commands.checks.has_permissions(administrator=True)
    async def mc_filter(self, interaction: discord.Interaction, enabled: bool) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Server only.", ephemeral=True); return
        await self.bot.db.upsert_guild_setting(interaction.guild.id, "filter_enabled", str(int(enabled)))
        await interaction.response.send_message(f"Word filter {'enabled' if enabled else 'disabled'}.", ephemeral=True)

    @modconfig.command(name="linkblock", description="Toggle link blocking.")
    @app_commands.checks.has_permissions(administrator=True)
    async def mc_linkblock(self, interaction: discord.Interaction, enabled: bool) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Server only.", ephemeral=True); return
        await self.bot.db.upsert_guild_setting(interaction.guild.id, "linkblock_enabled", str(int(enabled)))
        await interaction.response.send_message(f"Link blocking {'enabled' if enabled else 'disabled'}.", ephemeral=True)

    @modconfig.command(name="logging", description="Toggle moderation logging.")
    @app_commands.checks.has_permissions(administrator=True)
    async def mc_logging(self, interaction: discord.Interaction, enabled: bool) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Server only.", ephemeral=True); return
        await self.bot.db.upsert_guild_setting(interaction.guild.id, "mod_logging_enabled", str(int(enabled)))
        await interaction.response.send_message(f"Mod logging {'enabled' if enabled else 'disabled'}.", ephemeral=True)

    @modconfig.command(name="view", description="View all moderation config settings.")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def mc_view(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Server only.", ephemeral=True); return
        gid = interaction.guild.id
        settings = {
            "Anti-Spam": await self.bot.db.get_guild_setting(gid, "antispam_enabled"),
            "Raid Mode": await self.bot.db.get_guild_setting(gid, "raid_mode"),
            "Word Filter": await self.bot.db.get_guild_setting(gid, "filter_enabled"),
            "Link Blocking": await self.bot.db.get_guild_setting(gid, "linkblock_enabled"),
            "Mod Logging": await self.bot.db.get_guild_setting(gid, "mod_logging_enabled"),
        }
        embed = discord.Embed(title="Moderation Configuration", color=discord.Color.orange())
        for name, val in settings.items():
            embed.add_field(name=name, value="✅ On" if val == "1" else "❌ Off", inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ---- Event Listeners ----

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> None:
        if after.author.bot or not after.guild:
            return
        if before.content != after.content:
            await self.check_message(after)

    # ---- Error Handler ----

    @purge.error
    @timeout.error
    @untimeout.error
    @warn.error
    @warns.error
    @unwarn.error
    @modlogs.error
    @slowmode.error
    @lock.error
    @unlock.error
    @kick.error
    @ban.error
    @unban.error
    @clean.error
    @nick.error
    @softban.error
    async def moderation_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ) -> None:
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "You don't have the required moderation permissions.", ephemeral=True
            )
            return
        await interaction.response.send_message(f"Moderation command failed: `{error}`", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ModerationCog(bot))
