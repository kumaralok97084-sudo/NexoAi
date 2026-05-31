from __future__ import annotations

import time

import discord
import psutil
from discord import app_commands
from discord.ext import commands


class TicketModal(discord.ui.Modal, title="Create Support Ticket"):
    issue = discord.ui.TextInput(
        label="Describe your issue",
        style=discord.TextStyle.paragraph,
        max_length=1000,
        required=True,
        placeholder="Explain what you need help with...",
    )

    def __init__(self, cog: "GeneralCog") -> None:
        super().__init__(timeout=300)
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            await interaction.response.send_message(
                "This command works only in servers.", ephemeral=True
            )
            return

        support_channel_id = await self.cog.bot.db.get_guild_setting(interaction.guild.id, "support_channel_id")  # type: ignore[attr-defined]
        if not support_channel_id:
            await interaction.response.send_message(
                "Support channel is not configured yet.", ephemeral=True
            )
            return

        support_channel = interaction.guild.get_channel(int(support_channel_id))
        if not isinstance(support_channel, discord.TextChannel):
            await interaction.response.send_message(
                "Configured support channel is invalid.", ephemeral=True
            )
            return

        embed = discord.Embed(
            title="New Support Ticket",
            color=discord.Color.blurple(),
            description=self.issue.value,
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(name="User", value=interaction.user.mention, inline=True)
        embed.add_field(name="User ID", value=str(interaction.user.id), inline=True)
        await support_channel.send(embed=embed)
        await interaction.response.send_message(
            "Your ticket has been sent to support.", ephemeral=True
        )


class GeneralCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="helpme", description="Show all major bot features.")
    async def helpme(self, interaction: discord.Interaction) -> None:
        embed = discord.Embed(
            title="NexoAI Bot Commands",
            color=discord.Color.green(),
            description="AI, support, hosting utilities, and moderation helpers.",
        )
        embed.add_field(
            name="🤖 AI & Memory",
            value=(
                "`/ai`, `/websearch`, `/imagine`, `/imagemodels`, `/summarize`, `/translate`, "
                "`/rewrite`, `/code`, `/codereview`, `/debug`, `/refactor`, `/explaincode`, "
                "`/train`, `/knowledge`, `/thread`, `/forget`, `/context`, `/custom`, "
                "`/setpersona`, `/agent`, `/agents`, `/clearhistory`, "
                "`/mymemory`, `/mypreferences`, `/clearmemory`, `/usage`"
            ),
            inline=False,
        )
        embed.add_field(
            name="🛡️ Moderation",
            value=(
                "`/purge`, `/timeout`, `/untimeout`, `/mute`, `/warn`, `/unwarn`, `/warns`, `/modlogs`, "
                "`/kick`, `/ban`, `/unban`, `/softban`, `/slowmode`, `/lock`, `/unlock`, `/lockdown`, `/unlockall`, "
                "`/clean`, `/nick`, `/filter`, `/filtermode`, `/raidmode`, `/antispam`, `/modsettings`"
            ),
            inline=False,
        )
        embed.add_field(
            name="⚙️ Admin",
            value=(
                "`/setaichannel`, `/toggleautoreply`, `/setsupportchannel`, "
                "`/setsystemprompt`, `/announce`, `/welcome`, `/leave`, `/autorole`, `/removeautorole`"
            ),
            inline=False,
        )
        embed.add_field(
            name="🔧 Utility",
            value="`/poll`, `/remind`, `/timer`, `/note`, `/notes`, `/rolemenu`, `/define`, `/weather`, `/color`",
            inline=False,
        )
        embed.add_field(
            name="🌐 Hosting",
            value=(
                "`/pinghost`, `/dns`, `/whois`, `/sslcheck`, `/portscan`, `/traceroute`, "
                "`/httpcheck`, `/headers`"
            ),
            inline=False,
        )
        embed.add_field(
            name="ℹ️ General",
            value="`/ping`, `/uptime`, `/serverinfo`, `/membercount`, `/userinfo`, `/ticket`",
            inline=False,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="ping", description="Check bot latency.")
    async def ping(self, interaction: discord.Interaction) -> None:
        latency = round(self.bot.latency * 1000)
        await interaction.response.send_message(f"Pong! `{latency}ms`")

    @app_commands.command(name="uptime", description="Show bot uptime and system usage.")
    async def uptime(self, interaction: discord.Interaction) -> None:
        started = self.bot.start_time  # type: ignore[attr-defined]
        elapsed = int(time.time() - started)
        hours, rem = divmod(elapsed, 3600)
        minutes, seconds = divmod(rem, 60)

        cpu = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory().percent
        await interaction.response.send_message(
            f"Uptime: `{hours}h {minutes}m {seconds}s` | CPU: `{cpu}%` | RAM: `{mem}%`"
        )

    @app_commands.command(name="serverinfo", description="Show current server information.")
    async def server_info(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        if not guild:
            await interaction.response.send_message("Use this in a server.", ephemeral=True)
            return
        embed = discord.Embed(title=f"{guild.name} - Server Info", color=discord.Color.gold())
        embed.add_field(name="Members", value=str(guild.member_count), inline=True)
        embed.add_field(
            name="Humans/Bots",
            value=f"{sum(1 for m in guild.members if not m.bot)}/{sum(1 for m in guild.members if m.bot)}",
            inline=True,
        )
        embed.add_field(name="Channels", value=str(len(guild.channels)), inline=True)
        embed.add_field(name="Roles", value=str(len(guild.roles)), inline=True)
        embed.add_field(name="Owner", value=str(guild.owner), inline=True)
        embed.add_field(name="Server ID", value=str(guild.id), inline=True)
        embed.set_thumbnail(url=guild.icon.url if guild.icon else discord.Embed.Empty)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="userinfo", description="Show user information.")
    async def user_info(
        self, interaction: discord.Interaction, user: discord.User | None = None
    ) -> None:
        target = user or interaction.user
        embed = discord.Embed(title=f"{target} - User Info", color=discord.Color.teal())
        embed.add_field(name="ID", value=str(target.id), inline=True)
        embed.add_field(name="Created", value=str(target.created_at)[:19], inline=True)
        embed.add_field(name="Bot Account", value=str(target.bot), inline=True)
        if interaction.guild:
            member = interaction.guild.get_member(target.id)
            if member:
                embed.add_field(name="Joined", value=str(member.joined_at)[:19], inline=True)
                embed.add_field(name="Top Role", value=member.top_role.mention, inline=True)
                embed.add_field(name="Nickname", value=member.nick or "None", inline=True)
        embed.set_thumbnail(url=target.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="membercount", description="Show total, human, and bot member counts.")
    async def member_count(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        if not guild:
            await interaction.response.send_message("Use this in a server.", ephemeral=True)
            return
        humans = sum(1 for m in guild.members if not m.bot)
        bots = sum(1 for m in guild.members if m.bot)
        await interaction.response.send_message(
            f"Members: **{guild.member_count}** | Humans: **{humans}** | Bots: **{bots}**"
        )

    @app_commands.command(name="ticket", description="Create a support ticket.")
    async def ticket(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(TicketModal(self))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(GeneralCog(bot))
