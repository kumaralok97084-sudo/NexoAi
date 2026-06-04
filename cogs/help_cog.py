from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

# ── Category Data ─────────────────────────────────────────────────────

CATEGORIES = {
    "ai": {
        "emoji": "\U0001f916",
        "name": "AI & Memory",
        "color": 0x5865F2,
        "desc": "Chat with AI, generate images, manage memory",
        "cmds": [
            ("/ai", "Ask AI anything"),
            ("/imagine", "Generate an image from text"),
            ("/imagemodels", "List available image models"),
            ("/summarize", "Summarize text"),
            ("/translate", "Translate text"),
            ("/rewrite", "Rewrite text in a style"),
            ("/code", "Generate or fix code"),
            ("/codereview", "Get AI code review"),
            ("/debug", "Get debugging help"),
            ("/refactor", "Refactor code"),
            ("/explaincode", "Explain what code does"),
            ("/train", "Teach the bot new knowledge"),
            ("/knowledge", "List or remove knowledge"),
            ("/thread", "Create/switch conversation thread"),
            ("/forget", "Clear AI memory about a topic"),
            ("/context", "Show conversation context"),
            ("/custom", "Set custom AI instruction"),
            ("/setpersona", "Set AI persona"),
            ("/agent", "Choose AI agent preset"),
            ("/agents", "List AI agent presets"),
            ("/clearhistory", "Clear conversation history"),
            ("/mymemory", "Show what bot remembers"),
            ("/mypreferences", "Show learned preferences"),
            ("/clearmemory", "Clear all stored facts"),
            ("/usage", "Show token usage"),
            ("/tldr", "Summarize long text"),
            ("/roast", "Roast someone"),
            ("/compliment", "Compliment someone"),
            ("/story", "Generate a short story"),
            ("/poem", "Write a poem"),
            ("/email", "Generate email draft"),
            ("/brainstorm", "Brainstorm ideas"),
            ("/quiz", "Generate a quiz question"),
        ],
    },
    "economy": {
        "emoji": "\U0001f4b0",
        "name": "Economy",
        "color": 0xFEE75C,
        "desc": "Earn, spend, and manage coins",
        "cmds": [
            ("/bal", "Check balance"),
            ("/baltop", "Richest users leaderboard"),
            ("/daily", "Claim daily reward"),
            ("/weekly", "Claim weekly bonus"),
            ("/work", "Work to earn coins"),
            ("/beg", "Beg for coins"),
            ("/crime", "Commit a crime (risky)"),
            ("/gamble", "Gamble coins (50/50)"),
            ("/rob", "Rob another user"),
            ("/pay", "Send coins to another user"),
            ("/gift", "Gift coins to another user"),
            ("/deposit", "Deposit coins into bank"),
            ("/withdraw", "Withdraw coins from bank"),
            ("/search", "Search for coins"),
            ("/transactions", "View transaction history"),
            ("/inventory", "View purchased items"),
            ("/shop list", "Browse shop items"),
            ("/shop buy", "Buy a shop item"),
            ("/shop additem", "\U0001f512 Add item to shop"),
            ("/shop removeitem", "\U0001f512 Remove item from shop"),
            ("/invest", "Invest coins for returns"),
            ("/horse", "Bet on a horse race"),
            ("/lottery", "Buy a lottery ticket"),
            ("/battle", "Battle another user"),
            ("/heist", "Plan a heist with friends"),
            ("/fish", "Go fishing"),
            ("/mine", "Go mining for resources"),
            ("/craft", "Craft an item"),
            ("/auction", "Auction an item"),
            ("/pet", "Check on your virtual pet"),
            ("/farm", "Harvest your crops"),
        ],
    },
    "moderation": {
        "emoji": "\U0001f6e1\U0000fe0f",
        "name": "Moderation",
        "color": 0xED4245,
        "desc": "Keep your server safe \U0001f512 Requires moderate_members+",
        "cmds": [
            ("/purge", "Delete recent messages"),
            ("/timeout", "Timeout a member"),
            ("/untimeout", "Remove timeout"),
            ("/mute", "Timeout alias"),
            ("/unmute", "Remove timeout"),
            ("/warn", "Warn a member"),
            ("/warns", "Check member warns"),
            ("/unwarn", "Remove latest warn"),
            ("/modlogs", "View moderation logs"),
            ("/kick", "Kick a member"),
            ("/ban", "Ban a member"),
            ("/unban", "Unban a user"),
            ("/softban", "Ban + instant unban"),
            ("/tempban", "Temporarily ban a user"),
            ("/massban", "Ban multiple users at once"),
            ("/banlist", "List all banned users"),
            ("/slowmode", "Set channel slowmode"),
            ("/slowmode_reset", "Reset all channel slowmodes"),
            ("/lock", "Lock a channel"),
            ("/unlock", "Unlock a channel"),
            ("/lockdown", "Lock all channels"),
            ("/unlockall", "Unlock all channels"),
            ("/hide", "Hide a channel"),
            ("/unhide", "Unhide a channel"),
            ("/nuke", "Clone + delete a channel"),
            ("/clone", "Duplicate a channel"),
            ("/topic", "Set channel topic"),
            ("/clean", "Delete messages from a user"),
            ("/cleanup", "Delete bot messages"),
            ("/cleanup_bots", "Delete bot messages"),
            ("/cleanup_matches", "Delete matching messages"),
            ("/cleanup_attachments", "Delete messages with files"),
            ("/cleanup_links", "Delete messages with links"),
            ("/cleanup_mentions", "Delete mass-mentions"),
            ("/massdelete", "Delete user's messages"),
            ("/nick", "Change nickname"),
            ("/nickall", "Change everyone's nickname"),
            ("/voicekick", "Disconnect from voice"),
            ("/voicemove", "Move between voice channels"),
            ("/voice_muteall", "Mute all in voice"),
            ("/voice_unmuteall", "Unmute all in voice"),
            ("/voice_deafen", "Deafen a user"),
            ("/voice_undeafen", "Undeafen a user"),
            ("/voice_deafenall", "Deafen all in voice"),
            ("/voice_lock", "Lock voice channel"),
            ("/voice_limit", "Set voice user limit"),
            ("/voice_region", "Set voice region"),
            ("/filter", "Manage word filters"),
            ("/censor", "Add censor word"),
            ("/uncensor", "Remove censor word"),
            ("/censorlist", "List censored words"),
            ("/regexfilter", "Add regex filter"),
            ("/filtermode", "Set filter strictness"),
            ("/raidmode", "Toggle raid protection"),
            ("/antispam", "Toggle anti-spam"),
            ("/automod", "Toggle auto-mod rules"),
            ("/automod_spam", "Set spam threshold"),
            ("/automod_caps", "Set caps threshold"),
            ("/automod_links", "Toggle link blocking"),
            ("/automod_invites", "Toggle invite blocking"),
            ("/automod_spoilers", "Toggle spoiler blocking"),
            ("/automod_repeat", "Toggle repeat blocking"),
            ("/modsettings", "View mod settings"),
            ("/modconfig", "Configure mod settings"),
            ("/modconfig view", "View all mod config"),
            ("/messagelogs", "View message logs"),
            ("/role_add", "Add role to user"),
            ("/role_remove", "Remove role from user"),
            ("/bypass", "Add auto-mod bypass role"),
            ("/unbypass", "Remove bypass role"),
            ("/permission", "Set channel permission"),
            ("/sync_perms", "Sync channel permissions"),
            ("/channel_rename", "Rename a channel"),
            ("/category_create", "Create category"),
            ("/category_delete", "Delete category"),
            ("/thread_create", "Create a thread"),
            ("/thread_delete", "Delete a thread"),
            ("/thread_lock", "Lock a thread"),
            ("/thread_unlock", "Unlock a thread"),
            ("/archive_threads", "Archive inactive threads"),
            ("/archive_all", "Archive all threads"),
            ("/log_set", "Enable/disable log event"),
            ("/log_channel", "Set log channel"),
            ("/nsfw", "Toggle NSFW on channel"),
            ("/member_breakdown", "Server member stats"),
            ("/userhistory", "View user mod history"),
            ("/userjoins", "Check join info"),
            ("/suspicious", "Flag new accounts"),
            ("/check", "Comprehensive user check"),
            ("/sharedservers", "Find shared servers"),
            ("/emoji_add", "Upload custom emoji"),
            ("/emoji_remove", "Delete custom emoji"),
            ("/sticker_add", "Add server sticker"),
            ("/invite_list", "List server invites"),
            ("/jail", "Remove all roles"),
            ("/unjail", "Restore jailed user"),
            ("/report", "Report user to staff"),
            ("/appeal", "Appeal moderation"),
            ("/notebook", "Write a note"),
        ],
    },
    "admin": {
        "emoji": "\u2699\U0000fe0f",
        "name": "Admin",
        "color": 0x57F287,
        "desc": "Server configuration \U0001f512 Requires administrator",
        "cmds": [
            ("/setaichannel", "Set AI auto-reply channel"),
            ("/toggleautoreply", "Enable/disable AI auto-reply"),
            ("/setsupportchannel", "Set ticket support channel"),
            ("/setsystemprompt", "Set AI system prompt"),
            ("/announce", "Send an announcement"),
            ("/welcome", "Set welcome message"),
            ("/leave", "Set leave message"),
            ("/autorole", "Set auto-assign role"),
            ("/removeautorole", "Remove auto-role"),
            ("/giveaway start", "Start a giveaway"),
            ("/suggest", "Set suggestions channel"),
            ("/customcmd create", "Create custom command"),
            ("/customcmd delete", "Delete custom command"),
            ("/customcmd list", "List custom commands"),
            ("/logging", "Set logging channel"),
            ("/linkblock add", "Block a domain"),
            ("/linkblock remove", "Unblock a domain"),
            ("/linkblock list", "List blocked domains"),
            ("/linkwhitelist addchannel", "Exempt channel from link filter"),
            ("/linkwhitelist addrole", "Exempt role from link filter"),
            ("/linkwhitelist remove", "Remove link exemption"),
            ("/linkwhitelist list", "List link exemptions"),
            ("/eco give", "Give coins to a user"),
            ("/eco take", "Take coins from a user"),
            ("/eco set", "Set a user's coin balance"),
        ],
    },
    "music": {
        "emoji": "\U0001f3b5",
        "name": "Music",
        "color": 0x1DB954,
        "desc": "Play music from YouTube",
        "cmds": [
            ("/play", "Play a song from YouTube"),
            ("/skip", "Skip current song"),
            ("/queue", "Show music queue"),
            ("/stop", "Stop playback and clear queue"),
            ("/pause", "Pause current song"),
            ("/resume", "Resume paused song"),
            ("/nowplaying", "Show current song"),
            ("/volume", "Set volume (0-200%)"),
            ("/loop", "Toggle loop current song"),
            ("/loopqueue", "Toggle loop entire queue"),
            ("/shuffle", "Shuffle the queue"),
            ("/seek", "Seek to position"),
            ("/remove", "Remove song from queue"),
            ("/move", "Move song in queue"),
            ("/save", "Save song to DMs"),
            ("/join", "Join voice channel"),
            ("/disconnect", "Leave voice channel"),
            ("/playlist_create", "Create a playlist"),
            ("/playlist_add", "Add song to playlist"),
            ("/playlist_remove", "Remove song from playlist"),
            ("/playlist_view", "View a playlist"),
            ("/playlist_play", "Load playlist into queue"),
            ("/playlist_delete", "Delete a playlist"),
            ("/clear", "Clear queue without stopping"),
            ("/previous", "Go back to last played song"),
            ("/jump", "Jump to a queue position"),
            ("/ytsearch", "Search YouTube and pick a result"),
        ],
    },
    "games": {
        "emoji": "\U0001f3ae",
        "name": "Games",
        "color": 0x9B59B6,
        "desc": "Fun games to play",
        "cmds": [
            ("/rps", "Rock, Paper, Scissors"),
            ("/coinflip", "Flip a coin"),
            ("/roll", "Roll a dice"),
            ("/8ball", "Ask the Magic 8-Ball"),
            ("/slot", "Play the slot machine"),
            ("/trivia", "Answer a trivia question"),
            ("/guess", "Guess a number"),
            ("/connect4", "Play Connect 4"),
            ("/c4place", "Place in Connect 4"),
            ("/tictactoe", "Play Tic-Tac-Toe"),
            ("/tttplace", "Place in Tic-Tac-Toe"),
            ("/blackjack", "Play Blackjack"),
            ("/typerace", "Race to type a sentence"),
            ("/anagram", "Solve the anagram"),
            ("/wouldyourather", "Would you rather?"),
            ("/neverhaveiever", "Never have I ever"),
            ("/truth", "Truth question"),
            ("/dare", "Give someone a dare"),
            ("/ship", "Ship two people"),
            ("/horoscope", "Daily horoscope"),
            ("/joke", "Random joke"),
            ("/fact", "Interesting fact"),
            ("/quote", "Inspirational quote"),
        ],
    },
    "fun": {
        "emoji": "\U0001f389",
        "name": "Fun",
        "color": 0xFDCF41,
        "desc": "Random fun commands",
        "cmds": [
            ("/cat", "Random cat picture"),
            ("/dog", "Random dog picture"),
            ("/fox", "Random fox picture"),
            ("/avatar", "Show user's avatar"),
            ("/servericon", "Show server icon"),
            ("/meme", "Generate a custom meme"),
            ("/memetemplates", "List meme templates"),
        ],
    },
    "leveling": {
        "emoji": "\U0001f3c6",
        "name": "Leveling",
        "color": 0xE67E22,
        "desc": "XP and level rewards",
        "cmds": [
            ("/rank", "Show XP and level"),
            ("/levelleaderboard", "Show XP leaderboard"),
            ("/levelconfig setxprate", "\U0001f512 Set XP per message"),
            ("/levelconfig addrole", "\U0001f512 Add level role reward"),
            ("/levelconfig removerole", "\U0001f512 Remove level role"),
            ("/levelconfig listroles", "\U0001f512 List level rewards"),
        ],
    },
    "hosting": {
        "emoji": "\U0001f310",
        "name": "Hosting",
        "color": 0x3498DB,
        "desc": "Network and server tools",
        "cmds": [
            ("/pinghost", "Ping a host"),
            ("/dns", "DNS lookup"),
            ("/whois", "WHOIS lookup"),
            ("/sslcheck", "Check SSL certificate"),
            ("/portscan", "Scan common ports"),
            ("/traceroute", "Trace route to host"),
            ("/httpcheck", "Check if website is reachable"),
            ("/headers", "View HTTP headers"),
        ],
    },
    "utility": {
        "emoji": "\U0001f6e0\U0000fe0f",
        "name": "Utility",
        "color": 0x95A5A6,
        "desc": "Everyday useful commands",
        "cmds": [
            ("/poll", "Create a poll"),
            ("/rolemenu", "Set up reaction roles"),
            ("/remind", "Set a reminder"),
            ("/timer", "Start a countdown"),
            ("/note", "Save a personal note"),
            ("/notes", "List your notes"),
            ("/color", "Preview a hex color"),
            ("/define", "Look up a word"),
            ("/weather", "Get weather for a city"),
            ("/afk", "Set yourself as AFK"),
            ("/embed", "Create a custom embed"),
            ("/qrcode", "Generate a QR code"),
            ("/password", "Generate a secure password"),
            ("/hash", "Generate text hash"),
            ("/shorten", "Shorten a URL"),
            ("/math", "Evaluate math expression"),
            ("/base64", "Encode/decode Base64"),
            ("/birthday", "Set or view birthday"),
            ("/countdown", "Set a countdown timer"),
            ("/template", "Send a message template"),
        ],
    },
    "general": {
        "emoji": "\u2139\U0000fe0f",
        "name": "General",
        "color": 0x2ECC71,
        "desc": "Basic bot commands",
        "cmds": [
            ("/help", "Interactive help menu"),
            ("/helpme", "Quick command overview"),
            ("/prefix", "Show all bot prefixes"),
            ("/ping", "Check bot latency"),
            ("/uptime", "Show bot uptime"),
            ("/serverinfo", "Show server information"),
            ("/userinfo", "Show user information"),
            ("/ticket", "Create a support ticket"),
            ("/avatar", "View user's avatar"),
            ("/banner", "View user's banner"),
            ("/roles", "List server roles"),
            ("/emoji_view", "View custom emojis"),
            ("/invite", "Get bot invite link"),
        ],
    },
    "social": {
        "emoji": "\U0001f91d",
        "name": "Social",
        "color": 0xE91E63,
        "desc": "Interact with other users",
        "cmds": [
            ("/rep", "Give reputation to someone"),
            ("/marry", "Propose to someone"),
            ("/profile", "View user's profile"),
            ("/badges", "View your badges"),
            ("/friend", "Friend request someone"),
            ("/clan", "View or create a clan"),
        ],
    },
    "integration": {
        "emoji": "\U0001f517",
        "name": "Integration",
        "color": 0x00BCD4,
        "desc": "External services and APIs",
        "cmds": [
            ("/github", "Search GitHub repos"),
            ("/youtube", "Search YouTube"),
            ("/twitch", "Search Twitch streams"),
            ("/reddit", "Random subreddit post"),
            ("/news", "Latest news headlines"),
            ("/weather", "Get weather for a city"),
            ("/crypto", "Cryptocurrency prices"),
            ("/stock", "Stock price info"),
            ("/urban", "Urban Dictionary lookup"),
            ("/wiki", "Wikipedia search"),
            ("/imdb", "Movie/TV lookup"),
            ("/xkcd", "Random XKCD comic"),
        ],
    },
    "tags": {
        "emoji": "\U0001f4cb",
        "name": "Tags & Commands",
        "color": 0x1ABC9C,
        "desc": "Custom tags and server stats",
        "cmds": [
            ("/tag create", "Create a new tag"),
            ("/tag show", "Show a tag"),
            ("/tag delete", "Delete a tag"),
            ("/tag list", "List all tags"),
            ("/statschannel set", "\U0001f512 Set stats voice channel"),
            ("/statschannel remove", "\U0001f512 Remove stats channel"),
            ("/statschannel list", "List stats channels"),
        ],
    },
}

