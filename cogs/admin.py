from __future__ import annotations

import aiosqlite
import discord
from discord import app_commands
from discord.ext import commands

from cogs.emojis import CHECK_OK, CROSS_NO, HELP_ECONOMY


class AdminCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="setaichannel", description="Set channel for automatic AI replies.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_ai_channel(
        self, interaction: discord.Interaction, channel: discord.TextChannel
    ) -> None:
        if not interaction.guild:
            await interaction.response.send_message(f"{CROSS_NO} Server only command.", ephemeral=True)
            return
        await self.bot.db.upsert_guild_setting(interaction.guild.id, "ai_channel_id", channel.id)  # type: ignore[attr-defined]
        await interaction.response.send_message(
            f"{CHECK_OK} AI auto-reply channel set to {channel.mention}.", ephemeral=True
        )

    @app_commands.command(name="toggleautoreply", description="Enable or disable AI auto reply.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def toggle_auto_reply(
        self, interaction: discord.Interaction, enabled: bool
    ) -> None:
        if not interaction.guild:
            await interaction.response.send_message(f"{CROSS_NO} Server only command.", ephemeral=True)
            return
        await self.bot.db.upsert_guild_setting(interaction.guild.id, "auto_reply_enabled", int(enabled))  # type: ignore[attr-defined]
        await interaction.response.send_message(
            f"{CHECK_OK} AI auto-reply is now {'enabled' if enabled else 'disabled'}.", ephemeral=True
        )

    @app_commands.command(name="setsupportchannel", description="Set support channel for ticket creation.")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def set_support_channel(
        self, interaction: discord.Interaction, channel: discord.TextChannel
    ) -> None:
        if not interaction.guild:
            await interaction.response.send_message(f"{CROSS_NO} Server only command.", ephemeral=True)
            return
        await self.bot.db.upsert_guild_setting(interaction.guild.id, "support_channel_id", channel.id)  # type: ignore[attr-defined]
        await interaction.response.send_message(
            f"{CHECK_OK} Support channel set to {channel.mention}.", ephemeral=True
        )

    @app_commands.command(name="setsystemprompt", description="Set server-level AI system prompt.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_system_prompt(self, interaction: discord.Interaction, prompt: str) -> None:
        if not interaction.guild:
            await interaction.response.send_message(f"{CROSS_NO} Server only command.", ephemeral=True)
            return
        await self.bot.db.upsert_guild_setting(interaction.guild.id, "system_prompt", prompt[:2000])  # type: ignore[attr-defined]
        await interaction.response.send_message(f"{CHECK_OK} Server system prompt updated.", ephemeral=True)

    @app_commands.command(name="announce", description="Send an announcement as the bot.")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def announce(
        self, interaction: discord.Interaction, channel: discord.TextChannel, message: str
    ) -> None:
        await channel.send(f"📢 **Announcement**\n{message}")
        await interaction.response.send_message(f"{CHECK_OK} Announcement sent.", ephemeral=True)

    # ---- New Admin Commands ----

    WELCOME_VARS = "{user} - mention, {username} - name, {server} - server name, {count} - member count"

    @app_commands.command(name="welcome", description="Set welcome message for new members.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_welcome(
        self, interaction: discord.Interaction,
        channel: discord.TextChannel,
        message: str = "Welcome {user} to **{server}**! You are member #{count}.",
    ) -> None:
        if not interaction.guild:
            await interaction.response.send_message(f"{CROSS_NO} Server only command.", ephemeral=True)
            return
        await self.bot.db.upsert_guild_setting(interaction.guild.id, "welcome_channel", str(channel.id))  # type: ignore[attr-defined]
        await self.bot.db.upsert_guild_setting(interaction.guild.id, "welcome_message", message[:1000])  # type: ignore[attr-defined]
        await interaction.response.send_message(
            f"{CHECK_OK} Welcome message set for {channel.mention}.\n"
            f"Available variables: `{self.WELCOME_VARS}`",
            ephemeral=True,
        )

    @app_commands.command(name="leave", description="Set leave message when members leave.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_leave(
        self, interaction: discord.Interaction,
        channel: discord.TextChannel,
        message: str = "{username} left **{server}**.",
    ) -> None:
        if not interaction.guild:
            await interaction.response.send_message(f"{CROSS_NO} Server only command.", ephemeral=True)
            return
        await self.bot.db.upsert_guild_setting(interaction.guild.id, "leave_channel", str(channel.id))  # type: ignore[attr-defined]
        await self.bot.db.upsert_guild_setting(interaction.guild.id, "leave_message", message[:1000])  # type: ignore[attr-defined]
        await interaction.response.send_message(
            f"{CHECK_OK} Leave message set for {channel.mention}.\n"
            f"Available variables: `{self.WELCOME_VARS}`",
            ephemeral=True,
        )

    @app_commands.command(name="autorole", description="Set a role to auto-assign on member join.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_autorole(
        self, interaction: discord.Interaction, role: discord.Role
    ) -> None:
        if not interaction.guild:
            await interaction.response.send_message(f"{CROSS_NO} Server only command.", ephemeral=True)
            return
        if role >= interaction.guild.me.top_role:
            await interaction.response.send_message(
                f"{CROSS_NO} I cannot assign that role (it's above my highest role).", ephemeral=True
            )
            return
        await self.bot.db.upsert_guild_setting(interaction.guild.id, "autorole_id", str(role.id))  # type: ignore[attr-defined]
        await interaction.response.send_message(
            f"{CHECK_OK} Auto-role set to {role.mention}. New members will get this role.", ephemeral=True
        )

    @app_commands.command(name="removeautorole", description="Remove auto-role setting.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def remove_autorole(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            await interaction.response.send_message(f"{CROSS_NO} Server only command.", ephemeral=True)
            return
        await self.bot.db.upsert_guild_setting(interaction.guild.id, "autorole_id", "")  # type: ignore[attr-defined]
        await interaction.response.send_message(f"{CHECK_OK} Auto-role removed.", ephemeral=True)

    # ══════════════════════════════════════════════════════════════
    #  ADMIN ECONOMY COMMANDS
    # ══════════════════════════════════════════════════════════════

    eco = app_commands.Group(name="eco", description="Admin economy management commands.")

    @eco.command(name="give", description="Give coins to a user (adds to wallet).")
    @app_commands.checks.has_permissions(administrator=True)
    async def eco_give(
        self, interaction: discord.Interaction, user: discord.User, amount: app_commands.Range[int, 1, 10_000_000]
    ) -> None:
        async with aiosqlite.connect(self.bot.db.db_path) as db:  # type: ignore[attr-defined]
            await db.execute("INSERT OR IGNORE INTO economy (user_id) VALUES (?)", (user.id,))
            await db.execute(
                "UPDATE economy SET balance = balance + ?, total_earned = total_earned + ? WHERE user_id = ?",
                (amount, amount, user.id),
            )
            await db.commit()
        await interaction.response.send_message(
            f"{CHECK_OK} Gave {HELP_ECONOMY} **{amount}** coins to {user.mention}.", ephemeral=True
        )

    @eco.command(name="take", description="Remove coins from a user's wallet.")
    @app_commands.checks.has_permissions(administrator=True)
    async def eco_take(
        self, interaction: discord.Interaction, user: discord.User, amount: app_commands.Range[int, 1, 10_000_000]
    ) -> None:
        async with aiosqlite.connect(self.bot.db.db_path) as db:  # type: ignore[attr-defined]
            cur = await db.execute(
                "UPDATE economy SET balance = balance - ?, total_spent = total_spent + ? WHERE user_id = ? AND balance >= ?",
                (amount, amount, user.id, amount),
            )
            await db.commit()
            if cur.rowcount == 0:
                await interaction.response.send_message(
                    f"{CROSS_NO} {user.mention} doesn't have enough coins.", ephemeral=True
                )
                return
        await interaction.response.send_message(
            f"{CHECK_OK} Took {HELP_ECONOMY} **{amount}** coins from {user.mention}.", ephemeral=True
        )

    @eco.command(name="set", description="Set a user's wallet balance to an exact amount.")
    @app_commands.checks.has_permissions(administrator=True)
    async def eco_set(
        self, interaction: discord.Interaction, user: discord.User, amount: app_commands.Range[int, 0, 10_000_000]
    ) -> None:
        async with aiosqlite.connect(self.bot.db.db_path) as db:  # type: ignore[attr-defined]
            await db.execute("INSERT OR IGNORE INTO economy (user_id) VALUES (?)", (user.id,))
            await db.execute(
                "UPDATE economy SET balance = ?, total_earned = total_earned + ? WHERE user_id = ?",
                (amount, max(0, amount), user.id),
            )
            await db.commit()
        await interaction.response.send_message(
            f"{CHECK_OK} Set {user.mention}'s wallet to {HELP_ECONOMY} **{amount}** coins.", ephemeral=True
        )

    # ---- Error Handler ----

    @set_ai_channel.error
    @toggle_auto_reply.error
    @set_support_channel.error
    @set_system_prompt.error
    @announce.error
    @set_welcome.error
    @set_leave.error
    @set_autorole.error
    @remove_autorole.error
    async def admin_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ) -> None:
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                f"{CROSS_NO} You don't have required permissions.", ephemeral=True
            )
            return
        await interaction.response.send_message(f"{CROSS_NO} Command failed: `{error}`", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AdminCog(bot))
