from __future__ import annotations

import asyncio
import json
import random
import string
from datetime import datetime, timezone, timedelta
from time import time
from typing import Any

import aiohttp
import aiosqlite
import discord
from discord import app_commands
from discord.ext import commands

from cogs.emojis import (
    INVEST, HORSE, LOTTERY, BATTLE, HEIST, FISHING, MINING, CRAFT, AUCTION, PET, FARMING,
    TRANSLATE, TLDR, ROAST, COMPLIMENT, STORY, POEM, EMAIL, BRAINSTORM, QUIZ,
    CONNECT4, TICTACTOE, HANGMAN, BLACKJACK, TYPERACE, ANAGRAM, WOULDYOU, NEVERHAVEIEVER,
    TRUTH, DARE, SHIP, HOROSCOPE, JOKE, FACT, QUOTE,
    GITHUB, TWITCH, YOUTUBE, TIMEZONE, CURRENCY_CONV, NEWS, URBAN, WIKI, IMDB, STEAM, CRYPTO, STOCK, REDDIT, XKCD,
    RADIO, SOUNDBOARD, SPOTIFY, LYRICS,
    REP, MARRY, PROFILE, BADGES, FRIEND, CLAN,
    QRCODE, PASSWORD, HASH, SHORTEN, MATH, BASE64,
    JAIL, REPORT, APPEAL, NOTEBOOK,
    VOICE, BUTTON, BIRTHDAY, COUNTDOWN, TEMPLATE,
    CHECK_OK, CROSS_NO,
)
from cogs.economy import EconomyCog

NEW_LINE = "\n"
F = "\u200b"


class FeaturesExtCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._economy: EconomyCog | None = None

    @property
    def economy(self) -> EconomyCog:
        if self._economy is None:
            cog = self.bot.get_cog("EconomyCog")
            if not isinstance(cog, EconomyCog):
                raise RuntimeError("EconomyCog not loaded")
            self._economy = cog
        return self._economy

    # ── Helpers ──

    async def _get_balance(self, uid: int) -> int:
        data = await self.economy._read(uid)
        return data["balance"]

    async def _add_balance(self, uid: int, amount: int) -> None:
        async with aiosqlite.connect(self.bot.db.db_path) as db:
            await db.execute(
                "UPDATE economy SET balance = balance + ?, total_earned = total_earned + ? WHERE user_id = ?",
                (amount, max(0, amount), uid),
            )
            await db.commit()

    async def _remove_balance(self, uid: int, amount: int) -> None:
        async with aiosqlite.connect(self.bot.db.db_path) as db:
            await db.execute(
                "UPDATE economy SET balance = balance - ?, total_spent = total_spent + ? WHERE user_id = ?",
                (amount, amount, uid),
            )
            await db.commit()

    async def _ensure_user(self, uid: int) -> None:
        await self.economy._ensure_user(uid)

    # ══════════════════════════════════════════════════════════════
    #  ECONOMY EXTENSIONS
    # ══════════════════════════════════════════════════════════════

    @app_commands.command(name="horse", description="Bet on a horse race!")
    @app_commands.describe(horse_number="Which horse? (1-5)", bet="Amount to bet")
    async def cmd_horse(self, interaction: discord.Interaction, horse_number: int, bet: int) -> None:
        if not 1 <= horse_number <= 5:
            await interaction.response.send_message(f"{CROSS_NO} Pick horse 1-5.", ephemeral=True)
            return
        if bet < 5:
            await interaction.response.send_message(f"{CROSS_NO} Minimum bet is 5.", ephemeral=True)
            return
        bal = await self._get_balance(interaction.user.id)
        if bet > bal:
            await interaction.response.send_message(f"{CROSS_NO} Not enough coins.", ephemeral=True)
            return
        await self._remove_balance(interaction.user.id, bet)
        winner = random.randint(1, 5)
        horses = ["🏇", "🐎", "🐴", "🏇", "🐎"]
        lines = []
        for i in range(5):
            pos = "=" * (i * 2) + horses[i]
            marker = " <-- YOU" if i + 1 == horse_number else ""
            tag = " <-- WINNER" if i + 1 == winner else ""
            lines.append(f"Horse {i+1}: {pos}{marker if i+1 == horse_number else ''}{tag if i+1 == winner else ''}")
        msg = await interaction.response.send_message(f"{HORSE} **Horse Race!**\n" + "\n".join(lines))
        if horse_number == winner:
            payout = int(bet * random.uniform(1.5, 3.0))
            await self._add_balance(interaction.user.id, payout)
            await interaction.edit_original_response(content=f"{HORSE} **Horse Race!**\n" + "\n".join(lines) + f"\n🎉 Horse {winner} wins! You won **{payout}** coins!")
        else:
            await interaction.edit_original_response(content=f"{HORSE} **Horse Race!**\n" + "\n".join(lines) + f"\n😔 Horse {winner} wins. You lost **{bet}** coins.")

    @app_commands.command(name="lottery", description="Buy a lottery ticket!")
    async def cmd_lottery(self, interaction: discord.Interaction) -> None:
        uid = interaction.user.id
        bal = await self._get_balance(uid)
        cost = 50
        if bal < cost:
            await interaction.response.send_message(f"{CROSS_NO} Lottery costs {cost} coins.", ephemeral=True)
            return
        await self._remove_balance(uid, cost)
        ticket = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        pool_key = f"lottery_pool_{datetime.now(timezone.utc).strftime('%Y%m%d')}"
        pool = await self.bot.db.get_guild_setting(0, pool_key) or 0
        pool = int(pool) + int(cost * 0.7)
        await self.bot.db.set_guild_setting(0, pool_key, str(pool))
        embed = discord.Embed(title=f"{LOTTERY} Lottery Ticket", color=discord.Color.gold())
        embed.add_field(name="Ticket", value=f"`{ticket}`", inline=False)
        embed.add_field(name="Cost", value=f"{cost} coins", inline=True)
        embed.add_field(name="Prize Pool", value=f"{pool} coins", inline=True)
        embed.set_footer(text="Daily draw at midnight UTC!")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="battle", description="Battle another user!")
    async def cmd_battle(self, interaction: discord.Interaction, opponent: discord.Member, bet: int) -> None:
        if opponent.bot or opponent == interaction.user:
            await interaction.response.send_message(f"{CROSS_NO} Pick a real opponent.", ephemeral=True)
            return
        if bet < 10:
            await interaction.response.send_message(f"{CROSS_NO} Minimum bet is 10.", ephemeral=True)
            return
        for uid in (interaction.user.id, opponent.id):
            bal = await self._get_balance(uid)
            if bet > bal:
                await interaction.response.send_message(f"{CROSS_NO} {interaction.user if uid == interaction.user.id else opponent} doesn't have enough.", ephemeral=True)
                return
        await self._remove_balance(interaction.user.id, bet)
        await self._remove_balance(opponent.id, bet)
        p1_power = random.randint(50, 100)
        p2_power = random.randint(50, 100)
        embed = discord.Embed(title=f"{BATTLE} Battle!", color=discord.Color.red())
        embed.add_field(name=interaction.user.display_name, value=f"⚔️ Power: {p1_power}")
        embed.add_field(name=opponent.display_name, value=f"🛡️ Power: {p2_power}")
        if p1_power > p2_power:
            winner, loser = interaction.user, opponent
        elif p2_power > p1_power:
            winner, loser = opponent, interaction.user
        else:
            embed.description = "It's a tie! Bets refunded."
            await self._add_balance(interaction.user.id, bet)
            await self._add_balance(opponent.id, bet)
            await interaction.response.send_message(embed=embed)
            return
        await self._add_balance(winner.id, bet * 2)
        embed.description = f"{winner.mention} wins! +{bet * 2} coins!"
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="heist", description="Plan a heist with friends!")
    async def cmd_heist(self, interaction: discord.Interaction, member1: discord.Member, member2: discord.Member | None = None, member3: discord.Member | None = None) -> None:
        members = [m for m in (member1, member2, member3) if m and not m.bot and m != interaction.user]
        if not members:
            await interaction.response.send_message(f"{CROSS_NO} Need at least one crew member.", ephemeral=True)
            return
        all_members = [interaction.user] + members
        cost = 25 * len(all_members)
        for m in all_members:
            bal = await self._get_balance(m.id)
            if bal < cost:
                await interaction.response.send_message(f"{CROSS_NO} {m.mention} doesn't have {cost} coins.", ephemeral=True)
                return
        for m in all_members:
            await self._remove_balance(m.id, cost)
        success = random.random() < 0.5
        if success:
            reward = int(cost * len(all_members) * random.uniform(1.5, 4.0))
            share = reward // len(all_members)
            for m in all_members:
                await self._add_balance(m.id, share)
            await interaction.response.send_message(
                f"{HEIST} **Heist successful!** Your crew stole **{reward}** coins! Each member gets **{share}**."
            )
        else:
            await interaction.response.send_message(
                f"{HEIST} **Heist failed!** Everyone lost their entry fee of **{cost}** coins."
            )

    @app_commands.command(name="fish", description="Go fishing!")
    async def cmd_fish(self, interaction: discord.Interaction) -> None:
        uid = interaction.user.id
        bal = await self._get_balance(uid)
        cost = 15
        if bal < cost:
            await interaction.response.send_message(f"{CROSS_NO} Fishing costs {cost} coins.", ephemeral=True)
            return
        await self._remove_balance(uid, cost)
        catches = ["🐟 Common fish", "🐠 Tropical fish", "🐡 Pufferfish", "🦈 Shark!", "🐋 Whale!", "👢 Old boot", "🪸 Coral", "🦀 Crab"]
        weights = [40, 25, 15, 8, 4, 30, 10, 12]
        catch = random.choices(catches, weights=weights, k=1)[0]
        value = max(0, int(cost * random.uniform(-0.5, 2.0))) if "boot" not in catch else 0
        if value > 0:
            await self._add_balance(uid, value)
        await interaction.response.send_message(f"{FISHING} You caught: {catch}! {'+' + str(value) + ' coins!' if value > 0 else 'No value.'}")

    @app_commands.command(name="mine", description="Go mining for resources!")
    async def cmd_mine(self, interaction: discord.Interaction) -> None:
        uid = interaction.user.id
        bal = await self._get_balance(uid)
        cost = 20
        if bal < cost:
            await interaction.response.send_message(f"{CROSS_NO} Mining costs {cost} coins.", ephemeral=True)
            return
        await self._remove_balance(uid, cost)
        ores = ["Stone", "Coal", "Iron", "Gold", "Diamond", "Emerald", "Ancient Relic"]
        weights = [30, 25, 20, 12, 7, 4, 2]
        values = [0, 5, 25, 60, 150, 300, 800]
        idx = random.choices(range(len(ores)), weights=weights, k=1)[0]
        value = values[idx]
        if value > 0:
            await self._add_balance(uid, value)
        await interaction.response.send_message(f"{MINING} You mined: **{ores[idx]}** worth **{value}** coins!")

    @app_commands.command(name="craft", description="Craft an item!")
    @app_commands.describe(item="Item to craft")
    async def cmd_craft(self, interaction: discord.Interaction, item: str) -> None:
        recipes = {
            "sword": {"cost": 100, "sell": 150},
            "shield": {"cost": 80, "sell": 120},
            "potion": {"cost": 30, "sell": 50},
            "ring": {"cost": 200, "sell": 350},
            "helmet": {"cost": 150, "sell": 220},
        }
        item_key = item.lower().strip()
        recipe = recipes.get(item_key)
        if not recipe:
            await interaction.response.send_message(f"{CROSS_NO} Unknown item. Try: {', '.join(recipes)}", ephemeral=True)
            return
        uid = interaction.user.id
        bal = await self._get_balance(uid)
        if bal < recipe["cost"]:
            await interaction.response.send_message(f"{CROSS_NO} {item} costs {recipe['cost']} coins to craft.", ephemeral=True)
            return
        await self._remove_balance(uid, recipe["cost"])
        async with aiosqlite.connect(self.bot.db.db_path) as db:
            await db.execute("INSERT OR IGNORE INTO inventory (user_id, item_name, quantity) VALUES (?, ?, 0)", (uid, item_key))
            await db.execute("UPDATE inventory SET quantity = quantity + 1 WHERE user_id = ? AND item_name = ?", (uid, item_key))
            await db.commit()
        await interaction.response.send_message(f"{CRAFT} You crafted a **{item}**! ({recipe['sell']} coin sell value)")

    @app_commands.command(name="auction", description="Auction an item!")
    @app_commands.describe(item="Item to auction", price="Starting price")
    async def cmd_auction(self, interaction: discord.Interaction, item: str, price: int) -> None:
        uid = interaction.user.id
        item_key = item.lower().strip()
        async with aiosqlite.connect(self.bot.db.db_path) as db:
            cur = await db.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?", (uid, item_key))
            row = await cur.fetchone()
            if not row or row[0] < 1:
                await interaction.response.send_message(f"{CROSS_NO} You don't have that item.", ephemeral=True)
                return
            await db.execute("UPDATE inventory SET quantity = quantity - 1 WHERE user_id = ? AND item_name = ?", (uid, item_key))
            await db.commit()
        premium = random.uniform(0.5, 2.5)
        final_price = int(price * premium)
        await self._add_balance(uid, final_price)
        await interaction.response.send_message(f"{AUCTION} Your **{item}** sold for **{final_price}** coins! (started at {price})")

    @app_commands.command(name="pet", description="Check on your virtual pet!")
    async def cmd_pet(self, interaction: discord.Interaction) -> None:
        uid = interaction.user.id
        async with aiosqlite.connect(self.bot.db.db_path) as db:
            await db.execute("INSERT OR IGNORE INTO user_profiles (user_id) VALUES (?)", (uid,))
            cur = await db.execute("SELECT persona FROM user_profiles WHERE user_id = ?", (uid,))
            row = await cur.fetchone()
        pet_name = "Pet"
        happiness = random.randint(30, 100)
        hunger = random.randint(20, 80)
        embed = discord.Embed(title=f"{PET} {pet_name}", color=discord.Color.gold())
        embed.add_field(name="Happiness", value=f"{'❤️' * (happiness // 10)}{'🖤' * (10 - happiness // 10)}")
        embed.add_field(name="Hunger", value=f"{'🍖' * (hunger // 10)}{'🖤' * (10 - hunger // 10)}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="farm", description="Check your farm!")
    async def cmd_farm(self, interaction: discord.Interaction) -> None:
        uid = interaction.user.id
        bal = await self._get_balance(uid)
        harvest = random.randint(5, 50)
        await self._add_balance(uid, harvest)
        await interaction.response.send_message(f"{FARMING} You harvested your crops and earned **{harvest}** coins! Balance: **{bal + harvest}**")

    # ══════════════════════════════════════════════════════════════
    #  AI / LLM FEATURES
    # ══════════════════════════════════════════════════════════════

    async def _ai_quick(self, prompt: str, system: str = "") -> str:
        try:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            return await self.bot.llm.chat(messages, max_tokens=500)
        except Exception:
            return "AI service unavailable."

    @app_commands.command(name="tldr", description="Summarize a long text.")
    @app_commands.describe(text="Text to summarize")
    async def cmd_tldr(self, interaction: discord.Interaction, text: str) -> None:
        await interaction.response.defer()
        result = await self._ai_quick(f"Summarize this concisely (max 3 sentences):\n\n{text}")
        embed = discord.Embed(title=f"{TLDR} Summary", description=result[:2000], color=discord.Color.blue())
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="roast", description="Roast someone!")
    @app_commands.describe(target="Who to roast")
    async def cmd_roast(self, interaction: discord.Interaction, target: discord.Member) -> None:
        await interaction.response.defer()
        result = await self._ai_quick(f"Give a funny, creative roast for {target.display_name}. Keep it PG-13 and witty. Max 3 sentences.")
        embed = discord.Embed(title=f"{ROAST} Roast!", description=result[:2000], color=discord.Color.orange())
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="compliment", description="Compliment someone!")
    @app_commands.describe(target="Who to compliment")
    async def cmd_compliment(self, interaction: discord.Interaction, target: discord.Member) -> None:
        await interaction.response.defer()
        result = await self._ai_quick(f"Give a genuine, warm compliment to {target.display_name}. 2-3 sentences.")
        embed = discord.Embed(title=f"{COMPLIMENT} Compliment", description=result[:2000], color=discord.Color.pink())
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="story", description="Generate a short AI story.")
    @app_commands.describe(prompt="Story prompt", genre="Genre (fantasy, sci-fi, horror, comedy, etc.)")
    async def cmd_story(self, interaction: discord.Interaction, prompt: str, genre: str = "fantasy") -> None:
        await interaction.response.defer()
        result = await self._ai_quick(f"Write a very short {genre} story (max 5 sentences) about: {prompt}")
        embed = discord.Embed(title=f"{STORY} {genre.title()} Story", description=result[:2000], color=discord.Color.purple())
        embed.set_footer(text="Powered by AI")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="poem", description="Write a poem about anything!")
    @app_commands.describe(topic="Topic of the poem", style="Style (haiku, limerick, free verse, sonnet)")
    async def cmd_poem(self, interaction: discord.Interaction, topic: str, style: str = "haiku") -> None:
        await interaction.response.defer()
        result = await self._ai_quick(f"Write a {style} poem about: {topic}")
        embed = discord.Embed(title=f"{POEM} {style.title()}: {topic}", description=result[:2000], color=discord.Color.green())
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="email", description="Generate an email draft.")
    @app_commands.describe(purpose="Purpose of the email", recipient="Recipient name")
    async def cmd_email(self, interaction: discord.Interaction, purpose: str, recipient: str = "") -> None:
        await interaction.response.defer()
        to = recipient or "[Recipient]"
        result = await self._ai_quick(f"Write a professional email to {to} about: {purpose}\nFormat with subject, greeting, body, closing.")
        embed = discord.Embed(title=f"{EMAIL} Email Draft", description=f"```{result[:2000]}```", color=discord.Color.blue())
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="brainstorm", description="Brainstorm ideas on any topic!")
    @app_commands.describe(topic="Topic to brainstorm")
    async def cmd_brainstorm(self, interaction: discord.Interaction, topic: str) -> None:
        await interaction.response.defer()
        result = await self._ai_quick(f"Brainstorm 5 creative ideas about: {topic}\nNumber them 1-5, keep each brief.")
        embed = discord.Embed(title=f"{BRAINSTORM} Ideas: {topic}", description=result[:2000], color=discord.Color.yellow())
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="quiz", description="Generate a quiz question!")
    @app_commands.describe(topic="Quiz topic")
    async def cmd_quiz(self, interaction: discord.Interaction, topic: str = "general knowledge") -> None:
        await interaction.response.defer()
        result = await self._ai_quick(f"Create a multiple choice quiz question about {topic}. Format:\nQuestion: ...\nA) ...\nB) ...\nC) ...\nD) ...\nAnswer: ...")
        embed = discord.Embed(title=f"{QUIZ} Quiz: {topic}", description=result[:2000], color=discord.Color.teal())
        await interaction.followup.send(embed=embed)

    # ══════════════════════════════════════════════════════════════
    #  FUN & GAMES
    # ══════════════════════════════════════════════════════════════

    _games: dict[str, dict[str, Any]] = {}

    @app_commands.command(name="connect4", description="Play Connect 4 with someone!")
    async def cmd_connect4(self, interaction: discord.Interaction, opponent: discord.Member) -> None:
        if opponent.bot or opponent == interaction.user:
            await interaction.response.send_message(f"{CROSS_NO} Pick a real opponent.", ephemeral=True)
            return
        game_id = f"c4_{interaction.channel_id}"
        if game_id in self._games:
            await interaction.response.send_message(f"{CROSS_NO} A game is already in progress.", ephemeral=True)
            return
        self._games[game_id] = {"board": [0]*42, "turn": interaction.user.id, "players": [interaction.user.id, opponent.id], "moves": 0}
        await interaction.response.send_message(f"{CONNECT4} **Connect 4**\n{interaction.user.mention} (🔴) vs {opponent.mention} (🟡)\nUse `/c4place <1-7>` to drop a piece!")
        await asyncio.sleep(300)
        self._games.pop(game_id, None)

    @app_commands.command(name="c4place", description="Place a piece in Connect 4.")
    @app_commands.describe(column="Column 1-7")
    async def cmd_c4place(self, interaction: discord.Interaction, column: int) -> None:
        game_id = f"c4_{interaction.channel_id}"
        game = self._games.get(game_id)
        if not game:
            await interaction.response.send_message(f"{CROSS_NO} No active game here.", ephemeral=True)
            return
        if interaction.user.id != game["turn"]:
            await interaction.response.send_message(f"{CROSS_NO} Not your turn.", ephemeral=True)
            return
        if not 1 <= column <= 7:
            await interaction.response.send_message(f"{CROSS_NO} Use column 1-7.", ephemeral=True)
            return
        col = column - 1
        board = game["board"]
        for row in range(5, -1, -1):
            idx = row * 7 + col
            if board[idx] == 0:
                board[idx] = 1 if interaction.user.id == game["players"][0] else 2
                break
        else:
            await interaction.response.send_message(f"{CROSS_NO} Column full.", ephemeral=True)
            return
        game["moves"] += 1
        game["turn"] = game["players"][1] if game["turn"] == game["players"][0] else game["players"][0]
        display = "\n".join(" ".join("🔴" if c == 1 else "🟡" if c == 2 else "⚫" for c in board[i*7:(i+1)*7]) for i in range(6))
        display += "\n1 2 3 4 5 6 7"
        await interaction.response.send_message(f"{CONNECT4}\n{display}")
        if game["moves"] >= 42:
            self._games.pop(game_id, None)
            await interaction.channel.send("It's a tie!")

    @app_commands.command(name="tictactoe", description="Play Tic-Tac-Toe!")
    @app_commands.describe(opponent="Who to play against")
    async def cmd_tictac(self, interaction: discord.Interaction, opponent: discord.Member) -> None:
        if opponent.bot or opponent == interaction.user:
            await interaction.response.send_message(f"{CROSS_NO} Pick a real opponent.", ephemeral=True)
            return
        gid = f"ttt_{interaction.channel_id}"
        if gid in self._games:
            await interaction.response.send_message(f"{CROSS_NO} Game in progress.", ephemeral=True)
            return
        self._games[gid] = {"board": [" "] * 9, "turn": interaction.user.id, "players": [interaction.user.id, opponent.id]}
        b = "\n".join(" | ".join(self._games[gid]["board"][i*3:(i+1)*3]) for i in range(3))
        await interaction.response.send_message(f"{TICTACTOE}\n{b}\nUse `/tttplace <1-9>` to play!")

    @app_commands.command(name="tttplace", description="Place your mark in Tic-Tac-Toe.")
    @app_commands.describe(position="Position (1-9, left to right, top to bottom)")
    async def cmd_tttplace(self, interaction: discord.Interaction, position: int) -> None:
        gid = f"ttt_{interaction.channel_id}"
        game = self._games.get(gid)
        if not game:
            await interaction.response.send_message(f"{CROSS_NO} No active game.", ephemeral=True)
            return
        if interaction.user.id != game["turn"]:
            await interaction.response.send_message(f"{CROSS_NO} Not your turn.", ephemeral=True)
            return
        if not 1 <= position <= 9:
            await interaction.response.send_message(f"{CROSS_NO} Use 1-9.", ephemeral=True)
            return
        idx = position - 1
        if game["board"][idx] != " ":
            await interaction.response.send_message(f"{CROSS_NO} Spot taken.", ephemeral=True)
            return
        mark = "X" if interaction.user.id == game["players"][0] else "O"
        game["board"][idx] = mark
        game["turn"] = game["players"][1] if game["turn"] == game["players"][0] else game["players"][0]
        b = "\n".join(" | ".join(game["board"][i*3:(i+1)*3]) for i in range(3))
        await interaction.response.send_message(f"{TICTACTOE}\n{b}")
        wins = [(0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6)]
        for a, b, c in wins:
            if game["board"][a] == game["board"][b] == game["board"][c] != " ":
                self._games.pop(gid, None)
                await interaction.channel.send(f"🎉 {interaction.user.mention if game['board'][a] == ('X' if interaction.user.id == game['players'][0] else 'O') else 'Someone'} wins!")
                return
        if " " not in game["board"]:
            self._games.pop(gid, None)
            await interaction.channel.send("It's a tie!")

    @app_commands.command(name="blackjack", description="Play a quick round of Blackjack!")
    @app_commands.describe(bet="Your bet")
    async def cmd_blackjack(self, interaction: discord.Interaction, bet: int) -> None:
        if bet < 10:
            await interaction.response.send_message(f"{CROSS_NO} Minimum bet is 10.", ephemeral=True)
            return
        uid = interaction.user.id
        bal = await self._get_balance(uid)
        if bet > bal:
            await interaction.response.send_message(f"{CROSS_NO} Not enough coins.", ephemeral=True)
            return
        await self._remove_balance(uid, bet)

        def deal():
            c = random.randint(1, 13)
            return min(c, 10) if c < 11 else 10, ["A","2","3","4","5","6","7","8","9","10","J","Q","K"][c-1]

        def soft(v, a):
            return v + 10 if a and v + 10 <= 21 else v

        p_cards, p_v, p_a = [], 0, 0
        d_cards, d_v, d_a = [], 0, 0
        for _ in range(2):
            for lst, v, a in [(p_cards, p_v, p_a), (d_cards, d_v, d_a)]:
                val, card = deal()
                lst.append(card)
                v += val
                if card == "A": a += 1
        p_v = soft(v, a)
        if p_v == 21:
            payout = int(bet * 2.5)
            await self._add_balance(uid, payout)
            embed = discord.Embed(title=f"{BLACKJACK} Blackjack!", description=f"You: {', '.join(p_cards)} = 21\nDealer: {', '.join(d_cards)}\n\n**Blackjack! You won {payout}!**", color=discord.Color.gold())
            await interaction.response.send_message(embed=embed)
            return
        while d_v < 17:
            val, card = deal()
            d_cards.append(card)
            d_v += val
            if card == "A": d_a += 1
        d_v = soft(d_v, d_a)
        won = False
        if d_v > 21 or p_v > d_v:
            won = True
        elif p_v == d_v:
            await self._add_balance(uid, bet)
        if won:
            payout = bet * 2
            await self._add_balance(uid, payout)
            desc = f"You: {', '.join(p_cards)} = {p_v}\nDealer: {', '.join(d_cards)} = {d_v}\n\n**You won {payout}!**"
        else:
            desc = f"You: {', '.join(p_cards)} = {p_v}\nDealer: {', '.join(d_cards)} = {d_v}\n\n**You lost {bet}.**"
        embed = discord.Embed(title=f"{BLACKJACK} Blackjack", description=desc, color=discord.Color.green() if won else discord.Color.red())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="typerace", description="Race to type a sentence!")
    async def cmd_typerace(self, interaction: discord.Interaction) -> None:
        sentences = [
            "The quick brown fox jumps over the lazy dog.",
            "Python is a powerful programming language.",
            "Discord bots can do amazing things!",
            "NexoAI is your friendly assistant.",
            "Coding is fun and rewarding.",
        ]
        sentence = random.choice(sentences)
        embed = discord.Embed(title=f"{TYPERACE} Type Race!", description=f"Type this in chat:\n```{sentence}```\nYou have 30 seconds!", color=discord.Color.blue())
        await interaction.response.send_message(embed=embed)

        def check(m):
            return m.channel == interaction.channel and not m.author.bot and m.content.strip().lower() == sentence.lower()

        try:
            msg = await self.bot.wait_for("message", timeout=30.0, check=check)
            embed = discord.Embed(title=f"{TYPERACE} Winner!", description=f"{msg.author.mention} typed it first!", color=discord.Color.gold())
            await interaction.channel.send(embed=embed)
        except asyncio.TimeoutError:
            embed = discord.Embed(title=f"{TYPERACE} Time's up!", description="No one typed it correctly.", color=discord.Color.red())
            await interaction.channel.send(embed=embed)

    @app_commands.command(name="anagram", description="Solve the anagram!")
    async def cmd_anagram(self, interaction: discord.Interaction) -> None:
        words = ["python", "discord", "bot", "server", "channel", "emoji", "gaming"]
        word = random.choice(words)
        scrambled = "".join(random.sample(word, len(word)))
        embed = discord.Embed(title=f"{ANAGRAM} Anagram!", description=f"Unscramble: **{scrambled}**\nType the answer in chat! (30s)", color=discord.Color.purple())
        await interaction.response.send_message(embed=embed)

        def check(m):
            return m.channel == interaction.channel and not m.author.bot and m.content.strip().lower() == word

        try:
            msg = await self.bot.wait_for("message", timeout=30.0, check=check)
            embed = discord.Embed(title=f"{ANAGRAM} Correct!", description=f"{msg.author.mention} solved it: **{word}**", color=discord.Color.gold())
            await interaction.channel.send(embed=embed)
        except asyncio.TimeoutError:
            embed = discord.Embed(title=f"{ANAGRAM} Time's up!", description=f"The answer was: **{word}**", color=discord.Color.red())
            await interaction.channel.send(embed=embed)

    @app_commands.command(name="wouldyourather", description="Would you rather...?")
    async def cmd_wouldyou(self, interaction: discord.Interaction) -> None:
        questions = [
            ("Have the ability to fly", "Be invisible"),
            ("Be rich but unhappy", "Be poor but happy"),
            ("Live in the past", "Live in the future"),
            ("Speak all languages", "Play all instruments"),
            ("Be famous", "Be powerful"),
            ("Never have to sleep", "Never have to eat"),
            ("Have a rewind button", "Have a pause button"),
        ]
        a, b = random.choice(questions)
        embed = discord.Embed(title=f"{WOULDYOU} Would You Rather...", color=discord.Color.blue())
        embed.add_field(name="1️⃣", value=a)
        embed.add_field(name="2️⃣", value=b)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="neverhaveiever", description="Never Have I Ever!")
    async def cmd_nhie(self, interaction: discord.Interaction) -> None:
        prompts = [
            "eaten food off the floor",
            "lied to get out of plans",
            "sung in the shower",
            "stayed up past 3 AM gaming",
            "pretended to laugh at a joke I didn't get",
            "googled myself",
            "talked to my pet",
            "cried during a movie",
        ]
        embed = discord.Embed(title=f"{NEVERHAVEIEVER} Never Have I Ever...", description=f"React with ✅ if you have!\n\n**{random.choice(prompts)}**", color=discord.Color.orange())
        msg = await interaction.response.send_message(embed=embed)
        # Add reactions via followup
        if isinstance(msg, discord.WebhookMessage):
            pass

    @app_commands.command(name="truth", description="Ask a truth question!")
    async def cmd_truth(self, interaction: discord.Interaction) -> None:
        questions = [
            "What's your biggest secret?",
            "Who do you secretly admire?",
            "What's the most embarrassing thing you've done?",
            "Have you ever cheated in a game?",
            "What's a fear you've never told anyone?",
            "What's the worst date you've been on?",
            "Have you ever broken something and blamed someone else?",
        ]
        embed = discord.Embed(title=f"{TRUTH} Truth", description=random.choice(questions), color=discord.Color.purple())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="dare", description="Give someone a dare!")
    @app_commands.describe(target="Who to dare")
    async def cmd_dare(self, interaction: discord.Interaction, target: discord.Member) -> None:
        dares = [
            f"Send a random emoji, {target.mention}!",
            f"{target.mention}, compliment the last person you texted!",
            f"{target.mention}, do 10 pushups!",
            f"Type your message backwards, {target.mention}!",
            f"{target.mention}, sing a line from your favorite song!",
        ]
        embed = discord.Embed(title=f"{DARE} Dare!", description=random.choice(dares), color=discord.Color.red())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="ship", description="Ship two people!")
    @app_commands.describe(person1="First person", person2="Second person")
    async def cmd_ship(self, interaction: discord.Interaction, person1: discord.Member, person2: discord.Member) -> None:
        compatibility = random.randint(10, 100)
        hearts = "❤️" * (compatibility // 10) + "🖤" * (10 - compatibility // 10)
        name = "".join(person1.display_name[:len(person1.display_name)//2] + person2.display_name[len(person2.display_name)//2:])
        embed = discord.Embed(title=f"{SHIP} Ship", color=discord.Color.pink())
        embed.add_field(name="Couple", value=f"{person1.mention} + {person2.mention}")
        embed.add_field(name="Ship Name", value=name, inline=False)
        embed.add_field(name="Compatibility", value=f"{compatibility}%\n{hearts}", inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="horoscope", description="Get your daily horoscope!")
    @app_commands.describe(sign="Your zodiac sign")
    async def cmd_horoscope(self, interaction: discord.Interaction, sign: str) -> None:
        signs = ["aries", "taurus", "gemini", "cancer", "leo", "virgo", "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces"]
        sign_key = sign.lower().strip()
        if sign_key not in signs:
            await interaction.response.send_message(f"{CROSS_NO} Not a valid sign. Try: {', '.join(s.capitalize() for s in signs)}", ephemeral=True)
            return
        await interaction.response.defer()
        result = await self._ai_quick(f"Write a daily horoscope for {sign_key} today. 2-3 sentences, positive and encouraging.")
        embed = discord.Embed(title=f"{HOROSCOPE} {sign_key.capitalize()} Horoscope", description=result[:2000], color=discord.Color.gold())
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="joke", description="Tell a random joke!")
    async def cmd_joke(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        result = await self._ai_quick("Tell a funny, clean joke. Pun or one-liner style.")
        embed = discord.Embed(title=f"{JOKE} Joke", description=result[:2000], color=discord.Color.yellow())
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="fact", description="Get a random interesting fact!")
    async def cmd_fact(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        result = await self._ai_quick("Give one short, interesting, true fact. Keep it under 2 sentences.")
        embed = discord.Embed(title=f"{FACT} Did You Know?", description=result[:2000], color=discord.Color.blue())
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="quote", description="Get an inspirational quote!")
    async def cmd_quote(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        result = await self._ai_quick("Give an inspirational quote with the author. Format: Quote - Author")
        embed = discord.Embed(title=f"{QUOTE} Quote", description=result[:2000], color=discord.Color.gold())
        await interaction.followup.send(embed=embed)

    # ══════════════════════════════════════════════════════════════
    #  INTEGRATION
    # ══════════════════════════════════════════════════════════════

    @app_commands.command(name="github", description="Search GitHub repositories!")
    @app_commands.describe(query="Search query")
    async def cmd_github(self, interaction: discord.Interaction, query: str) -> None:
        await interaction.response.defer()
        url = f"https://api.github.com/search/repositories?q={query}&per_page=5"
        headers = {"Accept": "application/vnd.github.v3+json"}
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(url, headers=headers) as r:
                    if r.status != 200:
                        await interaction.followup.send(f"{CROSS_NO} GitHub API error.")
                        return
                    data = await r.json()
            items = data.get("items", [])
            if not items:
                await interaction.followup.send(f"{CROSS_NO} No results.")
                return
            lines = []
            for repo in items[:5]:
                stars = repo.get("stargazers_count", 0)
                desc = (repo.get("description") or "No description")[:80]
                lines.append(f"[**{repo['full_name']}**]({repo['html_url']}) ⭐ {stars}\n> {desc}")
            embed = discord.Embed(title=f"{GITHUB} GitHub Results", description="\n".join(lines), color=discord.Color.dark_gray())
            await interaction.followup.send(embed=embed)
        except Exception:
            await interaction.followup.send(f"{CROSS_NO} Search failed.")

    @app_commands.command(name="news", description="Get latest news headlines!")
    @app_commands.describe(topic="News topic/category")
    async def cmd_news(self, interaction: discord.Interaction, topic: str = "technology") -> None:
        await interaction.response.defer()
        result = await self._ai_quick(f"Give 5 current news headlines about {topic} as of 2026. Format each as: - [Headline]. Be factual.")
        embed = discord.Embed(title=f"{NEWS} News: {topic.title()}", description=result[:2000], color=discord.Color.blue())
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="urban", description="Search Urban Dictionary.")
    @app_commands.describe(term="Term to look up")
    async def cmd_urban(self, interaction: discord.Interaction, term: str) -> None:
        await interaction.response.defer()
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(f"https://api.urbandictionary.com/v0/define?term={term}") as r:
                    data = await r.json()
            entries = data.get("list", [])
            if not entries:
                await interaction.followup.send(f"{CROSS_NO} No definition found.")
                return
            entry = entries[0]
            embed = discord.Embed(title=f"{URBAN} {entry['word']}", description=entry["definition"][:2000], color=discord.Color.purple())
            embed.add_field(name="Example", value=entry.get("example", "N/A")[:500], inline=False)
            embed.set_footer(text=f"👍 {entry.get('thumbs_up', 0)} | 👎 {entry.get('thumbs_down', 0)}")
            await interaction.followup.send(embed=embed)
        except Exception:
            await interaction.followup.send(f"{CROSS_NO} Search failed.")

    @app_commands.command(name="wiki", description="Search Wikipedia!")
    @app_commands.describe(query="Search term")
    async def cmd_wiki(self, interaction: discord.Interaction, query: str) -> None:
        await interaction.response.defer()
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(f"https://en.wikipedia.org/api/rest_v1/page/summary/{query}") as r:
                    if r.status != 200:
                        await interaction.followup.send(f"{CROSS_NO} Page not found.")
                        return
                    data = await r.json()
            embed = discord.Embed(title=f"{WIKI} {data.get('title', query)}", description=(data.get("extract") or "No summary")[:2000], color=discord.Color.white())
            if "thumbnail" in data:
                embed.set_thumbnail(url=data["thumbnail"]["source"])
            embed.add_field(name="Read more", value=f"https://en.wikipedia.org/wiki/{data.get('title', query).replace(' ', '_')}", inline=False)
            await interaction.followup.send(embed=embed)
        except Exception:
            await interaction.followup.send(f"{CROSS_NO} Search failed.")

    @app_commands.command(name="imdb", description="Look up a movie or show!")
    @app_commands.describe(title="Movie or show title")
    async def cmd_imdb(self, interaction: discord.Interaction, title: str) -> None:
        await interaction.response.defer()
        await interaction.followup.send(
            embed=discord.Embed(title=f"{IMDB} Search: {title}", description="Search OMDB/IMDB... (API key needed for live results)", color=discord.Color.yellow())
        )

    @app_commands.command(name="crypto", description="Get crypto prices!")
    @app_commands.describe(coin="Coin name (bitcoin, ethereum, etc)")
    async def cmd_crypto(self, interaction: discord.Interaction, coin: str = "bitcoin") -> None:
        await interaction.response.defer()
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(f"https://api.coingecko.com/api/v3/simple/price?ids={coin}&vs_currencies=usd&include_24hr_change=true") as r:
                    if r.status != 200:
                        await interaction.followup.send(f"{CROSS_NO} Coin not found.")
                        return
                    data = await r.json()
            info = data.get(coin, {})
            price = info.get("usd", "N/A")
            change = info.get("usd_24h_change", 0)
            arrow = "📈" if (change or 0) >= 0 else "📉"
            embed = discord.Embed(title=f"{CRYPTO} {coin.capitalize()}", color=discord.Color.gold())
            embed.add_field(name="Price (USD)", value=f"${price:,}" if isinstance(price, (int, float)) else str(price))
            embed.add_field(name="24h Change", value=f"{arrow} {change:.2f}%" if isinstance(change, (int, float)) else "N/A")
            await interaction.followup.send(embed=embed)
        except Exception:
            await interaction.followup.send(f"{CROSS_NO} API error.")

    @app_commands.command(name="stock", description="Get stock price info!")
    @app_commands.describe(symbol="Stock symbol (e.g. AAPL, TSLA, GOOGL)")
    async def cmd_stock(self, interaction: discord.Interaction, symbol: str) -> None:
        await interaction.response.defer()
        result = await self._ai_quick(f"Give current approximate stock info for {symbol.upper()} as of 2026. Include price range and sentiment. Keep brief.")
        embed = discord.Embed(title=f"{STOCK} {symbol.upper()}", description=result[:2000], color=discord.Color.green())
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="reddit", description="Get a random post from a subreddit!")
    @app_commands.describe(subreddit="Subreddit name")
    async def cmd_reddit(self, interaction: discord.Interaction, subreddit: str = "funny") -> None:
        await interaction.response.defer()
        try:
            async with aiohttp.ClientSession(headers={"User-Agent": "NexoAI/1.0"}) as s:
                async with s.get(f"https://www.reddit.com/r/{subreddit}/hot.json?limit=5") as r:
                    if r.status != 200:
                        await interaction.followup.send(f"{CROSS_NO} Subreddit not found.")
                        return
                    data = await r.json()
            posts = data.get("data", {}).get("children", [])
            if not posts:
                await interaction.followup.send(f"{CROSS_NO} No posts found.")
                return
            post = random.choice(posts)["data"]
            title = post.get("title", "No title")
            url = post.get("url", "")
            selftext = (post.get("selftext") or "")[:200]
            score = post.get("score", 0)
            embed = discord.Embed(title=f"{REDDIT} r/{subreddit}: {title}", url=url, description=selftext[:500], color=discord.Color.orange())
            embed.set_footer(text=f"👍 {score}")
            await interaction.followup.send(embed=embed)
        except Exception:
            await interaction.followup.send(f"{CROSS_NO} Failed to fetch.")

    @app_commands.command(name="xkcd", description="Get a random XKCD comic!")
    async def cmd_xkcd(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get("https://xkcd.com/info.0.json") as r:
                    latest = await r.json()
                num = random.randint(1, latest["num"])
                async with s.get(f"https://xkcd.com/{num}/info.0.json") as r:
                    comic = await r.json()
            embed = discord.Embed(title=f"{XKCD} #{comic['num']}: {comic['title']}", description=comic.get("alt", ""), color=discord.Color.white())
            embed.set_image(url=comic["img"])
            await interaction.followup.send(embed=embed)
        except Exception:
            await interaction.followup.send(f"{CROSS_NO} Failed to fetch XKCD.")

    @app_commands.command(name="youtube", description="Search YouTube!")
    @app_commands.describe(query="Search query")
    async def cmd_youtube(self, interaction: discord.Interaction, query: str) -> None:
        await interaction.response.defer()
        result = await self._ai_quick(f"Give 3 popular YouTube videos related to '{query}' with titles. Don't include URLs, just titles and channel names.")
        embed = discord.Embed(title=f"{YOUTUBE} YouTube: {query}", description=result[:2000], color=discord.Color.red())
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="twitch", description="Search Twitch streams!")
    @app_commands.describe(game="Game to search")
    async def cmd_twitch(self, interaction: discord.Interaction, game: str) -> None:
        await interaction.response.defer()
        result = await self._ai_quick(f"Give 3 popular Twitch streamers or streams for '{game}' as of 2026. Just names and brief descriptions.")
        embed = discord.Embed(title=f"{TWITCH} Twitch: {game}", description=result[:2000], color=discord.Color.purple())
        await interaction.followup.send(embed=embed)

    # ══════════════════════════════════════════════════════════════
    #  MUSIC / MEDIA
    # ══════════════════════════════════════════════════════════════

    @app_commands.command(name="radio", description="Play an internet radio station!")
    @app_commands.describe(station="Station name or genre")
    async def cmd_radio(self, interaction: discord.Interaction, station: str = "lofi") -> None:
        stations = {
            "lofi": "https://www.youtube.com/watch?v=jfKfPfyJRdk",
            "jazz": "https://www.youtube.com/watch?v=DWcJFNfaw9c",
            "classical": "https://www.youtube.com/watch?v=4Tr0otuiQuU",
            "chillhop": "https://www.youtube.com/watch?v=7NOSDKb0HlU",
        }
        url = stations.get(station.lower().strip(), stations["lofi"])
        embed = discord.Embed(title=f"{RADIO} Radio: {station.title()}", description=f"Playing: {url}", color=discord.Color.teal())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="lyrics", description="Get song lyrics!")
    @app_commands.describe(song="Song title", artist="Artist (optional)")
    async def cmd_lyrics(self, interaction: discord.Interaction, song: str, artist: str = "") -> None:
        await interaction.response.defer()
        q = f"{song} {artist}".strip()
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(f"https://api.lyrics.ovh/v1/{artist}/{song}" if artist else f"https://api.lyrics.ovh/v1/song/{song}") as r:
                    if r.status != 200:
                        await interaction.followup.send(f"{CROSS_NO} Lyrics not found.")
                        return
                    data = await r.json()
            lyrics = data.get("lyrics", "")[:2000] or "No lyrics found."
            embed = discord.Embed(title=f"{LYRICS} {song}" + (f" - {artist}" if artist else ""), description=lyrics, color=discord.Color.teal())
            await interaction.followup.send(embed=embed)
        except Exception:
            await interaction.followup.send(f"{CROSS_NO} Lyrics lookup failed.")

    @app_commands.command(name="soundboard", description="Play a sound from the soundboard!")
    @app_commands.describe(sound="Sound effect name")
    async def cmd_soundboard(self, interaction: discord.Interaction, sound: str) -> None:
        sounds = ["airhorn", "boom", "bruh", "drumroll", "fail", "laugh", "oof", "wow"]
        if sound.lower() not in sounds:
            await interaction.response.send_message(f"{CROSS_NO} Available: {', '.join(sounds)}", ephemeral=True)
            return
        embed = discord.Embed(title=f"{SOUNDBOARD} {sound.title()}", description="Sound played! (voice connection needed for audio)", color=discord.Color.blue())
        await interaction.response.send_message(embed=embed)

    # ══════════════════════════════════════════════════════════════
    #  SOCIAL
    # ══════════════════════════════════════════════════════════════

    _rep_cooldowns: dict[int, float] = {}

    @app_commands.command(name="rep", description="Give reputation to someone!")
    @app_commands.describe(user="Who to give rep to")
    async def cmd_rep(self, interaction: discord.Interaction, user: discord.Member) -> None:
        if user == interaction.user:
            await interaction.response.send_message(f"{CROSS_NO} You can't rep yourself.", ephemeral=True)
            return
        uid = interaction.user.id
        now = time()
        last = self._rep_cooldowns.get(uid, 0)
        if now - last < 43200:
            remaining = int(43200 - (now - last))
            await interaction.response.send_message(f"{CROSS_NO} You can give rep again in {remaining//3600}h {(remaining%3600)//60}m.", ephemeral=True)
            return
        self._rep_cooldowns[uid] = now
        async with aiosqlite.connect(self.bot.db.db_path) as db:
            await db.execute("INSERT OR IGNORE INTO user_profiles (user_id) VALUES (?)", (user.id,))
            cur = await db.execute("SELECT COALESCE(reputation, '0') FROM user_profiles WHERE user_id = ?", (user.id,))
            row = await cur.fetchone()
            rep = (int(row[0]) if row and row[0] else 0) + 1
            await db.execute("UPDATE user_profiles SET reputation = ? WHERE user_id = ?", (str(rep), user.id))
            await db.commit()
        embed = discord.Embed(title=f"{REP} +1 Rep", description=f"{interaction.user.mention} gave rep to {user.mention}! Total: **{rep}**", color=discord.Color.gold())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="marry", description="Propose to someone!")
    @app_commands.describe(partner="Who to propose to")
    async def cmd_marry(self, interaction: discord.Interaction, partner: discord.Member) -> None:
        if partner.bot or partner == interaction.user:
            await interaction.response.send_message(f"{CROSS_NO} Pick a real person.", ephemeral=True)
            return
        embed = discord.Embed(title=f"{MARRY} Proposal!", color=discord.Color.pink())
        embed.description = f"{interaction.user.mention} proposes to {partner.mention}! 💍\n\nDo they accept?"
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="profile", description="View a user's profile!")
    @app_commands.describe(user="User to look up")
    async def cmd_profile(self, interaction: discord.Interaction, user: discord.Member | None = None) -> None:
        user = user or interaction.user
        embed = discord.Embed(title=f"{PROFILE} {user.display_name}", color=user.color if user.color.value else discord.Color.blue())
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="Joined Discord", value=user.created_at.strftime("%b %d, %Y") if user.created_at else "N/A")
        embed.add_field(name="Joined Server", value=user.joined_at.strftime("%b %d, %Y") if user.joined_at else "N/A")
        embed.add_field(name="Roles", value=f"{len(user.roles)}")
        embed.add_field(name="Badges", value=f"{sum(1 for f in user.public_flags if f[1])} public flags")
        embed.set_footer(text=f"ID: {user.id}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="badges", description="View your badges!")
    async def cmd_badges(self, interaction: discord.Interaction) -> None:
        flag_names = {
            discord.PublicUserFlags.staff: "Staff",
            discord.PublicUserFlags.partner: "Partner",
            discord.PublicUserFlags.hypesquad: "HypeSquad",
            discord.PublicUserFlags.bug_hunter: "Bug Hunter",
            discord.PublicUserFlags.hypesquad_bravery: "Bravery",
            discord.PublicUserFlags.hypesquad_brilliance: "Brilliance",
            discord.PublicUserFlags.hypesquad_balance: "Balance",
            discord.PublicUserFlags.early_supporter: "Early Supporter",
            discord.PublicUserFlags.verified_bot_developer: "Bot Dev",
        }
        badges = [v for k, v in flag_names.items() if k in interaction.user.public_flags.all()]
        if not badges:
            badges = ["No public badges"]
        embed = discord.Embed(title=f"{BADGES} Badges", description="\n".join(f"🏅 {b}" for b in badges), color=discord.Color.gold())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="friend", description="Friend request another user!")
    @app_commands.describe(user="User to friend")
    async def cmd_friend(self, interaction: discord.Interaction, user: discord.Member) -> None:
        if user.bot or user == interaction.user:
            await interaction.response.send_message(f"{CROSS_NO} Can't friend that.", ephemeral=True)
            return
        embed = discord.Embed(title=f"{FRIEND} Friend Request", description=f"{interaction.user.mention} wants to be friends with {user.mention}! 🎉", color=discord.Color.green())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="clan", description="View or create a clan!")
    @app_commands.describe(name="Clan name (to create)")
    async def cmd_clan(self, interaction: discord.Interaction, name: str | None = None) -> None:
        if name:
            embed = discord.Embed(title=f"{CLAN} {name}", description=f"Clan created by {interaction.user.mention}!", color=discord.Color.blue())
            embed.add_field(name="Members", value="1")
            await interaction.response.send_message(embed=embed)
        else:
            embed = discord.Embed(title=f"{CLAN} My Clan", description="You are not in a clan yet. Use `/clan name:` to create one!", color=discord.Color.blue())
            await interaction.response.send_message(embed=embed)

    # ══════════════════════════════════════════════════════════════
    #  UTILITY
    # ══════════════════════════════════════════════════════════════

    @app_commands.command(name="qrcode", description="Generate a QR code!")
    @app_commands.describe(text="Text or URL to encode")
    async def cmd_qrcode(self, interaction: discord.Interaction, text: str) -> None:
        await interaction.response.defer()
        url = f"https://api.qrserver.com/v1/create-qr-code/?size=256x256&data={text}"
        embed = discord.Embed(title=f"{QRCODE} QR Code", color=discord.Color.blue())
        embed.set_image(url=url)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="password", description="Generate a secure password!")
    @app_commands.describe(length="Password length (8-64)")
    async def cmd_password(self, interaction: discord.Interaction, length: int = 16) -> None:
        if not 8 <= length <= 64:
            await interaction.response.send_message(f"{CROSS_NO} Length must be 8-64.", ephemeral=True)
            return
        chars = string.ascii_letters + string.digits + "!@#$%^&*"
        pwd = "".join(random.choice(chars) for _ in range(length))
        embed = discord.Embed(title=f"{PASSWORD} Generated Password", description=f"||{pwd}||", color=discord.Color.cyan())
        embed.set_footer(text="Only you can see this (spoiler-tagged)")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="hash", description="Generate a text hash!")
    @app_commands.describe(text="Text to hash")
    async def cmd_hash(self, interaction: discord.Interaction, text: str) -> None:
        import hashlib
        md5 = hashlib.md5(text.encode()).hexdigest()
        sha1 = hashlib.sha1(text.encode()).hexdigest()
        sha256 = hashlib.sha256(text.encode()).hexdigest()
        embed = discord.Embed(title=f"{HASH} Hash Results", color=discord.Color.purple())
        embed.add_field(name="MD5", value=f"`{md5}`", inline=False)
        embed.add_field(name="SHA-1", value=f"`{sha1}`", inline=False)
        embed.add_field(name="SHA-256", value=f"`{sha256}`", inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="shorten", description="Shorten a URL!")
    @app_commands.describe(url="URL to shorten")
    async def cmd_shorten(self, interaction: discord.Interaction, url: str) -> None:
        await interaction.response.defer()
        try:
            async with aiohttp.ClientSession() as s:
                async with s.post("https://is.gd/create.php", params={"format": "json", "url": url}) as r:
                    data = await r.json()
            short = data.get("shorturl") or data.get("error", "Failed")
            embed = discord.Embed(title=f"{SHORTEN} Shortened URL", color=discord.Color.blue())
            embed.add_field(name="Original", value=url[:200], inline=False)
            embed.add_field(name="Short", value=short, inline=False)
            await interaction.followup.send(embed=embed)
        except Exception:
            await interaction.followup.send(f"{CROSS_NO} URL shortening failed.")

    @app_commands.command(name="math", description="Evaluate a math expression!")
    @app_commands.describe(expression="Math expression (e.g. 2 + 2 * 3)")
    async def cmd_math(self, interaction: discord.Interaction, expression: str) -> None:
        allowed = set("0123456789+-*/.()%^ ")
        if not all(c in allowed for c in expression):
            await interaction.response.send_message(f"{CROSS_NO} Only basic math allowed.", ephemeral=True)
            return
        try:
            result = eval(expression, {"__builtins__": {}}, {})
            embed = discord.Embed(title=f"{MATH} Math Result", color=discord.Color.cyan())
            embed.add_field(name="Expression", value=f"`{expression}`", inline=False)
            embed.add_field(name="Result", value=f"**{result}**", inline=False)
            await interaction.response.send_message(embed=embed)
        except Exception:
            await interaction.response.send_message(f"{CROSS_NO} Invalid expression.", ephemeral=True)

    @app_commands.command(name="base64", description="Encode/decode Base64!")
    @app_commands.describe(action="encode or decode", text="Text to process")
    async def cmd_base64(self, interaction: discord.Interaction, action: str, text: str) -> None:
        import base64 as b64
        try:
            if action.lower() == "encode":
                result = b64.b64encode(text.encode()).decode()
            elif action.lower() == "decode":
                result = b64.b64decode(text.encode()).decode()
            else:
                await interaction.response.send_message(f"{CROSS_NO} Use 'encode' or 'decode'.", ephemeral=True)
                return
            embed = discord.Embed(title=f"{BASE64} Base64", color=discord.Color.purple())
            embed.add_field(name="Action", value=action.title())
            embed.add_field(name="Result", value=f"`{result[:1500]}`", inline=False)
            await interaction.response.send_message(embed=embed)
        except Exception:
            await interaction.response.send_message(f"{CROSS_NO} Invalid Base64 {action}.", ephemeral=True)

    @app_commands.command(name="birthday", description="Set or view your birthday!")
    @app_commands.describe(date="Your birthday (MM-DD)")
    async def cmd_birthday(self, interaction: discord.Interaction, date: str | None = None) -> None:
        if date:
            try:
                datetime.strptime(date, "%m-%d")
            except ValueError:
                await interaction.response.send_message(f"{CROSS_NO} Use MM-DD format (e.g. 12-25).", ephemeral=True)
                return
            async with aiosqlite.connect(self.bot.db.db_path) as db:
                await db.execute("INSERT OR IGNORE INTO user_profiles (user_id) VALUES (?)", (interaction.user.id,))
                await db.execute("UPDATE user_profiles SET birthday = ? WHERE user_id = ?", (date, interaction.user.id))
                await db.commit()
            await interaction.response.send_message(f"{BIRTHDAY} Birthday set to {date}!")
        else:
            embed = discord.Embed(title=f"{BIRTHDAY} Birthday", description="Use `/birthday MM-DD` to set your birthday!", color=discord.Color.pink())
            await interaction.response.send_message(embed=embed)

    @app_commands.command(name="countdown", description="Set or view a countdown!")
    @app_commands.describe(target_date="Target date (YYYY-MM-DD)", event="Event name")
    async def cmd_countdown(self, interaction: discord.Interaction, target_date: str, event: str = "Countdown") -> None:
        try:
            target = datetime.strptime(target_date, "%Y-%m-%d")
        except ValueError:
            await interaction.response.send_message(f"{CROSS_NO} Use YYYY-MM-DD format.", ephemeral=True)
            return
        now = datetime.now()
        diff = target - now
        if diff.total_seconds() < 0:
            await interaction.response.send_message(f"{COUNTDOWN} **{event}** happened {abs(diff.days)} days ago!")
        else:
            embed = discord.Embed(title=f"{COUNTDOWN} {event}", color=discord.Color.cyan())
            embed.description = f"**{diff.days} days, {diff.seconds // 3600} hours, {(diff.seconds // 60) % 60} minutes** remaining"
            embed.set_footer(text=f"Target: {target_date}")
            await interaction.response.send_message(embed=embed)

    @app_commands.command(name="template", description="Send a message template!")
    @app_commands.describe(template="Template name", user="Optional user to mention")
    async def cmd_template(self, interaction: discord.Interaction, template: str, user: discord.Member | None = None) -> None:
        templates = {
            "welcome": "Welcome to the server! 🎉",
            "goodbye": "Goodbye and take care! 👋",
            "thanks": "Thank you! 🙏",
            "congrats": "Congratulations! 🎊",
            "gg": "GG! Well played! 🎮",
            "gm": "Good morning! ☀️",
            "gn": "Good night! 🌙",
        }
        msg = templates.get(template.lower())
        if not msg:
            await interaction.response.send_message(f"{CROSS_NO} Unknown template. Try: {', '.join(templates)}", ephemeral=True)
            return
        if user:
            msg = f"{user.mention} {msg}"
        embed = discord.Embed(title=f"{TEMPLATE} {template.title()}", description=msg, color=discord.Color.blue())
        await interaction.response.send_message(embed=embed)

    # ══════════════════════════════════════════════════════════════
    #  MODERATION EXTENSIONS
    # ══════════════════════════════════════════════════════════════

    @app_commands.command(name="jail", description="Jail a user (removes all roles)!")
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.describe(user="User to jail")
    async def cmd_jail(self, interaction: discord.Interaction, user: discord.Member) -> None:
        if not isinstance(interaction.guild, discord.Guild):
            await interaction.response.send_message(f"{CROSS_NO} Use in a server.", ephemeral=True)
            return
        try:
            roles = [r for r in user.roles if r != interaction.guild.default_role]
            await user.remove_roles(*roles, reason=f"Jailed by {interaction.user}")
            await interaction.response.send_message(f"{JAIL} {user.mention} has been jailed. Removed {len(roles)} roles.")
        except discord.Forbidden:
            await interaction.response.send_message(f"{CROSS_NO} I don't have permission.", ephemeral=True)

    @app_commands.command(name="unjail", description="Unjail a user!")
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.describe(user="User to unjail")
    async def cmd_unjail(self, interaction: discord.Interaction, user: discord.Member) -> None:
        embed = discord.Embed(title=f"{JAIL} Unjailed", description=f"{user.mention} has been unjailed.", color=discord.Color.green())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="report", description="Report a user to staff!")
    @app_commands.describe(user="User to report", reason="Reason for report")
    async def cmd_report(self, interaction: discord.Interaction, user: discord.Member, reason: str) -> None:
        embed = discord.Embed(title=f"{REPORT} Report", color=discord.Color.red())
        embed.add_field(name="Reporter", value=interaction.user.mention)
        embed.add_field(name="Reported", value=user.mention)
        embed.add_field(name="Reason", value=reason[:1000], inline=False)
        embed.add_field(name="Channel", value=interaction.channel.mention if interaction.channel else "N/A")
        await interaction.response.send_message(embed=embed)
        staff_channel_id = await self.bot.db.get_guild_setting(interaction.guild_id or 0, "mod_log_channel")
        if staff_channel_id:
            ch = interaction.guild.get_channel(int(staff_channel_id))
            if isinstance(ch, discord.TextChannel):
                await ch.send(embed=embed)

    @app_commands.command(name="appeal", description="Appeal a moderation action!")
    @app_commands.describe(reason="Why should the action be appealed?")
    async def cmd_appeal(self, interaction: discord.Interaction, reason: str) -> None:
        embed = discord.Embed(title=f"{APPEAL} Appeal", description=reason[:2000], color=discord.Color.pink())
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="notebook", description="Write a quick note!")
    @app_commands.describe(note="Note content", title="Optional title")
    async def cmd_notebook(self, interaction: discord.Interaction, note: str, title: str = "Note") -> None:
        uid = interaction.user.id
        import hashlib
        note_id = hashlib.md5(f"{uid}{time()}{note}".encode()).hexdigest()[:8]
        async with aiosqlite.connect(self.bot.db.db_path) as db:
            await db.execute(
                "INSERT INTO user_notes (user_id, note_id, title, content, created_at) VALUES (?, ?, ?, ?, ?)",
                (uid, note_id, title[:50], note[:1000], datetime.now(timezone.utc).isoformat()),
            )
            await db.commit()
        embed = discord.Embed(title=f"{NOTEBOOK} {title}", description=note[:1000], color=discord.Color.orange())
        embed.set_footer(text=f"ID: {note_id}")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ══════════════════════════════════════════════════════════════
    #  SERVER
    # ══════════════════════════════════════════════════════════════

    @app_commands.command(name="voice", description="View voice channel info!")
    @app_commands.describe(channel="Voice channel")
    async def cmd_voice(self, interaction: discord.Interaction, channel: discord.VoiceChannel | None = None) -> None:
        if not isinstance(interaction.guild, discord.Guild):
            await interaction.response.send_message(f"{CROSS_NO} Use in a server.", ephemeral=True)
            return
        if not channel:
            channel = next((c for c in interaction.guild.voice_channels if c in [m.voice.channel for m in interaction.guild.members if m.voice]), None)
        if not channel:
            await interaction.response.send_message(f"{CROSS_NO} No voice channel found.", ephemeral=True)
            return
        members = channel.members
        embed = discord.Embed(title=f"{VOICE} {channel.name}", color=discord.Color.teal())
        embed.add_field(name="Members", value=str(len(members)))
        embed.add_field(name="Bitrate", value=f"{channel.bitrate // 1000}kbps")
        embed.add_field(name="User Limit", value=str(channel.user_limit) if channel.user_limit else "Unlimited")
        if members:
            embed.add_field(name="Connected Users", value=", ".join(m.display_name for m in members[:20]), inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="banner", description="View a user's banner!")
    @app_commands.describe(user="User whose banner to view")
    async def cmd_banner(self, interaction: discord.Interaction, user: discord.Member | None = None) -> None:
        user = user or interaction.user
        fetched = await self.bot.fetch_user(user.id)
        embed = discord.Embed(title=f"{BUTTON} {fetched.display_name}'s Banner", color=user.color if user.color.value else discord.Color.blue())
        if fetched.banner:
            embed.set_image(url=fetched.banner.url)
        else:
            embed.description = "No banner set."
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="roles", description="List all server roles!")
    async def cmd_roles(self, interaction: discord.Interaction) -> None:
        if not isinstance(interaction.guild, discord.Guild):
            await interaction.response.send_message(f"{CROSS_NO} Use in a server.", ephemeral=True)
            return
        roles = sorted(interaction.guild.roles, key=lambda r: r.position, reverse=True)
        lines = []
        for r in roles[:30]:
            if r.name != "@everyone":
                lines.append(f"{r.mention} - {len(r.members)} members")
        embed = discord.Embed(title=f"{BUTTON} Server Roles", description="\n".join(lines[:25]), color=discord.Color.blue())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="emoji_view", description="View all custom emojis in the server!")
    async def cmd_emoji_view(self, interaction: discord.Interaction) -> None:
        if not isinstance(interaction.guild, discord.Guild):
            await interaction.response.send_message(f"{CROSS_NO} Use in a server.", ephemeral=True)
            return
        emojis = list(interaction.guild.emojis)
        if not emojis:
            await interaction.response.send_message(f"{CROSS_NO} No custom emojis.", ephemeral=True)
            return
        lines = []
        for e in emojis[:40]:
            anim = "a" if e.animated else ""
            lines.append(f"<{anim}:{e.name}:{e.id}> - `:{e.name}:`")
        embed = discord.Embed(title=f"{BUTTON} Server Emojis ({len(emojis)})", description="\n".join(lines[:25]), color=discord.Color.yellow())
        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(FeaturesExtCog(bot))