CATEGORY_KEYS = [
    "general", "ai", "economy", "moderation", "admin", "music",
    "games", "fun", "social", "integration", "leveling", "hosting", "utility", "tags",
]


class HelpSelect(discord.ui.Select):
    def __init__(self) -> None:
        options = []
        for key in CATEGORY_KEYS:
            cat = CATEGORIES[key]
            options.append(
                discord.SelectOption(
                    label=cat["name"],
                    description=cat["desc"],
                    emoji=cat["emoji"],
                    value=key,
                )
            )
        super().__init__(placeholder="Select a category...", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction) -> None:
        key = self.values[0]
        cat = CATEGORIES[key]
        embed = discord.Embed(
            title=f"{cat['emoji']} {cat['name']}",
            description=cat["desc"],
            color=cat["color"],
        )
        half = (len(cat["cmds"]) + 1) // 2
        left = cat["cmds"][:half]
        right = cat["cmds"][half:]
        left_lines = []
        right_lines = []
        for cmd, desc in left:
            left_lines.append(f"**{cmd}** — {desc}")
        for cmd, desc in right:
            right_lines.append(f"**{cmd}** — {desc}")
        embed.add_field(name="\U0000200b", value="\n".join(left_lines) if left_lines else "\U0000200b", inline=True)
        embed.add_field(name="\U0000200b", value="\n".join(right_lines) if right_lines else "\U0000200b", inline=True)
        embed.set_footer(text=f"Page: {CATEGORY_KEYS.index(key) + 1}/{len(CATEGORY_KEYS)} | \U0001f512 = Admin only")
        await interaction.response.edit_message(embed=embed, view=self.view)


