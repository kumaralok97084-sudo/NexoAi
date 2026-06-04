from __future__ import annotations

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands

from cogs.emojis import CHECK_OK, CROSS_NO


class ModerationExtCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    def _mod_only(self):
        return app_commands.checks.has_permissions(moderate_members=True)

    # ══════════════════════════════════════════════════════════════
    #  QUICK ACTIONS
    # ══════════════════════════════════════════════════════════════

    @app_commands.command(name="mute", description="Timeout a member.")
    @app_commands.describe(user="Member to mute", minutes="Duration in minutes (max 40320)")
    async def cmd_mute(self, interaction: discord.Interaction, user: discord.Member, minutes: app_commands.Range[int, 1, 40320]) -> None:
        if not isinstance(interaction.guild, discord.Guild):
            await interaction.response.send_message(f"{CROSS_NO} Use in a server.", ephemeral=True)
            return
        try:
            await user.timeout(timedelta(minutes=minutes), reason=f"Muted by {interaction.user}")
            await interaction.response.send_message(f"{CHECK_OK} {user.mention} muted for {minutes} minutes.")
        except discord.Forbidden:
            await interaction.response.send_message(f"{CROSS_NO} I can't mute that user.", ephemeral=True)

    @app_commands.command(name="unmute", description="Remove a member's timeout.")
    @app_commands.describe(user="Member to unmute")
    async def cmd_unmute(self, interaction: discord.Interaction, user: discord.Member) -> None:
        if not isinstance(interaction.guild, discord.Guild):
            await interaction.response.send_message(f"{CROSS_NO} Use in a server.", ephemeral=True)
            return
        try:
            await user.timeout(None, reason=f"Unmuted by {interaction.user}")
            await interaction.response.send_message(f"{CHECK_OK} {user.mention} unmuted.")
        except discord.Forbidden:
            await interaction.response.send_message(f"{CROSS_NO} I can't unmute that user.", ephemeral=True)

    @app_commands.command(name="voicekick", description="Disconnect a user from voice.")
    @app_commands.describe(user="User to disconnect")
    async def cmd_voicekick(self, interaction: discord.Interaction, user: discord.Member) -> None:
        if not isinstance(interaction.guild, discord.Guild):
            await interaction.response.send_message(f"{CROSS_NO} Use in a server.", ephemeral=True)
            return
        if not user.voice:
            await interaction.response.send_message(f"{CROSS_NO} They're not in a voice channel.", ephemeral=True)
            return
        try:
            await user.move_to(None, reason=f"Voice kicked by {interaction.user}")
            await interaction.response.send_message(f"{CHECK_OK} {user.mention} disconnected from voice.")
        except discord.Forbidden:
            await interaction.response.send_message(f"{CROSS_NO} I can't do that.", ephemeral=True)

    @app_commands.command(name="voicemove", description="Move a user to another voice channel.")
    @app_commands.describe(user="User to move", channel="Target voice channel")
    async def cmd_voicemove(self, interaction: discord.Interaction, user: discord.Member, channel: discord.VoiceChannel) -> None:
        if not isinstance(interaction.guild, discord.Guild):
            await interaction.response.send_message(f"{CROSS_NO} Use in a server.", ephemeral=True)
            return
        if not user.voice:
            await interaction.response.send_message(f"{CROSS_NO} They're not in voice.", ephemeral=True)
            return
        try:
            await user.move_to(channel, reason=f"Moved by {interaction.user}")
            await interaction.response.send_message(f"{CHECK_OK} {user.mention} moved to {channel.mention}.")
        except discord.Forbidden:
            await interaction.response.send_message(f"{CROSS_NO} I can't do that.", ephemeral=True)

    @app_commands.command(name="nickall", description="Change nickname for all members.")
    @app_commands.describe(name="New nickname (empty to reset)")
    async def cmd_nickall(self, interaction: discord.Interaction, name: str = "") -> None:
        if not isinstance(interaction.guild, discord.Guild):
            await interaction.response.send_message(f"{CROSS_NO} Use in a server.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        done, failed = 0, 0
        for m in interaction.guild.members:
            if m == interaction.guild.me:
                continue
            try:
                await m.edit(nick=name if name else None, reason=f"Mass nick by {interaction.user}")
                done += 1
            except discord.Forbidden:
                failed += 1
        await interaction.followup.send(f"{CHECK_OK} Nicked {done} members. {failed} failed (hierarchy).")

    # ══════════════════════════════════════════════════════════════
    #  CHANNEL MANAGEMENT
    # ══════════════════════════════════════════════════════════════

    @app_commands.command(name="nuke", description="Clone + delete a channel (full reset).")
    @app_commands.describe(channel="Channel to nuke")
    async def cmd_nuke(self, interaction: discord.Interaction, channel: discord.TextChannel | None = None) -> None:
        if not isinstance(interaction.guild, discord.Guild):
            await interaction.response.send_message(f"{CROSS_NO} Use in a server.", ephemeral=True)
            return
        ch = channel or interaction.channel
        if not isinstance(ch, discord.TextChannel):
            await interaction.response.send_message(f"{CROSS_NO} Not a text channel.", ephemeral=True)
            return
        try:
            new = await ch.clone(reason=f"Nuked by {interaction.user}")
            await ch.delete(reason=f"Nuked by {interaction.user}")
            await new.send(f"{CHECK_OK} Channel nuked by {interaction.user.mention}!")
        except discord.Forbidden:
            await interaction.response.send_message(f"{CROSS_NO} I can't do that.", ephemeral=True)

    @app_commands.command(name="hide", description="Hide a channel from @everyone.")
    @app_commands.describe(channel="Channel to hide")
    async def cmd_hide(self, interaction: discord.Interaction, channel: discord.TextChannel | None = None) -> None:
        if not isinstance(interaction.guild, discord.Guild):
            await interaction.response.send_message(f"{CROSS_NO} Use in a server.", ephemeral=True)
            return
        ch = channel or interaction.channel
        if not isinstance(ch, (discord.TextChannel, discord.VoiceChannel)):
            await interaction.response.send_message(f"{CROSS_NO} Invalid channel.", ephemeral=True)
            return
        try:
            await ch.set_permissions(interaction.guild.default_role, read_messages=False, reason=f"Hid by {interaction.user}")
            await interaction.response.send_message(f"{CHECK_OK} {ch.mention} hidden.")
        except discord.Forbidden:
            await interaction.response.send_message(f"{CROSS_NO} I can't do that.", ephemeral=True)

    @app_commands.command(name="unhide", description="Restore visibility of a channel.")
    @app_commands.describe(channel="Channel to unhide")
    async def cmd_unhide(self, interaction: discord.Interaction, channel: discord.TextChannel | None = None) -> None:
        if not isinstance(interaction.guild, discord.Guild):
            await interaction.response.send_message(f"{CROSS_NO} Use in a server.", ephemeral=True)
            return
        ch = channel or interaction.channel
        if not isinstance(ch, (discord.TextChannel, discord.VoiceChannel)):
            await interaction.response.send_message(f"{CROSS_NO} Invalid channel.", ephemeral=True)
            return
        try:
            await ch.set_permissions(interaction.guild.default_role, read_messages=None, reason=f"Unhid by {interaction.user}")
            await interaction.response.send_message(f"{CHECK_OK} {ch.mention} unhidden.")
        except discord.Forbidden:
            await interaction.response.send_message(f"{CROSS_NO} I can't do that.", ephemeral=True)

    @app_commands.command(name="clone", description="Duplicate a channel.")
    @app_commands.describe(channel="Channel to clone", name="New channel name (optional)")
    async def cmd_clone(self, interaction: discord.Interaction, channel: discord.TextChannel, name: str = "") -> None:
        if not isinstance(interaction.guild, discord.Guild):
            await interaction.response.send_message(f"{CROSS_NO} Use in a server.", ephemeral=True)
            return
        try:
            new = await channel.clone(name=name or f"{channel.name}-copy", reason=f"Cloned by {interaction.user}")
            await interaction.response.send_message(f"{CHECK_OK} Cloned {channel.mention} -> {new.mention}.")
        except discord.Forbidden:
            await interaction.response.send_message(f"{CROSS_NO} I can't do that.", ephemeral=True)

    @app_commands.command(name="topic", description="Set channel topic.")
    @app_commands.describe(channel="Channel", text="New topic text")
    async def cmd_topic(self, interaction: discord.Interaction, channel: discord.TextChannel, text: str) -> None:
        try:
            await channel.edit(topic=text[:1024], reason=f"Topic set by {interaction.user}")
            await interaction.response.send_message(f"{CHECK_OK} Topic set for {channel.mention}.")
        except discord.Forbidden:
            await interaction.response.send_message(f"{CROSS_NO} I can't do that.", ephemeral=True)

    # ══════════════════════════════════════════════════════════════
    #  ROLE & MEMBER MANAGEMENT
    # ══════════════════════════════════════════════════════════════

    @app_commands.command(name="role_add", description="Add a role to a user.")
    @app_commands.describe(user="User", role="Role to add")
    async def cmd_role_add(self, interaction: discord.Interaction, user: discord.Member, role: discord.Role) -> None:
        if role >= interaction.guild.me.top_role if interaction.guild else True:
            await interaction.response.send_message(f"{CROSS_NO} Role is above my highest role.", ephemeral=True)
            return
        try:
            await user.add_roles(role, reason=f"Added by {interaction.user}")
            await interaction.response.send_message(f"{CHECK_OK} Added {role.mention} to {user.mention}.")
        except discord.Forbidden:
            await interaction.response.send_message(f"{CROSS_NO} I can't do that.", ephemeral=True)

    @app_commands.command(name="role_remove", description="Remove a role from a user.")
    @app_commands.describe(user="User", role="Role to remove")
    async def cmd_role_remove(self, interaction: discord.Interaction, user: discord.Member, role: discord.Role) -> None:
        if role >= interaction.guild.me.top_role if interaction.guild else True:
            await interaction.response.send_message(f"{CROSS_NO} Role is above my highest role.", ephemeral=True)
            return
        try:
            await user.remove_roles(role, reason=f"Removed by {interaction.user}")
            await interaction.response.send_message(f"{CHECK_OK} Removed {role.mention} from {user.mention}.")
        except discord.Forbidden:
            await interaction.response.send_message(f"{CROSS_NO} I can't do that.", ephemeral=True)

    @app_commands.command(name="banlist", description="List all banned users.")
    async def cmd_banlist(self, interaction: discord.Interaction) -> None:
        if not isinstance(interaction.guild, discord.Guild):
            await interaction.response.send_message(f"{CROSS_NO} Use in a server.", ephemeral=True)
            return
        await interaction.response.defer()
        bans = [b async for b in interaction.guild.bans()]
        if not bans:
            await interaction.followup.send(f"{CROSS_NO} No bans.")
            return
        lines = [f"**{b.user}** (`{b.user.id}`) — {b.reason or 'No reason'}" for b in bans[:25]]
        embed = discord.Embed(title=f"Ban List ({len(bans)})", description="\n".join(lines), color=discord.Color.red())
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="cleanup", description="Delete bot messages in this channel.")
    @app_commands.describe(count="Number of messages to check")
    async def cmd_cleanup(self, interaction: discord.Interaction, count: app_commands.Range[int, 1, 500] = 50) -> None:
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message(f"{CROSS_NO} Use in a text channel.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        deleted = 0
        async for msg in interaction.channel.history(limit=count):
            if msg.author.bot:
                try:
                    await msg.delete()
                    deleted += 1
                    await asyncio.sleep(0.1)
                except discord.Forbidden:
                    pass
        await interaction.followup.send(f"{CHECK_OK} Deleted {deleted} bot messages.")

    # ══════════════════════════════════════════════════════════════
    #  SERVER TOOLS
    # ══════════════════════════════════════════════════════════════

    @app_commands.command(name="emoji_add", description="Upload a custom emoji to the server.")
    @app_commands.checks.has_permissions(manage_expressions=True)
    @app_commands.describe(name="Emoji name", image="Image file (PNG/GIF, 256KB max)")
    async def cmd_emoji_add(self, interaction: discord.Interaction, name: str, image: discord.Attachment) -> None:
        if not isinstance(interaction.guild, discord.Guild):
            await interaction.response.send_message(f"{CROSS_NO} Use in a server.", ephemeral=True)
            return
        if image.size > 262144:
            await interaction.response.send_message(f"{CROSS_NO} Image too large (max 256KB).", ephemeral=True)
            return
        img_bytes = await image.read()
        try:
            emoji = await interaction.guild.create_custom_emoji(name=name, image=img_bytes, reason=f"Added by {interaction.user}")
            anim = "a" if emoji.animated else ""
            await interaction.response.send_message(f"{CHECK_OK} Emoji created: <{anim}:{emoji.name}:{emoji.id}>")
        except discord.Forbidden:
            await interaction.response.send_message(f"{CROSS_NO} Missing manage_emojis permission.", ephemeral=True)
        except discord.HTTPException as e:
            await interaction.response.send_message(f"{CROSS_NO} Failed: {e}", ephemeral=True)

    @app_commands.command(name="emoji_remove", description="Delete a custom emoji from the server.")
    @app_commands.checks.has_permissions(manage_expressions=True)
    @app_commands.describe(emoji="Emoji to delete")
    async def cmd_emoji_remove(self, interaction: discord.Interaction, emoji: str) -> None:
        if not isinstance(interaction.guild, discord.Guild):
            await interaction.response.send_message(f"{CROSS_NO} Use in a server.", ephemeral=True)
            return
        parsed = discord.PartialEmoji.from_str(emoji)
        guild_emoji = interaction.guild.get_emoji(parsed.id) if parsed.id else None
        if not guild_emoji:
            await interaction.response.send_message(f"{CROSS_NO} Emoji not found in this server.", ephemeral=True)
            return
        try:
            await guild_emoji.delete(reason=f"Removed by {interaction.user}")
            await interaction.response.send_message(f"{CHECK_OK} Emoji deleted.")
        except discord.Forbidden:
            await interaction.response.send_message(f"{CROSS_NO} I can't do that.", ephemeral=True)

    @app_commands.command(name="sticker_add", description="Add a sticker to the server.")
    @app_commands.checks.has_permissions(manage_expressions=True)
    @app_commands.describe(name="Sticker name", file="Sticker image (PNG/APNG, 512KB max)")
    async def cmd_sticker_add(self, interaction: discord.Interaction, name: str, file: discord.Attachment) -> None:
        if not isinstance(interaction.guild, discord.Guild):
            await interaction.response.send_message(f"{CROSS_NO} Use in a server.", ephemeral=True)
            return
        if file.size > 524288:
            await interaction.response.send_message(f"{CROSS_NO} File too large (max 512KB).", ephemeral=True)
            return
        try:
            await interaction.guild.create_sticker(name=name, description=name, file=await file.to_file(), reason=f"Added by {interaction.user}")
            await interaction.response.send_message(f"{CHECK_OK} Sticker **{name}** created.")
        except discord.Forbidden:
            await interaction.response.send_message(f"{CROSS_NO} Missing permission.", ephemeral=True)

    @app_commands.command(name="archive_threads", description="Archive inactive threads.")
    @app_commands.describe(days="Archive threads inactive for this many days")
    async def cmd_archive_threads(self, interaction: discord.Interaction, days: int = 7) -> None:
        if not isinstance(interaction.guild, discord.Guild):
            await interaction.response.send_message(f"{CROSS_NO} Use in a server.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        archived = 0
        for ch in interaction.guild.text_channels:
            for thread in ch.threads:
                if not thread.archived:
                    last = thread.last_message_id or 0
                    age_days = (discord.utils.utcnow() - (thread.archive_timestamp or discord.utils.utcnow())).days
                    if age_days >= days:
                        try:
                            await thread.edit(archived=True, reason=f"Archived by {interaction.user}")
                            archived += 1
                        except discord.Forbidden:
                            pass
        await interaction.followup.send(f"{CHECK_OK} Archived {archived} threads inactive for >{days}d.")

    @app_commands.command(name="invite_list", description="List active server invites.")
    async def cmd_invite_list(self, interaction: discord.Interaction) -> None:
        if not isinstance(interaction.guild, discord.Guild):
            await interaction.response.send_message(f"{CROSS_NO} Use in a server.", ephemeral=True)
            return
        try:
            invites = await interaction.guild.invites()
        except discord.Forbidden:
            await interaction.response.send_message(f"{CROSS_NO} I can't view invites.", ephemeral=True)
            return
        if not invites:
            await interaction.response.send_message(f"{CROSS_NO} No active invites.")
            return
        lines = [f"`{i.code}` — {i.channel.mention} (uses: {i.uses})" for i in invites[:20]]
        embed = discord.Embed(title="Server Invites", description="\n".join(lines), color=discord.Color.blue())
        await interaction.response.send_message(embed=embed)

    # ══════════════════════════════════════════════════════════════
    #  ADVANCED
    # ══════════════════════════════════════════════════════════════

    @app_commands.command(name="massban", description="Ban multiple users at once.")
    @app_commands.describe(users="User IDs/mentions separated by spaces", reason="Ban reason")
    async def cmd_massban(self, interaction: discord.Interaction, users: str, reason: str = "Mass ban") -> None:
        if not isinstance(interaction.guild, discord.Guild):
            await interaction.response.send_message(f"{CROSS_NO} Use in a server.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        ids = []
        for part in users.split():
            try:
                ids.append(int(part.strip("<@!>")))
            except ValueError:
                pass
        if not ids:
            await interaction.followup.send(f"{CROSS_NO} No valid user IDs found.")
            return
        done = 0
        for uid in ids:
            try:
                await interaction.guild.ban(discord.Object(id=uid), reason=f"{reason} | by {interaction.user}")
                done += 1
            except discord.Forbidden:
                pass
        await interaction.followup.send(f"{CHECK_OK} Banned {done}/{len(ids)} users.")

    @app_commands.command(name="automod", description="Toggle auto-mod rules.")
    @app_commands.describe(rule="Rule to toggle", enabled="Enable or disable")
    async def cmd_automod(self, interaction: discord.Interaction, rule: str, enabled: bool) -> None:
        if not isinstance(interaction.guild, discord.Guild):
            await interaction.response.send_message(f"{CROSS_NO} Use in a server.", ephemeral=True)
            return
        valid = ("spam", "caps", "links", "invites", "spoilers", "repeat")
        if rule.lower() not in valid:
            await interaction.response.send_message(f"{CROSS_NO} Rule must be one of: {', '.join(valid)}", ephemeral=True)
            return
        key = f"automod_{rule.lower()}"
        await self.bot.db.set_config(interaction.guild.id, key, "1" if enabled else "0")
        await interaction.response.send_message(f"{CHECK_OK} Auto-mod **{rule}** set to {'enabled' if enabled else 'disabled'}.")

    @app_commands.command(name="member_breakdown", description="View member statistics.")
    async def cmd_member_breakdown(self, interaction: discord.Interaction) -> None:
        if not isinstance(interaction.guild, discord.Guild):
            await interaction.response.send_message(f"{CROSS_NO} Use in a server.", ephemeral=True)
            return
        g = interaction.guild
        total = g.member_count or 0
        humans = sum(1 for m in g.members if not m.bot)
        bots = total - humans
        online = sum(1 for m in g.members if m.status == discord.Status.online)
        idle = sum(1 for m in g.members if m.status == discord.Status.idle)
        dnd = sum(1 for m in g.members if m.status == discord.Status.dnd)
        offline = sum(1 for m in g.members if m.status == discord.Status.offline)
        embed = discord.Embed(title="Member Breakdown", color=discord.Color.blue())
        embed.add_field(name="Members", value=f"👤 {total}")
        embed.add_field(name="Humans", value=f"{humans}")
        embed.add_field(name="Bots", value=f"{bots}")
        embed.add_field(name="Online", value=f"🟢 {online}")
        embed.add_field(name="Idle", value=f"🟡 {idle}")
        embed.add_field(name="DND", value=f"🔴 {dnd}")
        embed.add_field(name="Offline", value=f"⚫ {offline}")
        embed.add_field(name="Roles", value=str(len(g.roles)))
        await interaction.response.send_message(embed=embed)

    # ══════════════════════════════════════════════════════════════
    #  MEMBER INVESTIGATION
    # ══════════════════════════════════════════════════════════════

    @app_commands.command(name="userhistory", description="View moderation history for a user.")
    @app_commands.describe(user="User to check")
    async def cmd_userhistory(self, interaction: discord.Interaction, user: str) -> None:
        if not isinstance(interaction.guild, discord.Guild):
            await interaction.response.send_message(f"{CROSS_NO} Use in a server.", ephemeral=True)
            return
        uid = None
        member = None
        try:
            uid = int(user)
        except ValueError:
            if interaction.guild:
                member = discord.utils.get(interaction.guild.members, name=user)
            if member is None:
                await interaction.response.send_message(f"{CROSS_NO} Invalid user.", ephemeral=True)
                return
            uid = member.id
        logs = await self.bot.db.get_moderation_logs(interaction.guild.id, uid)
        if not logs:
            await interaction.response.send_message(f"{CROSS_NO} No moderation history for that user.")
            return
        blocks = []
        for log in logs[:15]:
            action = log.get("action", "?")
            reason = (log.get("reason") or "No reason")[:100]
            ts = (log.get("created_at") or "?")[:10]
            blocks.append(f"[{ts}] **{action}** — {reason}")
        embed = discord.Embed(title=f"Mod History for {uid}", description="\n".join(blocks) or "None", color=discord.Color.orange())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="userjoins", description="Check when a user joined Discord and this server.")
    @app_commands.describe(user="User to check")
    async def cmd_userjoins(self, interaction: discord.Interaction, user: discord.Member) -> None:
        now = discord.utils.utcnow()
        account_age = (now - user.created_at).days if user.created_at else 0
        join_age = (now - user.joined_at).days if isinstance(user, discord.Member) and user.joined_at else 0
        embed = discord.Embed(title="Join Info", color=discord.Color.blue())
        embed.add_field(name="Account Created", value=f"{user.created_at.strftime('%b %d, %Y') if user.created_at else 'N/A'} ({account_age}d ago)")
        if isinstance(user, discord.Member) and user.joined_at:
            embed.add_field(name="Joined Server", value=f"{user.joined_at.strftime('%b %d, %Y')} ({join_age}d ago)")
        embed.add_field(name="Alt Risk", value="⚠️ **HIGH**" if account_age < 7 else "✅ Normal")
        embed.set_thumbnail(url=user.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="suspicious", description="Flag members with new accounts (<7 days).")
    async def cmd_suspicious(self, interaction: discord.Interaction) -> None:
        if not isinstance(interaction.guild, discord.Guild):
            await interaction.response.send_message(f"{CROSS_NO} Use in a server.", ephemeral=True)
            return
        now = discord.utils.utcnow()
        flagged = []
        for m in interaction.guild.members:
            if m.bot:
                continue
            age = (now - m.created_at).days if m.created_at else 999
            if age < 7:
                flagged.append(f"{m.mention} — {age}d old account")
        embed = discord.Embed(title=f"Suspicious Members ({len(flagged)})", color=discord.Color.red())
        if flagged:
            embed.description = "\n".join(flagged[:25])
        else:
            embed.description = "No suspicious members found."
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="sharedservers", description="Show servers you share with a user.")
    @app_commands.describe(user="User to check")
    async def cmd_sharedservers(self, interaction: discord.Interaction, user: discord.Member) -> None:
        shared = []
        for g in self.bot.guilds:
            if g.get_member(user.id):
                shared.append(g.name)
        embed = discord.Embed(title=f"Shared Servers with {user.display_name}", color=discord.Color.blue())
        embed.description = "\n".join(shared) if shared else "None"
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="check", description="Comprehensive member check.")
    @app_commands.describe(user="User to check")
    async def cmd_check(self, interaction: discord.Interaction, user: discord.Member) -> None:
        if not isinstance(interaction.guild, discord.Guild):
            await interaction.response.send_message(f"{CROSS_NO} Use in a server.", ephemeral=True)
            return
        now = discord.utils.utcnow()
        account_age = (now - user.created_at).days if user.created_at else 0
        join_age = (now - user.joined_at).days if user.joined_at else 0
        logs = await self.bot.db.get_moderation_logs(interaction.guild.id, user.id)
        warn_count = sum(1 for l in logs if l.get("action") == "warn") if logs else 0
        roles = [r.mention for r in user.roles if r != interaction.guild.default_role]
        embed = discord.Embed(title=f"Check: {user}", color=user.color if user.color.value else discord.Color.blue())
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="Account Age", value=f"{account_age}d")
        embed.add_field(name="Joined", value=f"{join_age}d ago")
        embed.add_field(name="Warns", value=str(warn_count))
        embed.add_field(name="Roles", value=", ".join(roles[:8]) or "None", inline=False)
        embed.add_field(name="Alt Risk", value="⚠️ HIGH" if account_age < 7 else "✅ OK")
        await interaction.response.send_message(embed=embed)

    # ══════════════════════════════════════════════════════════════
    #  MESSAGE & CONTENT MODERATION
    # ══════════════════════════════════════════════════════════════

    @app_commands.command(name="censor", description="Add a word to the auto-censor list.")
    @app_commands.describe(word="Word or phrase to censor")
    async def cmd_censor(self, interaction: discord.Interaction, word: str) -> None:
        if not isinstance(interaction.guild, discord.Guild):
            await interaction.response.send_message(f"{CROSS_NO} Use in a server.", ephemeral=True)
            return
        await self.bot.db.add_filter(interaction.guild.id, word.lower())
        await interaction.response.send_message(f"{CHECK_OK} `{word}` added to censor list.")

    @app_commands.command(name="uncensor", description="Remove a word from the auto-censor list.")
    @app_commands.describe(word="Word to remove")
    async def cmd_uncensor(self, interaction: discord.Interaction, word: str) -> None:
        if not isinstance(interaction.guild, discord.Guild):
            await interaction.response.send_message(f"{CROSS_NO} Use in a server.", ephemeral=True)
            return
        filters = await self.bot.db.get_filters(interaction.guild.id)
        for f in filters:
            if f["pattern"].lower() == word.lower():
                await self.bot.db.remove_filter(f["id"])
        await interaction.response.send_message(f"{CHECK_OK} `{word}` removed from censor list.")

    @app_commands.command(name="censorlist", description="Show all censored words.")
    async def cmd_censorlist(self, interaction: discord.Interaction) -> None:
        if not isinstance(interaction.guild, discord.Guild):
            await interaction.response.send_message(f"{CROSS_NO} Use in a server.", ephemeral=True)
            return
        filters = await self.bot.db.get_filters(interaction.guild.id)
        if not filters:
            await interaction.response.send_message(f"{CROSS_NO} No censored words.")
            return
        words = [f["pattern"] for f in filters]
        embed = discord.Embed(title=f"Censored Words ({len(words)})", description=", ".join(f"`{w}`" for w in words), color=discord.Color.red())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="regexfilter", description="Add a regex filter pattern.")
    @app_commands.describe(pattern="Regex pattern", action="Action: delete (default) or warn")
    async def cmd_regexfilter(self, interaction: discord.Interaction, pattern: str, action: str = "delete") -> None:
        if not isinstance(interaction.guild, discord.Guild):
            await interaction.response.send_message(f"{CROSS_NO} Use in a server.", ephemeral=True)
            return
        import re
        try:
            re.compile(pattern)
        except re.error:
            await interaction.response.send_message(f"{CROSS_NO} Invalid regex pattern.", ephemeral=True)
            return
        await self.bot.db.set_config(interaction.guild.id, f"regexfilter_{len(pattern)}", f"{pattern}|{action}")
        await interaction.response.send_message(f"{CHECK_OK} Regex filter added: `{pattern}` -> {action}.")

    @app_commands.command(name="massdelete", description="Delete recent messages from a user.")
    @app_commands.describe(user="User whose messages to delete", count="Number of messages to check")
    async def cmd_massdelete(self, interaction: discord.Interaction, user: discord.Member, count: app_commands.Range[int, 1, 500] = 100) -> None:
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message(f"{CROSS_NO} Use in a text channel.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        deleted = 0
        async for msg in interaction.channel.history(limit=count):
            if msg.author == user:
                try:
                    await msg.delete()
                    deleted += 1
                    await asyncio.sleep(0.1)
                except discord.Forbidden:
                    pass
        await interaction.followup.send(f"{CHECK_OK} Deleted {deleted} messages from {user.mention}.")

    @app_commands.command(name="cleanup_bots", description="Delete all bot messages in this channel.")
    @app_commands.describe(count="Number of messages to check")
    async def cmd_cleanup_bots(self, interaction: discord.Interaction, count: app_commands.Range[int, 1, 500] = 100) -> None:
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message(f"{CROSS_NO} Use in a text channel.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        deleted = 0
        async for msg in interaction.channel.history(limit=count):
            if msg.author.bot:
                try:
                    await msg.delete()
                    deleted += 1
                    await asyncio.sleep(0.1)
                except discord.Forbidden:
                    pass
        await interaction.followup.send(f"{CHECK_OK} Deleted {deleted} bot messages.")

    @app_commands.command(name="cleanup_matches", description="Delete messages containing specific text.")
    @app_commands.describe(text="Text to match", count="Number of messages to check")
    async def cmd_cleanup_matches(self, interaction: discord.Interaction, text: str, count: app_commands.Range[int, 1, 500] = 100) -> None:
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message(f"{CROSS_NO} Use in a text channel.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        deleted = 0
        async for msg in interaction.channel.history(limit=count):
            if text.lower() in msg.content.lower():
                try:
                    await msg.delete()
                    deleted += 1
                    await asyncio.sleep(0.1)
                except discord.Forbidden:
                    pass
        await interaction.followup.send(f"{CHECK_OK} Deleted {deleted} matching messages.")

    @app_commands.command(name="cleanup_attachments", description="Delete messages with attachments.")
    @app_commands.describe(count="Number of messages to check")
    async def cmd_cleanup_attachments(self, interaction: discord.Interaction, count: app_commands.Range[int, 1, 500] = 100) -> None:
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message(f"{CROSS_NO} Use in a text channel.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        deleted = 0
        async for msg in interaction.channel.history(limit=count):
            if msg.attachments:
                try:
                    await msg.delete()
                    deleted += 1
                    await asyncio.sleep(0.1)
                except discord.Forbidden:
                    pass
        await interaction.followup.send(f"{CHECK_OK} Deleted {deleted} messages with attachments.")

    @app_commands.command(name="cleanup_links", description="Delete messages containing links.")
    @app_commands.describe(count="Number of messages to check")
    async def cmd_cleanup_links(self, interaction: discord.Interaction, count: app_commands.Range[int, 1, 500] = 100) -> None:
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message(f"{CROSS_NO} Use in a text channel.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        deleted = 0
        async for msg in interaction.channel.history(limit=count):
            if "http" in msg.content.lower():
                try:
                    await msg.delete()
                    deleted += 1
                    await asyncio.sleep(0.1)
                except discord.Forbidden:
                    pass
        await interaction.followup.send(f"{CHECK_OK} Deleted {deleted} messages with links.")

    @app_commands.command(name="cleanup_mentions", description="Delete messages with mass mentions.")
    @app_commands.describe(count="Number of messages to check")
    async def cmd_cleanup_mentions(self, interaction: discord.Interaction, count: app_commands.Range[int, 1, 500] = 100) -> None:
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message(f"{CROSS_NO} Use in a text channel.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        deleted = 0
        async for msg in interaction.channel.history(limit=count):
            if "@everyone" in msg.content or "@here" in msg.content:
                try:
                    await msg.delete()
                    deleted += 1
                    await asyncio.sleep(0.1)
                except discord.Forbidden:
                    pass
        await interaction.followup.send(f"{CHECK_OK} Deleted {deleted} mass-mention messages.")

    # ══════════════════════════════════════════════════════════════
    #  VOICE MODERATION
    # ══════════════════════════════════════════════════════════════

    @app_commands.command(name="voice_muteall", description="Server-mute everyone in a voice channel.")
    @app_commands.describe(channel="Voice channel (default: your current)")
    async def cmd_voice_muteall(self, interaction: discord.Interaction, channel: discord.VoiceChannel | None = None) -> None:
        ch = channel or (interaction.user.voice.channel if isinstance(interaction.user, discord.Member) and interaction.user.voice else None)
        if not ch:
            await interaction.response.send_message(f"{CROSS_NO} Specify a voice channel or join one.", ephemeral=True)
            return
        done = 0
        for m in ch.members:
            try:
                await m.edit(mute=True, reason=f"Muteall by {interaction.user}")
                done += 1
            except discord.Forbidden:
                pass
        await interaction.response.send_message(f"{CHECK_OK} Server-muted {done} members in {ch.name}.")

    @app_commands.command(name="voice_unmuteall", description="Unmute everyone in a voice channel.")
    @app_commands.describe(channel="Voice channel (default: your current)")
    async def cmd_voice_unmuteall(self, interaction: discord.Interaction, channel: discord.VoiceChannel | None = None) -> None:
        ch = channel or (interaction.user.voice.channel if isinstance(interaction.user, discord.Member) and interaction.user.voice else None)
        if not ch:
            await interaction.response.send_message(f"{CROSS_NO} Specify a voice channel.", ephemeral=True)
            return
        done = 0
        for m in ch.members:
            try:
                await m.edit(mute=False, reason=f"Unmuteall by {interaction.user}")
                done += 1
            except discord.Forbidden:
                pass
        await interaction.response.send_message(f"{CHECK_OK} Unmuted {done} members in {ch.name}.")

    @app_commands.command(name="voice_deafen", description="Deafen a user in voice.")
    @app_commands.describe(user="User to deafen")
    async def cmd_voice_deafen(self, interaction: discord.Interaction, user: discord.Member) -> None:
        if not user.voice:
            await interaction.response.send_message(f"{CROSS_NO} Not in voice.", ephemeral=True)
            return
        try:
            await user.edit(deafen=True, reason=f"Deafened by {interaction.user}")
            await interaction.response.send_message(f"{CHECK_OK} {user.mention} deafened.")
        except discord.Forbidden:
            await interaction.response.send_message(f"{CROSS_NO} I can't do that.", ephemeral=True)

    @app_commands.command(name="voice_undeafen", description="Undeafen a user in voice.")
    @app_commands.describe(user="User to undeafen")
    async def cmd_voice_undeafen(self, interaction: discord.Interaction, user: discord.Member) -> None:
        if not user.voice:
            await interaction.response.send_message(f"{CROSS_NO} Not in voice.", ephemeral=True)
            return
        try:
            await user.edit(deafen=False, reason=f"Undeafened by {interaction.user}")
            await interaction.response.send_message(f"{CHECK_OK} {user.mention} undeafened.")
        except discord.Forbidden:
            await interaction.response.send_message(f"{CROSS_NO} I can't do that.", ephemeral=True)

    @app_commands.command(name="voice_deafenall", description="Deafen everyone in a voice channel.")
    @app_commands.describe(channel="Voice channel (default: your current)")
    async def cmd_voice_deafenall(self, interaction: discord.Interaction, channel: discord.VoiceChannel | None = None) -> None:
        ch = channel or (interaction.user.voice.channel if isinstance(interaction.user, discord.Member) and interaction.user.voice else None)
        if not ch:
            await interaction.response.send_message(f"{CROSS_NO} Specify a voice channel.", ephemeral=True)
            return
        done = 0
        for m in ch.members:
            try:
                await m.edit(deafen=True, reason=f"Deafenall by {interaction.user}")
                done += 1
            except discord.Forbidden:
                pass
        await interaction.response.send_message(f"{CHECK_OK} Deafened {done} members in {ch.name}.")

    @app_commands.command(name="voice_lock", description="Lock voice channel to current members.")
    @app_commands.describe(channel="Voice channel (default: your current)")
    async def cmd_voice_lock(self, interaction: discord.Interaction, channel: discord.VoiceChannel | None = None) -> None:
        ch = channel or (interaction.user.voice.channel if isinstance(interaction.user, discord.Member) and interaction.user.voice else None)
        if not ch:
            await interaction.response.send_message(f"{CROSS_NO} Specify a voice channel.", ephemeral=True)
            return
        try:
            await ch.edit(user_limit=len(ch.members), reason=f"Locked by {interaction.user}")
            await interaction.response.send_message(f"{CHECK_OK} {ch.name} locked ({len(ch.members)} user limit).")
        except discord.Forbidden:
            await interaction.response.send_message(f"{CROSS_NO} I can't do that.", ephemeral=True)

    @app_commands.command(name="voice_limit", description="Set voice channel user limit.")
    @app_commands.describe(channel="Voice channel", limit="Max users (0 = unlimited)")
    async def cmd_voice_limit(self, interaction: discord.Interaction, channel: discord.VoiceChannel, limit: int) -> None:
        try:
            await channel.edit(user_limit=max(0, limit), reason=f"Limit set by {interaction.user}")
            await interaction.response.send_message(f"{CHECK_OK} {channel.name} limit set to {max(0, limit)}.")
        except discord.Forbidden:
            await interaction.response.send_message(f"{CROSS_NO} I can't do that.", ephemeral=True)

    @app_commands.command(name="voice_region", description="Set voice channel region.")
    @app_commands.describe(channel="Voice channel", region="Region (e.g. us-west, eu-west, etc.)")
    async def cmd_voice_region(self, interaction: discord.Interaction, channel: discord.VoiceChannel, region: str) -> None:
        try:
            rtc = discord.VoiceRegion(region)
        except ValueError:
            await interaction.response.send_message(f"{CROSS_NO} Invalid region. Try: us-west, us-east, eu-west, eu-central, etc.", ephemeral=True)
            return
        try:
            await channel.edit(rtc_region=rtc, reason=f"Region set by {interaction.user}")
            await interaction.response.send_message(f"{CHECK_OK} {channel.name} region set to {rtc}.")
        except discord.Forbidden:
            await interaction.response.send_message(f"{CROSS_NO} I can't do that.", ephemeral=True)

    # ══════════════════════════════════════════════════════════════
    #  SERVER CONFIG
    # ══════════════════════════════════════════════════════════════

    @app_commands.command(name="automod_spam", description="Configure spam auto-mod threshold.")
    @app_commands.describe(messages="Max messages", seconds="In this many seconds")
    async def cmd_automod_spam(self, interaction: discord.Interaction, messages: int = 5, seconds: int = 3) -> None:
        await self.bot.db.set_config(interaction.guild_id, "automod_spam_msgs", str(messages))
        await self.bot.db.set_config(interaction.guild_id, "automod_spam_secs", str(seconds))
        await interaction.response.send_message(f"{CHECK_OK} Spam threshold: {messages}msgs/{seconds}s.")

    @app_commands.command(name="automod_caps", description="Set caps auto-mod threshold.")
    @app_commands.describe(percent="Caps percentage to trigger (50-100)")
    async def cmd_automod_caps(self, interaction: discord.Interaction, percent: app_commands.Range[int, 50, 100] = 80) -> None:
        await self.bot.db.set_config(interaction.guild_id, "automod_caps", str(percent))
        await interaction.response.send_message(f"{CHECK_OK} Caps threshold set to {percent}%.")

    @app_commands.command(name="automod_links", description="Toggle link blocking.")
    @app_commands.describe(enabled="Enable or disable")
    async def cmd_automod_links(self, interaction: discord.Interaction, enabled: bool) -> None:
        await self.bot.db.set_config(interaction.guild_id, "automod_links", "1" if enabled else "0")
        await interaction.response.send_message(f"{CHECK_OK} Link blocking {'enabled' if enabled else 'disabled'}.")

    @app_commands.command(name="automod_invites", description="Toggle invite blocking.")
    @app_commands.describe(enabled="Enable or disable")
    async def cmd_automod_invites(self, interaction: discord.Interaction, enabled: bool) -> None:
        await self.bot.db.set_config(interaction.guild_id, "automod_invites", "1" if enabled else "0")
        await interaction.response.send_message(f"{CHECK_OK} Invite blocking {'enabled' if enabled else 'disabled'}.")

    @app_commands.command(name="automod_spoilers", description="Toggle spoiler blocking.")
    @app_commands.describe(enabled="Enable or disable")
    async def cmd_automod_spoilers(self, interaction: discord.Interaction, enabled: bool) -> None:
        await self.bot.db.set_config(interaction.guild_id, "automod_spoilers", "1" if enabled else "0")
        await interaction.response.send_message(f"{CHECK_OK} Spoiler blocking {'enabled' if enabled else 'disabled'}.")

    @app_commands.command(name="automod_repeat", description="Toggle repeat message blocking.")
    @app_commands.describe(enabled="Enable or disable")
    async def cmd_automod_repeat(self, interaction: discord.Interaction, enabled: bool) -> None:
        await self.bot.db.set_config(interaction.guild_id, "automod_repeat", "1" if enabled else "0")
        await interaction.response.send_message(f"{CHECK_OK} Repeat blocking {'enabled' if enabled else 'disabled'}.")

    @app_commands.command(name="log_set", description="Enable/disable logging for specific events.")
    @app_commands.describe(event="Event type", enabled="Enable or disable")
    async def cmd_log_set(self, interaction: discord.Interaction, event: str, enabled: bool) -> None:
        valid = ("joins", "leaves", "bans", "kicks", "edits", "deletes", "voice", "all")
        if event.lower() not in valid:
            await interaction.response.send_message(f"{CROSS_NO} Event must be: {', '.join(valid)}", ephemeral=True)
            return
        await self.bot.db.set_config(interaction.guild_id, f"log_{event.lower()}", "1" if enabled else "0")
        await interaction.response.send_message(f"{CHECK_OK} Logging for **{event}** {'enabled' if enabled else 'disabled'}.")

    @app_commands.command(name="log_channel", description="Set log channel for an event type.")
    @app_commands.describe(event="Event type", channel="Target channel")
    async def cmd_log_channel(self, interaction: discord.Interaction, event: str, channel: discord.TextChannel) -> None:
        valid = ("joins", "leaves", "bans", "kicks", "edits", "deletes", "voice", "mod", "all")
        if event.lower() not in valid:
            await interaction.response.send_message(f"{CROSS_NO} Event must be: {', '.join(valid)}", ephemeral=True)
            return
        await self.bot.db.set_config(interaction.guild_id, f"logchannel_{event.lower()}", str(channel.id))
        await interaction.response.send_message(f"{CHECK_OK} **{event}** logs -> {channel.mention}.")

    @app_commands.command(name="bypass", description="Add a role to auto-mod bypass list.")
    @app_commands.describe(role="Role to bypass auto-mod")
    async def cmd_bypass(self, interaction: discord.Interaction, role: discord.Role) -> None:
        await self.bot.db.add_bypass_role(interaction.guild_id, role.id)
        await interaction.response.send_message(f"{CHECK_OK} {role.mention} added to auto-mod bypass.")

    @app_commands.command(name="unbypass", description="Remove a role from auto-mod bypass list.")
    @app_commands.describe(role="Role to remove from bypass")
    async def cmd_unbypass(self, interaction: discord.Interaction, role: discord.Role) -> None:
        await self.bot.db.remove_bypass_role(interaction.guild_id, role.id)
        await interaction.response.send_message(f"{CHECK_OK} {role.mention} removed from auto-mod bypass.")

    # ══════════════════════════════════════════════════════════════
    #  CHANNEL PERMISSIONS
    # ══════════════════════════════════════════════════════════════

    @app_commands.command(name="slowmode_reset", description="Turn off slowmode for all text channels.")
    async def cmd_slowmode_reset(self, interaction: discord.Interaction) -> None:
        if not isinstance(interaction.guild, discord.Guild):
            await interaction.response.send_message(f"{CROSS_NO} Use in a server.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        done = 0
        for ch in interaction.guild.text_channels:
            try:
                await ch.edit(slowmode_delay=0, reason=f"Slowmode reset by {interaction.user}")
                done += 1
            except discord.Forbidden:
                pass
        await interaction.followup.send(f"{CHECK_OK} Reset slowmode for {done} channels.")

    @app_commands.command(name="nsfw", description="Toggle NSFW on a channel.")
    @app_commands.describe(channel="Channel to toggle", enabled="NSFW on/off")
    async def cmd_nsfw(self, interaction: discord.Interaction, channel: discord.TextChannel, enabled: bool) -> None:
        try:
            await channel.edit(nsfw=enabled, reason=f"NSFW set by {interaction.user}")
            await interaction.response.send_message(f"{CHECK_OK} {channel.mention} NSFW {'enabled' if enabled else 'disabled'}.")
        except discord.Forbidden:
            await interaction.response.send_message(f"{CROSS_NO} I can't do that.", ephemeral=True)

    @app_commands.command(name="permission", description="Set a permission on a channel for a role.")
    @app_commands.describe(channel="Target channel", role="Target role", permission="Permission name (e.g. read_messages, send_messages, attach_files)", value="Allow/deny/null")
    async def cmd_permission(self, interaction: discord.Interaction, channel: discord.TextChannel | discord.VoiceChannel, role: discord.Role, permission: str, value: str) -> None:
        perm_map = {
            "read_messages": "read_messages", "read": "read_messages",
            "send_messages": "send_messages", "send": "send_messages",
            "attach_files": "attach_files", "files": "attach_files",
            "read_history": "read_message_history", "history": "read_message_history",
            "add_reactions": "add_reactions", "reactions": "add_reactions",
        }
        key = perm_map.get(permission.lower())
        if not key:
            await interaction.response.send_message(f"{CROSS_NO} Unknown permission. Try: read_messages, send_messages, attach_files, read_history, add_reactions", ephemeral=True)
            return
        val = {"allow": True, "deny": False, "null": None}.get(value.lower())
        if val is None:
            await interaction.response.send_message(f"{CROSS_NO} Value must be: allow, deny, or null", ephemeral=True)
            return
        try:
            overwrite = channel.overwrites_for(role)
            setattr(overwrite, key, val)
            await channel.set_permissions(role, overwrite=overwrite, reason=f"Permission set by {interaction.user}")
            await interaction.response.send_message(f"{CHECK_OK} {role.mention} {permission} = {value} in {channel.mention}.")
        except discord.Forbidden:
            await interaction.response.send_message(f"{CROSS_NO} I can't do that.", ephemeral=True)

    @app_commands.command(name="sync_perms", description="Sync channel permissions with its category.")
    @app_commands.describe(channel="Channel to sync")
    async def cmd_sync_perms(self, interaction: discord.Interaction, channel: discord.TextChannel | discord.VoiceChannel) -> None:
        try:
            await channel.edit(sync_permissions=True, reason=f"Synced by {interaction.user}")
            await interaction.response.send_message(f"{CHECK_OK} {channel.mention} permissions synced.")
        except discord.Forbidden:
            await interaction.response.send_message(f"{CROSS_NO} I can't do that.", ephemeral=True)

    @app_commands.command(name="channel_rename", description="Rename a channel.")
    @app_commands.describe(channel="Channel to rename", name="New name")
    async def cmd_channel_rename(self, interaction: discord.Interaction, channel: discord.TextChannel | discord.VoiceChannel, name: str) -> None:
        try:
            await channel.edit(name=name, reason=f"Renamed by {interaction.user}")
            await interaction.response.send_message(f"{CHECK_OK} Channel renamed to **{name}**.")
        except discord.Forbidden:
            await interaction.response.send_message(f"{CROSS_NO} I can't do that.", ephemeral=True)

    @app_commands.command(name="category_create", description="Create a new category.")
    @app_commands.describe(name="Category name")
    async def cmd_category_create(self, interaction: discord.Interaction, name: str) -> None:
        if not isinstance(interaction.guild, discord.Guild):
            await interaction.response.send_message(f"{CROSS_NO} Use in a server.", ephemeral=True)
            return
        try:
            cat = await interaction.guild.create_category(name, reason=f"Created by {interaction.user}")
            await interaction.response.send_message(f"{CHECK_OK} Category **{cat.name}** created.")
        except discord.Forbidden:
            await interaction.response.send_message(f"{CROSS_NO} I can't do that.", ephemeral=True)

    @app_commands.command(name="category_delete", description="Delete a category and all channels inside.")
    @app_commands.describe(category="Category to delete")
    async def cmd_category_delete(self, interaction: discord.Interaction, category: discord.CategoryChannel) -> None:
        await interaction.response.defer(ephemeral=True)
        deleted = 0
        for ch in category.channels:
            try:
                await ch.delete(reason=f"Category deleted by {interaction.user}")
                deleted += 1
            except discord.Forbidden:
                pass
        try:
            await category.delete(reason=f"Deleted by {interaction.user}")
        except discord.Forbidden:
            pass
        await interaction.followup.send(f"{CHECK_OK} Deleted category **{category.name}** and {deleted} channels.")

    # ══════════════════════════════════════════════════════════════
    #  THREAD MODERATION
    # ══════════════════════════════════════════════════════════════

    @app_commands.command(name="thread_create", description="Create a thread in a channel.")
    @app_commands.describe(channel="Channel to create thread in", name="Thread name")
    async def cmd_thread_create(self, interaction: discord.Interaction, channel: discord.TextChannel, name: str) -> None:
        try:
            thread = await channel.create_thread(name=name, reason=f"Created by {interaction.user}")
            await interaction.response.send_message(f"{CHECK_OK} Thread **{name}** created in {channel.mention}.")
        except discord.Forbidden:
            await interaction.response.send_message(f"{CROSS_NO} I can't do that.", ephemeral=True)

    @app_commands.command(name="thread_delete", description="Delete a thread.")
    @app_commands.describe(thread="Thread to delete")
    async def cmd_thread_delete(self, interaction: discord.Interaction, thread: discord.Thread) -> None:
        try:
            await thread.delete(reason=f"Deleted by {interaction.user}")
            await interaction.response.send_message(f"{CHECK_OK} Thread deleted.")
        except discord.Forbidden:
            await interaction.response.send_message(f"{CROSS_NO} I can't do that.", ephemeral=True)

    @app_commands.command(name="thread_lock", description="Lock a thread.")
    @app_commands.describe(thread="Thread to lock")
    async def cmd_thread_lock(self, interaction: discord.Interaction, thread: discord.Thread) -> None:
        try:
            await thread.edit(locked=True, reason=f"Locked by {interaction.user}")
            await interaction.response.send_message(f"{CHECK_OK} Thread locked.")
        except discord.Forbidden:
            await interaction.response.send_message(f"{CROSS_NO} I can't do that.", ephemeral=True)

    @app_commands.command(name="thread_unlock", description="Unlock a thread.")
    @app_commands.describe(thread="Thread to unlock")
    async def cmd_thread_unlock(self, interaction: discord.Interaction, thread: discord.Thread) -> None:
        try:
            await thread.edit(locked=False, reason=f"Unlocked by {interaction.user}")
            await interaction.response.send_message(f"{CHECK_OK} Thread unlocked.")
        except discord.Forbidden:
            await interaction.response.send_message(f"{CROSS_NO} I can't do that.", ephemeral=True)

    @app_commands.command(name="archive_all", description="Archive all active threads in the server.")
    async def cmd_archive_all(self, interaction: discord.Interaction) -> None:
        if not isinstance(interaction.guild, discord.Guild):
            await interaction.response.send_message(f"{CROSS_NO} Use in a server.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        archived = 0
        for ch in interaction.guild.text_channels:
            for thread in ch.threads:
                if not thread.archived:
                    try:
                        await thread.edit(archived=True, reason=f"Archived by {interaction.user}")
                        archived += 1
                    except discord.Forbidden:
                        pass
        await interaction.followup.send(f"{CHECK_OK} Archived {archived} threads.")

    # ══════════════════════════════════════════════════════════════
    #  ERROR HANDLING
    # ══════════════════════════════════════════════════════════════

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
        if isinstance(error, app_commands.MissingPermissions):
            txt = ", ".join(error.missing_permissions)
            await interaction.response.send_message(f"{CROSS_NO} You need `{txt}` permission.", ephemeral=True)
        else:
            await interaction.response.send_message(f"{CROSS_NO} Error: {error}", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ModerationExtCog(bot))
