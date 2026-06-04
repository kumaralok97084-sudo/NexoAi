from __future__ import annotations

import asyncio
import random

import discord
from discord import app_commands
from discord.ext import commands

from cogs.emojis import CHECK_OK, COINFLIP, CROSS_NO, DICE, EIGHT_BALL, GIVEAWAY, PAPER, REMINDER, ROCK, SCISSORS, SLOT_CHERRY, SLOT_DIAMOND, SLOT_GRAPE, SLOT_LEMON, SLOT_MACHINE, SLOT_ORANGE, TARGET_GUESS, TRIVIA_GAME

RPS_CHOICES = ["rock", "paper", "scissors"]
RPS_BEATS = {"rock": "scissors", "paper": "rock", "scissors": "paper"}

EIGHT_BALL_RESPONSES = [
    "Yes.", "No.", "Definitely.", "Absolutely not.",
    "Ask again later.", "I wouldn't count on it.",
    "It is certain.", "Very doubtful.", "Without a doubt.",
    "My sources say no.", "Signs point to yes.",
    "Cannot predict now.", "Most likely.", "Outlook not so good.",
    "Yes – in time.", "Don't bet on it.",
]

SLOT_EMOJIS = [SLOT_CHERRY, SLOT_LEMON, SLOT_ORANGE, SLOT_GRAPE, SLOT_DIAMOND, "7️⃣"]
SLOT_PAYOUTS: dict[str, int] = {
    f"{SLOT_CHERRY}{SLOT_CHERRY}{SLOT_CHERRY}": 3,
    f"{SLOT_LEMON}{SLOT_LEMON}{SLOT_LEMON}": 5,
    f"{SLOT_ORANGE}{SLOT_ORANGE}{SLOT_ORANGE}": 7,
    f"{SLOT_GRAPE}{SLOT_GRAPE}{SLOT_GRAPE}": 10,
    f"{SLOT_DIAMOND}{SLOT_DIAMOND}{SLOT_DIAMOND}": 20,
    "7️⃣7️⃣7️⃣": 50,
}

TRIVIA_QUESTIONS = [
    {"q": "What planet is known as the Red Planet?", "a": "Mars", "options": ["Mars", "Venus", "Jupiter", "Saturn"]},
    {"q": "What is the largest ocean on Earth?", "a": "Pacific", "options": ["Atlantic", "Indian", "Pacific", "Arctic"]},
    {"q": "What is the chemical symbol for water?", "a": "H2O", "options": ["CO2", "H2O", "NaCl", "O2"]},
    {"q": "What year did the Titanic sink?", "a": "1912", "options": ["1905", "1912", "1920", "1898"]},
    {"q": "Who painted the Mona Lisa?", "a": "Leonardo da Vinci", "options": ["Michelangelo", "Da Vinci", "Raphael", "Van Gogh"]},
    {"q": "What is the fastest land animal?", "a": "Cheetah", "options": ["Lion", "Cheetah", "Horse", "Gazelle"]},
    {"q": "How many sides does a hexagon have?", "a": "6", "options": ["5", "6", "7", "8"]},
    {"q": "What language is primarily used for web structure?", "a": "HTML", "options": ["Python", "HTML", "CSS", "JavaScript"]},
    {"q": "Which country invented pizza?", "a": "Italy", "options": ["France", "Spain", "Italy", "Greece"]},
    {"q": "What is the smallest prime number?", "a": "2", "options": ["0", "1", "2", "3"]},
    {"q": "What does 'HTTP' stand for?", "a": "HyperText Transfer Protocol", "options": ["HyperText Transfer Protocol", "High Transfer Protocol", "HyperText Transmission", "High Tech Transfer"]},
    {"q": "Which animal is known as the King of the Jungle?", "a": "Lion", "options": ["Tiger", "Lion", "Bear", "Elephant"]},
    {"q": "How many bones are in the adult human body?", "a": "206", "options": ["106", "206", "306", "406"]},
    {"q": "What color are emeralds?", "a": "Green", "options": ["Red", "Blue", "Green", "Purple"]},
    {"q": "What is the largest continent?", "a": "Asia", "options": ["Africa", "Asia", "Europe", "America"]},
    {"q": "Which gas do plants absorb?", "a": "Carbon dioxide", "options": ["Oxygen", "Nitrogen", "Carbon dioxide", "Hydrogen"]},
    {"q": "How many legs does a spider have?", "a": "8", "options": ["6", "8", "10", "12"]},
    {"q": "What is the freezing point of water in Celsius?", "a": "0", "options": ["0", "32", "100", "-10"]},
    {"q": "Who developed Python?", "a": "Guido van Rossum", "options": ["Dennis Ritchie", "Bjarne Stroustrup", "Guido van Rossum", "James Gosling"]},
    {"q": "What planet is closest to the Sun?", "a": "Mercury", "options": ["Venus", "Mercury", "Earth", "Mars"]},
]


class GamesCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="rps", description="Play Rock Paper Scissors with the bot.")
    @app_commands.describe(choice="Choose rock, paper, or scissors")
    @app_commands.choices(choice=[
        app_commands.Choice(name=f"Rock {ROCK}", value="rock"),
        app_commands.Choice(name=f"Paper {PAPER}", value="paper"),
        app_commands.Choice(name=f"Scissors {SCISSORS}", value="scissors"),
    ])
    async def rps(self, interaction: discord.Interaction, choice: str) -> None:
        bot_choice = random.choice(RPS_CHOICES)
        if choice == bot_choice:
            result = "It's a tie!"
            color = discord.Color.greyple()
        elif RPS_BEATS[choice] == bot_choice:
            result = "You win!"
            color = discord.Color.green()
        else:
            result = "I win!"
            color = discord.Color.red()

        embed = discord.Embed(title="Rock Paper Scissors", color=color)
        embed.add_field(name="You", value=choice.capitalize(), inline=True)
        embed.add_field(name="Bot", value=bot_choice.capitalize(), inline=True)
        embed.add_field(name="Result", value=result, inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="coinflip", description="Flip a coin.")
    async def coinflip(self, interaction: discord.Interaction) -> None:
        result = random.choice(["Heads", "Tails"])
        emoji = f"{COINFLIP}"
        embed = discord.Embed(
            title=f"{emoji} Coin Flip",
            description=f"It's **{result}**!",
            color=discord.Color.gold(),
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="roll", description="Roll a dice with custom sides.")
    @app_commands.describe(sides="Number of sides (default: 6, max: 100)")
    async def roll(self, interaction: discord.Interaction, sides: app_commands.Range[int, 2, 100] = 6) -> None:
        result = random.randint(1, sides)
        embed = discord.Embed(
            title=f"{DICE} Dice Roll",
            description=f"Rolled a **{sides}**-sided dice.\nResult: **{result}**",
            color=discord.Color.blue(),
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="8ball", description="Ask the Magic 8-Ball a question.")
    @app_commands.describe(question="Your yes/no question")
    async def eight_ball(self, interaction: discord.Interaction, question: str) -> None:
        answer = random.choice(EIGHT_BALL_RESPONSES)
        embed = discord.Embed(
            title=f"{EIGHT_BALL} Magic 8-Ball",
            color=discord.Color.purple(),
        )
        embed.add_field(name="Question", value=question[:1000], inline=False)
        embed.add_field(name="Answer", value=f"**{answer}**", inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="slot", description="Play the slot machine.")
    async def slot(self, interaction: discord.Interaction) -> None:
        reels = [random.choice(SLOT_EMOJIS) for _ in range(3)]
        display = " | ".join(reels)
        key = "".join(reels)

        if key in SLOT_PAYOUTS:
            payout = SLOT_PAYOUTS[key]
            result = f"**Jackpot!** You won **{payout}x** your bet! {GIVEAWAY}"
            color = discord.Color.gold()
        elif reels[0] == reels[1] or reels[1] == reels[2]:
            result = "Two in a row! Small win! 💫"
            color = discord.Color.green()
        else:
            result = "No luck. Try again! 😅"
            color = discord.Color.red()

        embed = discord.Embed(title=f"{SLOT_MACHINE} Slot Machine", description=display, color=color)
        embed.add_field(name="Result", value=result, inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="trivia", description="Answer a random trivia question.")
    async def trivia(self, interaction: discord.Interaction) -> None:
        q = random.choice(TRIVIA_QUESTIONS)
        options = q["options"]
        random.shuffle(options)

        correct_index = options.index(q["a"])
        emojis = ["🇦", "🇧", "🇨", "🇩"]
        lines = [f"{emojis[i]} {opt}" for i, opt in enumerate(options)]
        embed = discord.Embed(
            title=f"{TRIVIA_GAME} Trivia",
            description=f"**{q['q']}**\n\n" + "\n".join(lines),
            color=discord.Color.teal(),
        )
        msg = await interaction.response.send_message(embed=embed)
        msg = await interaction.original_response()

        for emoji in emojis:
            await msg.add_reaction(emoji)

        def check(reaction: discord.Reaction, user: discord.User) -> bool:
            return (
                user == interaction.user
                and reaction.message.id == msg.id
                and str(reaction.emoji) in emojis[:len(options)]
            )

        try:
            reaction, _ = await self.bot.wait_for("reaction_add", timeout=30.0, check=check)
        except asyncio.TimeoutError:
            try:
                await msg.clear_reactions()
            except discord.Forbidden:
                pass
            await msg.reply(f"{REMINDER} Time's up! The answer was **{q['a']}**.")
            return

        chosen_index = emojis.index(str(reaction.emoji))
        if chosen_index == correct_index:
            await msg.reply(f"{CHECK_OK} **Correct!** Well done!")
        else:
            await msg.reply(f"{CROSS_NO} **Wrong!** The correct answer was **{q['a']}**.")

        try:
            await msg.clear_reactions()
        except discord.Forbidden:
            pass

    @app_commands.command(name="guess", description="Guess a number between 1 and 10.")
    async def guess(self, interaction: discord.Interaction, number: app_commands.Range[int, 1, 10]) -> None:
        target = random.randint(1, 10)
        if number == target:
            embed = discord.Embed(
                title=f"{TARGET_GUESS} Number Guess",
                description=f"The number was **{target}**. You got it! Perfect! {GIVEAWAY}",
                color=discord.Color.green(),
            )
        elif abs(number - target) <= 2:
            embed = discord.Embed(
                title=f"{TARGET_GUESS} Number Guess",
                description=f"The number was **{target}**. You guessed **{number}**. So close! 🤏",
                color=discord.Color.gold(),
            )
        else:
            embed = discord.Embed(
                title=f"{TARGET_GUESS} Number Guess",
                description=f"The number was **{target}**. You guessed **{number}**. Try again! 😅",
                color=discord.Color.red(),
            )
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(GamesCog(bot))