class HelpView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=120)
        self.add_item(HelpSelect())


class HelpCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="help", description="Interactive help menu with category selection.")
    async def help(self, interaction: discord.Interaction) -> None:
        cat = CATEGORIES["general"]
        embed = discord.Embed(
            title=f"{cat['emoji']} {cat['name']}",
            description=cat["desc"],
            color=cat["color"],
        )
        half = (len(cat["cmds"]) + 1) // 2
        left = cat["cmds"][:half]
        right = cat["cmds"][half:]
        left_lines = []
        right_lines = []
        for cmd, desc in left:
            left_lines.append(f"**{cmd}** — {desc}")
        for cmd, desc in right:
            right_lines.append(f"**{cmd}** — {desc}")
        embed.add_field(name="\U0000200b", value="\n".join(left_lines), inline=True)
        embed.add_field(name="\U0000200b", value="\n".join(right_lines), inline=True)
        embed.set_footer(text="Select a category below | \U0001f512 = Admin only")
        await interaction.response.send_message(embed=embed, view=HelpView(), ephemeral=False)

    @app_commands.command(name="prefix", description="Show all available bot prefixes.")
    async def prefix(self, interaction: discord.Interaction) -> None:
        prefixes = self.bot.settings.bot_prefixes
        mention = f"@{self.bot.user.name}" if self.bot.user else "@NexoAI"
        lines = "\n".join(f"**`{p}`**" for p in prefixes)
        embed = discord.Embed(
            title="\u2139\ufe0f Bot Prefixes",
            description=f"Available prefixes for text commands:\n{lines}\n\nYou can also mention me: **{mention}**\n\nSlash commands use **`/`** directly.",
            color=0x2ECC71,
        )
        embed.set_footer(text=f"{len(prefixes)} text prefixes + 1 mention prefix")
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(HelpCog(bot))
