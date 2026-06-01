from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Any

import aiosqlite
import discord
from discord import app_commands
from discord.ext import commands

from cogs.emojis import BEGGING, BRONZE, CHECK_OK, COOLDOWN, CRIME, DAILY, DICE, EARNED, GIVEAWAY, GIVEAWAY_WIN, GOLD, HELP_ECONOMY, HELP_FUN, JOB_CHEF, JOB_CODER, JOB_DOCTOR, JOB_ENGINEER, JOB_FARMER, JOB_FISHER, JOB_MINER, JOB_TEACHER, SILVER, SLOT_DIAMOND, SPENT, STREAK, WITHDRAW, WORK_BRIEF

DAILY_AMOUNT = 100
STREAK_BONUS = 25
WORK_MIN = 15
WORK_MAX = 75
WORK_COOLDOWN = 1800
BEG_MIN = 1
BEG_MAX = 25
BEG_COOLDOWN = 300
CRIME_MIN = 50
CRIME_MAX = 300
CRIME_FAIL_PENALTY = 100
CRIME_SUCCESS_RATE = 0.4
CRIME_COOLDOWN = 600
ROB_COOLDOWN = 3600
ROB_TAKE_MIN = 0.10
ROB_TAKE_MAX = 0.25
ROB_FAIL_FINE = 50

JOBS = [
    (JOB_CODER, "programmer", 40, 90),
    (HELP_FUN, "designer", 40, 80),
    (WORK_BRIEF, "consultant", 30, 100),
    (JOB_TEACHER, "teacher", 30, 60),
    (JOB_MINER, "miner", 25, 70),
    (JOB_FISHER, "fisher", 25, 55),
    (JOB_FARMER, "farmer", 0, 50),
    (JOB_CHEF, "chef", 30, 65),
    (JOB_DOCTOR, "doctor", 55, 120),
    (JOB_ENGINEER, "engineer", 55, 95),
]

CRIMES = [
    "hacked a server", "picked a lock", "sold illegal goods",
    "rigged an auction", "stole crypto", "ran a gambling den",
    "smuggled goods", "broke into a vault",
]

CRIME_FAILS = [
    "got caught by police", "triggered an alarm", "left evidence behind",
    "was snitched on", "failed the hack", "tripped the security system",
]


class EconomyCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    # ── Atomic helpers ──

    async def _ensure_user(self, uid: int) -> None:
        async with aiosqlite.connect(self.bot.db.db_path) as db:
            await db.execute("INSERT OR IGNORE INTO economy (user_id) VALUES (?)", (uid,))
            await db.commit()

    async def _read(self, uid: int) -> dict[str, Any]:
        async with aiosqlite.connect(self.bot.db.db_path) as db:
            async with db.execute(
                "SELECT balance, bank, daily_streak, last_daily, last_work, "
                "last_crime, last_beg, last_rob, total_earned, total_spent "
                "FROM economy WHERE user_id = ?", (uid,)
            ) as cursor:
                row = await cursor.fetchone()
        if not row:
            return {"balance": 0, "bank": 0, "daily_streak": 0,
                    "last_daily": "", "last_work": "", "last_crime": "",
                    "last_beg": "", "last_rob": "", "total_earned": 0, "total_spent": 0}
        return {"balance": row[0], "bank": row[1], "daily_streak": row[2],
                "last_daily": row[3] or "", "last_work": row[4] or "",
                "last_crime": row[5] or "", "last_beg": row[6] or "",
                "last_rob": row[7] or "", "total_earned": row[8] or 0, "total_spent": row[9] or 0}

    async def _add_balance(self, uid: int, amount: int) -> int:
        """Atomically add coins to wallet + track earned. Returns new balance."""
        async with aiosqlite.connect(self.bot.db.db_path) as db:
            await db.execute("INSERT OR IGNORE INTO economy (user_id) VALUES (?)", (uid,))
            await db.execute(
                "UPDATE economy SET balance = balance + ?, total_earned = total_earned + ? WHERE user_id = ?",
                (amount, amount, uid),
            )
            await db.commit()
            async with db.execute("SELECT balance FROM economy WHERE user_id = ?", (uid,)) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0

    async def _sub_balance(self, uid: int, amount: int) -> tuple[bool, int]:
        """Atomically deduct coins if sufficient. Returns (succeeded, new_balance)."""
        if amount <= 0:
            return True, (await self._read(uid))["balance"]
        async with aiosqlite.connect(self.bot.db.db_path) as db:
            await db.execute("INSERT OR IGNORE INTO economy (user_id) VALUES (?)", (uid,))
            cursor = await db.execute(
                "UPDATE economy SET balance = balance - ?, total_spent = total_spent + ? WHERE user_id = ? AND balance >= ?",
                (amount, amount, uid, amount),
            )
            await db.commit()
            async with db.execute("SELECT balance FROM economy WHERE user_id = ?", (uid,)) as cursor2:
                row = await cursor2.fetchone()
                new_bal = row[0] if row else 0
            return cursor.rowcount > 0, new_bal

    async def _add_bank(self, uid: int, amount: int) -> int:
        """Atomically add coins to bank. Returns new bank balance."""
        async with aiosqlite.connect(self.bot.db.db_path) as db:
            await db.execute("INSERT OR IGNORE INTO economy (user_id) VALUES (?)", (uid,))
            await db.execute(
                "UPDATE economy SET bank = bank + ? WHERE user_id = ?", (amount, uid),
            )
            await db.commit()
            async with db.execute("SELECT bank FROM economy WHERE user_id = ?", (uid,)) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0

    async def _sub_bank(self, uid: int, amount: int) -> tuple[bool, int]:
        """Atomically deduct from bank if sufficient. Returns (succeeded, new_bank)."""
        async with aiosqlite.connect(self.bot.db.db_path) as db:
            await db.execute("INSERT OR IGNORE INTO economy (user_id) VALUES (?)", (uid,))
            cursor = await db.execute(
                "UPDATE economy SET bank = bank - ? WHERE user_id = ? AND bank >= ?",
                (amount, uid, amount),
            )
            await db.commit()
            async with db.execute("SELECT bank FROM economy WHERE user_id = ?", (uid,)) as cursor2:
                row = await cursor2.fetchone()
                new_bank = row[0] if row else 0
            return cursor.rowcount > 0, new_bank

    async def _set_fields(self, uid: int, **kwargs: Any) -> None:
        """Atomically set one or more fields."""
        if not kwargs:
            return
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        params = list(kwargs.values()) + [uid]
        async with aiosqlite.connect(self.bot.db.db_path) as db:
            await db.execute("INSERT OR IGNORE INTO economy (user_id) VALUES (?)", (uid,))
            await db.execute(f"UPDATE economy SET {sets} WHERE user_id = ?", params)
            await db.commit()

    def _cd_remaining(self, last_time: str, cooldown: int) -> int:
        if not last_time:
            return 0
        try:
            last = datetime.fromisoformat(last_time)
            if last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
            elapsed = (datetime.now(timezone.utc) - last).total_seconds()
            return max(0, int(cooldown - elapsed))
        except (ValueError, TypeError, OSError):
            return 0

    # ── Bal ──

    @app_commands.command(name="bal", description="Check your or another user's balance.")
    async def bal(self, interaction: discord.Interaction, user: discord.User | None = None) -> None:
        target = user or interaction.user
        d = await self._read(target.id)
        embed = discord.Embed(
            title=f"{target.display_name}'s Wallet",
            color=discord.Color.blue(),
        )
        embed.add_field(name=f"{HELP_ECONOMY} Wallet", value=f"**{d['balance']}**", inline=True)
        embed.add_field(name=f"{WITHDRAW} Bank", value=f"**{d['bank']}**", inline=True)
        embed.add_field(name=f"{SLOT_DIAMOND} Total", value=f"**{d['balance'] + d['bank']}**", inline=True)
        embed.add_field(name=f"{EARNED} Earned", value=f"**{d['total_earned']}**", inline=True)
        embed.add_field(name=f"{SPENT} Spent", value=f"**{d['total_spent']}**", inline=True)
        embed.set_thumbnail(url=target.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="baltop", description="Show the richest users.")
    async def baltop(self, interaction: discord.Interaction) -> None:
        async with aiosqlite.connect(self.bot.db.db_path) as db:
            async with db.execute(
                "SELECT user_id, balance + bank AS total FROM economy ORDER BY total DESC LIMIT 10"
            ) as cursor:
                rows = await cursor.fetchall()
        if not rows:
            await interaction.response.send_message("No economy data yet.", ephemeral=True)
            return
        lines = []
        for i, (uid, total) in enumerate(rows, 1):
            user = self.bot.get_user(uid)
            name = user.display_name if user else "Unknown"
            medal = {1: GOLD, 2: SILVER, 3: BRONZE}.get(i, f"{i}.")
            lines.append(f"{medal} **{name}** — {SLOT_DIAMOND} {total}")
        embed = discord.Embed(title=f"{GIVEAWAY_WIN} Richest Users", description="\n".join(lines), color=discord.Color.gold())
        await interaction.response.send_message(embed=embed)

    # ── Daily ──

    @app_commands.command(name="daily", description="Claim your daily reward.")
    async def daily(self, interaction: discord.Interaction) -> None:
        uid = interaction.user.id
        d = await self._read(uid)
        now = datetime.now(timezone.utc)

        cd = self._cd_remaining(d["last_daily"], 86400)
        if cd > 0:
            h, r = divmod(cd, 3600)
            m = r // 60
            await interaction.response.send_message(f"{COOLDOWN} Come back in **{h}h {m}m**.", ephemeral=True)
            return

        last = d["last_daily"]
        if last:
            try:
                last_dt = datetime.fromisoformat(last)
                if last_dt.tzinfo is None:
                    last_dt = last_dt.replace(tzinfo=timezone.utc)
                streak = d["daily_streak"] + 1 if (now - last_dt).total_seconds() < 172800 else 1
            except (ValueError, TypeError):
                streak = 1
        else:
            streak = 1

        bonus = STREAK_BONUS * (streak - 1)
        amount = DAILY_AMOUNT + bonus
        new_bal = await self._add_balance(uid, amount)
        await self._set_fields(uid, daily_streak=streak, last_daily=now.isoformat())

        embed = discord.Embed(title=f"{DAILY} Daily Reward", color=discord.Color.gold())
        embed.add_field(name="Claimed", value=f"{HELP_ECONOMY} {amount}", inline=True)
        if bonus:
            embed.add_field(name="Bonus", value=f"{STREAK} +{bonus}", inline=True)
        embed.add_field(name="Streak", value=f"{streak} day(s)", inline=True)
        embed.add_field(name="Balance", value=f"{new_bal}", inline=False)
        await interaction.response.send_message(embed=embed)

    # ── Work ──

    @app_commands.command(name="work", description="Work to earn coins.")
    async def work(self, interaction: discord.Interaction) -> None:
        uid = interaction.user.id
        d = await self._read(uid)
        cd = self._cd_remaining(d["last_work"], WORK_COOLDOWN)
        if cd > 0:
            m, s = divmod(cd, 60)
            await interaction.response.send_message(f"{COOLDOWN} Rest **{m}m {s}s** before working again.", ephemeral=True)
            return

        emoji, job, wmin, wmax = random.choice(JOBS)
        earnings = random.randint(wmin, wmax)
        new_bal = await self._add_balance(uid, earnings)
        await self._set_fields(uid, last_work=datetime.now(timezone.utc).isoformat())

        embed = discord.Embed(title=f"{emoji} Work Complete", color=discord.Color.green())
        embed.add_field(name="Job", value=job.capitalize(), inline=True)
        embed.add_field(name="Earned", value=f"{HELP_ECONOMY} {earnings}", inline=True)
        embed.add_field(name="Balance", value=f"{new_bal}", inline=False)
        await interaction.response.send_message(embed=embed)

    # ── Beg ──

    @app_commands.command(name="beg", description="Beg for some coins.")
    async def beg(self, interaction: discord.Interaction) -> None:
        uid = interaction.user.id
        d = await self._read(uid)
        cd = self._cd_remaining(d["last_beg"], BEG_COOLDOWN)
        if cd > 0:
            await interaction.response.send_message(f"{COOLDOWN} Wait **{cd}s** before begging again.", ephemeral=True)
            return

        amount = random.randint(BEG_MIN, BEG_MAX)
        donors = ["a kind stranger", "a rich tourist", "your grandma", "a generous bot",
                  "a mysterious figure", "a charity fund", "a lost wallet"]
        donor = random.choice(donors)
        new_bal = await self._add_balance(uid, amount)
        await self._set_fields(uid, last_beg=datetime.now(timezone.utc).isoformat())

        embed = discord.Embed(
            title=f"{BEGGING} Begging",
            description=f"{donor} gave you **{amount}** coins!",
            color=discord.Color.teal(),
        )
        embed.add_field(name="Balance", value=f"{new_bal}", inline=False)
        await interaction.response.send_message(embed=embed)

    # ── Crime ──

    @app_commands.command(name="crime", description="Commit a crime for high risk/reward.")
    async def crime(self, interaction: discord.Interaction) -> None:
        uid = interaction.user.id
        d = await self._read(uid)
        cd = self._cd_remaining(d["last_crime"], CRIME_COOLDOWN)
        if cd > 0:
            await interaction.response.send_message(f"{COOLDOWN} Wait **{cd}s**.", ephemeral=True)
            return

        success = random.random() < CRIME_SUCCESS_RATE
        now = datetime.now(timezone.utc)
        act = random.choice(CRIMES if success else CRIME_FAILS)

        if success:
            loot = random.randint(CRIME_MIN, CRIME_MAX)
            new_bal = await self._add_balance(uid, loot)
            desc = f"You {act} and got away with **{loot}** coins!"
            color = discord.Color.green()
        else:
            fine = random.randint(CRIME_FAIL_PENALTY // 2, CRIME_FAIL_PENALTY)
            ok, new_bal = await self._sub_balance(uid, fine)
            if not ok:
                await interaction.response.send_message("You need coins in your wallet to attempt a crime.", ephemeral=True)
                return
            desc = f"You {act} and paid a fine of **{fine}** coins!"
            color = discord.Color.red()

        await self._set_fields(uid, last_crime=now.isoformat())
        embed = discord.Embed(title=f"{CRIME} Crime", description=desc, color=color)
        embed.add_field(name="Balance", value=f"{new_bal}", inline=False)
        await interaction.response.send_message(embed=embed)

    # ── Gamble ──

    @app_commands.command(name="gamble", description="Gamble your coins (50/50 double or nothing).")
    async def gamble(self, interaction: discord.Interaction, amount: int) -> None:
        if amount < 5:
            await interaction.response.send_message("Minimum gamble is **5** coins.", ephemeral=True)
            return

        win = random.random() < 0.5
        if win:
            new_bal = await self._add_balance(interaction.user.id, amount)
            result = f"You won **{amount}** coins! {GIVEAWAY}"
            color = discord.Color.green()
        else:
            ok, new_bal = await self._sub_balance(interaction.user.id, amount)
            if not ok:
                await interaction.response.send_message(f"You don't have **{amount}** coins.", ephemeral=True)
                return
            result = f"You lost **{amount}** coins. 😅"
            color = discord.Color.red()

        embed = discord.Embed(title=f"{DICE} Gamble", description=result, color=color)
        embed.add_field(name="Balance", value=f"{new_bal}", inline=False)
        await interaction.response.send_message(embed=embed)

    # ── Rob ──

    @app_commands.command(name="rob", description="Rob another user.")
    async def rob(self, interaction: discord.Interaction, user: discord.User) -> None:
        if user.id == interaction.user.id:
            await interaction.response.send_message("You can't rob yourself.", ephemeral=True)
            return
        if user.bot:
            await interaction.response.send_message("You can't rob a bot.", ephemeral=True)
            return

        uid = interaction.user.id
        d = await self._read(uid)
        cd = self._cd_remaining(d["last_rob"], ROB_COOLDOWN)
        if cd > 0:
            m, s = divmod(cd, 60)
            await interaction.response.send_message(f"{COOLDOWN} Wait **{m}m {s}s**.", ephemeral=True)
            return

        target = await self._read(user.id)
        if target["balance"] < 50:
            await interaction.response.send_message(f"{user.display_name} is too poor to rob.", ephemeral=True)
            return

        success = random.random() < 0.45
        now = datetime.now(timezone.utc)

        async with aiosqlite.connect(self.bot.db.db_path) as db:
            if success:
                take_pct = random.uniform(ROB_TAKE_MIN, ROB_TAKE_MAX)
                take = max(5, int(target["balance"] * take_pct))
                cursor = await db.execute(
                    "UPDATE economy SET balance = balance - ?, total_spent = total_spent + ? WHERE user_id = ? AND balance >= ?",
                    (take, take, user.id, take),
                )
                if cursor.rowcount == 0:
                    await interaction.response.send_message("They lost their coins before you could rob them!", ephemeral=True)
                    return
                await db.execute("INSERT OR IGNORE INTO economy (user_id) VALUES (?)", (uid,))
                await db.execute(
                    "UPDATE economy SET balance = balance + ?, total_earned = total_earned + ? WHERE user_id = ?",
                    (take, take, uid),
                )
                desc = f"You robbed **{take}** coins from {user.mention}!"
                color = discord.Color.green()
            else:
                fine = min(ROB_FAIL_FINE, d["balance"])
                cursor = await db.execute(
                    "UPDATE economy SET balance = balance - ?, total_spent = total_spent + ? WHERE user_id = ? AND balance >= ?",
                    (fine, fine, uid, fine),
                )
                if cursor.rowcount == 0:
                    await interaction.response.send_message("You tried to rob but got caught! No fine since you're broke.", ephemeral=True)
                    await self._set_fields(uid, last_rob=now.isoformat())
                    return
                desc = f"You got caught and paid **{fine}** coins to {user.mention}!"
                color = discord.Color.red()

            await db.execute(
                "UPDATE economy SET last_rob = ? WHERE user_id = ?", (now.isoformat(), uid),
            )
            await db.commit()

            async with db.execute("SELECT balance FROM economy WHERE user_id = ?", (uid,)) as cursor:
                row = await cursor.fetchone()
                new_bal = row[0] if row else 0

        embed = discord.Embed(title=f"{CRIME} Robbery", description=desc, color=color)
        embed.add_field(name="Your Balance", value=f"{new_bal}", inline=True)
        await interaction.response.send_message(embed=embed)

    # ── Pay ──

    @app_commands.command(name="pay", description="Send coins to another user.")
    async def pay(self, interaction: discord.Interaction, user: discord.User, amount: int) -> None:
        if amount < 1:
            await interaction.response.send_message("Amount must be at least 1.", ephemeral=True)
            return
        if user.id == interaction.user.id:
            await interaction.response.send_message("You can't pay yourself.", ephemeral=True)
            return

        async with aiosqlite.connect(self.bot.db.db_path) as db:
            await db.execute("BEGIN")
            cursor = await db.execute(
                "UPDATE economy SET balance = balance - ?, total_spent = total_spent + ? WHERE user_id = ? AND balance >= ?",
                (amount, amount, interaction.user.id, amount),
            )
            if cursor.rowcount == 0:
                await db.execute("ROLLBACK")
                await interaction.response.send_message("You don't have enough coins.", ephemeral=True)
                return
            await db.execute("INSERT OR IGNORE INTO economy (user_id) VALUES (?)", (user.id,))
            await db.execute(
                "UPDATE economy SET balance = balance + ?, total_earned = total_earned + ? WHERE user_id = ?",
                (amount, amount, user.id),
            )
            await db.commit()
            async with db.execute("SELECT balance FROM economy WHERE user_id = ?", (interaction.user.id,)) as cursor:
                row = await cursor.fetchone()
                new_bal = row[0] if row else 0

        await interaction.response.send_message(f"{CHECK_OK} Sent **{amount}** coins to {user.mention}. Your balance: **{new_bal}**")

    # ── Bank ──

    @app_commands.command(name="deposit", description="Deposit coins into your bank.")
    async def deposit(self, interaction: discord.Interaction, amount: str) -> None:
        uid = interaction.user.id
        if amount.lower() == "all":
            d = await self._read(uid)
            amt = d["balance"]
        else:
            try:
                amt = int(amount)
            except ValueError:
                await interaction.response.send_message("Enter a number or 'all'.", ephemeral=True)
                return

        if amt <= 0:
            await interaction.response.send_message("Amount must be positive.", ephemeral=True)
            return

        ok, new_wallet = await self._sub_balance(uid, amt)
        if not ok:
            await interaction.response.send_message("You don't have enough coins.", ephemeral=True)
            return
        new_bank = await self._add_bank(uid, amt)

        await interaction.response.send_message(f"{WITHDRAW} Deposited **{amt}** coins. Wallet: **{new_wallet}** | Bank: **{new_bank}**")

    @app_commands.command(name="withdraw", description="Withdraw coins from your bank.")
    async def withdraw(self, interaction: discord.Interaction, amount: str) -> None:
        uid = interaction.user.id
        if amount.lower() == "all":
            d = await self._read(uid)
            amt = d["bank"]
        else:
            try:
                amt = int(amount)
            except ValueError:
                await interaction.response.send_message("Enter a number or 'all'.", ephemeral=True)
                return

        if amt <= 0:
            await interaction.response.send_message("Amount must be positive.", ephemeral=True)
            return

        ok, new_bank = await self._sub_bank(uid, amt)
        if not ok:
            await interaction.response.send_message("Not enough coins in bank.", ephemeral=True)
            return
        new_wallet = await self._add_balance(uid, amt)

        await interaction.response.send_message(f"{WITHDRAW} Withdrew **{amt}** coins. Wallet: **{new_wallet}** | Bank: **{new_bank}**")

    # ── Inventory ──

    @app_commands.command(name="inventory", description="View your purchased items.")
    async def inventory(self, interaction: discord.Interaction) -> None:
        async with aiosqlite.connect(self.bot.db.db_path) as db:
            async with db.execute(
                """SELECT s.name, s.description, i.purchased_at
                   FROM inventory i JOIN shop_items s ON i.item_id = s.id
                   WHERE i.user_id = ? ORDER BY i.purchased_at DESC LIMIT 25""",
                (interaction.user.id,),
            ) as cursor:
                items = await cursor.fetchall()

        if not items:
            await interaction.response.send_message("You don't own any items.", ephemeral=True)
            return

        lines = [f"• **{i[0]}** — {i[1] or 'No description'}\n  `{i[2]}`" for i in items]
        embed = discord.Embed(title=f"{interaction.user.display_name}'s Inventory", description="\n".join(lines), color=discord.Color.green())
        await interaction.response.send_message(embed=embed)

    # ── Weekly ──

    @app_commands.command(name="weekly", description="Claim your weekly bonus.")
    async def weekly(self, interaction: discord.Interaction) -> None:
        uid = interaction.user.id
        now = datetime.now(timezone.utc)
        d = await self._read(uid)
        last = d.get("last_weekly", "")
        if last:
            try:
                delta = now - datetime.fromisoformat(last)
                if delta.days < 7:
                    remaining = 7 - delta.days
                    await interaction.response.send_message(f"{COOLDOWN} Come back in **{remaining}d** for your weekly.", ephemeral=True)
                    return
            except ValueError:
                pass
        async with aiosqlite.connect(self.bot.db.db_path) as db:
            await db.execute(
                "UPDATE economy SET balance = balance + ?, total_earned = total_earned + ?, last_weekly = ? WHERE user_id = ?",
                (DAILY_AMOUNT * 5, DAILY_AMOUNT * 5, now.isoformat(), uid),
            )
            await db.commit()
        await interaction.response.send_message(f"{DAILY} Weekly bonus: **{DAILY_AMOUNT * 5}** coins!")

    # ── Search ──

    SEARCH_PLACES = ["the couch cushions", "the trash bin", "an old jacket", "the parking lot", "a random drawer", "the garden"]

    @app_commands.command(name="search", description="Search for coins in random places.")
    async def search(self, interaction: discord.Interaction) -> None:
        uid = interaction.user.id
        now = datetime.now(timezone.utc)
        d = await self._read(uid)
        last = d.get("last_search", "")
        if last:
            try:
                delta = now - datetime.fromisoformat(last)
                if delta.total_seconds() < 600:
                    remain = int(600 - delta.total_seconds())
                    await interaction.response.send_message(f"{COOLDOWN} You're tired of searching. Wait **{remain}s**.", ephemeral=True)
                    return
            except ValueError:
                pass
        place = random.choice(SEARCH_PLACES)
        found = random.randint(5, 50)
        async with aiosqlite.connect(self.bot.db.db_path) as db:
            await db.execute(
                "UPDATE economy SET balance = balance + ?, total_earned = total_earned + ?, last_search = ? WHERE user_id = ?",
                (found, found, now.isoformat(), uid),
            )
            await db.commit()
        await interaction.response.send_message(f"{WORK_BRIEF} You searched **{place}** and found **{found}** coins!")

    # ── Gift ──

    @app_commands.command(name="gift", description="Gift coins to another user.")
    async def gift(self, interaction: discord.Interaction, user: discord.User, amount: app_commands.Range[int, 1, 100000]) -> None:
        if user.id == interaction.user.id:
            await interaction.response.send_message("You can't gift yourself.", ephemeral=True); return
        async with aiosqlite.connect(self.bot.db.db_path) as db:
            await db.execute("BEGIN")
            cursor = await db.execute(
                "UPDATE economy SET balance = balance - ?, total_spent = total_spent + ? WHERE user_id = ? AND balance >= ?",
                (amount, amount, interaction.user.id, amount),
            )
            if cursor.rowcount == 0:
                await db.execute("ROLLBACK")
                await interaction.response.send_message("Not enough coins.", ephemeral=True); return
            await db.execute("INSERT OR IGNORE INTO economy (user_id) VALUES (?)", (user.id,))
            await db.execute(
                "UPDATE economy SET balance = balance + ?, total_earned = total_earned + ? WHERE user_id = ?",
                (amount, amount, user.id),
            )
            await db.commit()
        await interaction.response.send_message(f"{WIN} Gifted **{amount}** coins to {user.mention}!")

    # ── Shop ──

    shop = app_commands.Group(name="shop", description="Browse and buy items.")

    @shop.command(name="list", description="View items for sale.")
    async def shop_list(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Server only.", ephemeral=True)
            return
        async with aiosqlite.connect(self.bot.db.db_path) as db:
            async with db.execute(
                "SELECT id, name, description, price FROM shop_items WHERE guild_id = ?", (interaction.guild.id,)
            ) as cursor:
                items = await cursor.fetchall()
        if not items:
            await interaction.response.send_message("Shop is empty.", ephemeral=True)
            return
        lines = [f"`#{i[0]}` **{i[1]}** — {i[3]} coins\n  {i[2] or 'No description'}" for i in items]
        await interaction.response.send_message("**🛒 Server Shop**\n" + "\n".join(lines))

    @shop.command(name="buy", description="Buy an item from the shop.")
    async def shop_buy(self, interaction: discord.Interaction, item_id: int) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Server only.", ephemeral=True)
            return

        async with aiosqlite.connect(self.bot.db.db_path) as db:
            async with db.execute(
                "SELECT id, name, price, role_id FROM shop_items WHERE id = ? AND guild_id = ?",
                (item_id, interaction.guild.id),
            ) as cursor:
                item = await cursor.fetchone()
            if not item:
                await interaction.response.send_message("Item not found.", ephemeral=True)
                return

            await db.execute("BEGIN")
            cursor = await db.execute(
                "UPDATE economy SET balance = balance - ?, total_spent = total_spent + ? WHERE user_id = ? AND balance >= ?",
                (item[2], item[2], interaction.user.id, item[2]),
            )
            if cursor.rowcount == 0:
                await db.execute("ROLLBACK")
                await interaction.response.send_message(f"You need **{item[2]}** coins.", ephemeral=True)
                return
            await db.execute(
                "INSERT INTO inventory (user_id, item_id) VALUES (?, ?)", (interaction.user.id, item_id),
            )
            await db.commit()

            async with db.execute("SELECT balance FROM economy WHERE user_id = ?", (interaction.user.id,)) as cursor:
                row = await cursor.fetchone()
                new_bal = row[0] if row else 0

        msg = f"{CHECK_OK} Purchased **{item[1]}** for **{item[2]}** coins! Balance: **{new_bal}**"
        if item[3] and isinstance(interaction.user, discord.Member):
            role = interaction.guild.get_role(int(item[3]))
            if role and role < interaction.guild.me.top_role:
                try:
                    await interaction.user.add_roles(role, reason="Shop purchase")
                    msg += f"\nYou received {role.mention}!"
                except discord.Forbidden:
                    pass
        await interaction.response.send_message(msg)

    @shop.command(name="additem", description="Add an item to the shop.")
    @app_commands.checks.has_permissions(administrator=True)
    async def add_item(self, interaction: discord.Interaction, name: str, price: int,
                       description: str = "", role: discord.Role | None = None) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Server only.", ephemeral=True)
            return
        async with aiosqlite.connect(self.bot.db.db_path) as db:
            await db.execute(
                "INSERT INTO shop_items (guild_id, name, description, price, role_id) VALUES (?, ?, ?, ?, ?)",
                (interaction.guild.id, name[:100], description[:500], price, str(role.id) if role else None),
            )
            await db.commit()
        r = f" (role: {role.mention})" if role else ""
        await interaction.response.send_message(f"{CHECK_OK} Added **{name}** ({price} coins){r}.", ephemeral=True)

    @shop.command(name="removeitem", description="Remove an item from the shop.")
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_item(self, interaction: discord.Interaction, item_id: int) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Server only.", ephemeral=True)
            return
        async with aiosqlite.connect(self.bot.db.db_path) as db:
            await db.execute("DELETE FROM shop_items WHERE id = ? AND guild_id = ?", (item_id, interaction.guild.id))
            await db.commit()
        await interaction.response.send_message(f"{CHECK_OK} Removed item `#{item_id}`.", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(EconomyCog(bot))
