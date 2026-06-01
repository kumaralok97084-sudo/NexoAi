from __future__ import annotations

"""
PREMIUM CUSTOM EMOJI SETUP
───────────────────────────
To use Discord Application Emojis (works in every server, no Nitro needed):

1. Run:  python upload_emojis.py
   This uploads emojis from the emojis/ folder to your bot application
   and prints out the IDs.

2. Edit the _CUSTOM dict below with your real emoji IDs:
   _CUSTOM = {
       "CURRENCY": "<:nexocoin:123456789012345678>",
       "GOLD":     "<a:gold:123456789012345679>",   # animated
   }

3. Restart the bot.

When _CUSTOM is empty, all emojis fall back to Unicode.
"""

_CUSTOM: dict[str, str] = {}


def _emoji(key: str, fallback: str) -> str:
    return _CUSTOM.get(key, fallback)


# ── Economy ──
CURRENCY        = _emoji("CURRENCY", "\U0001fa99")
WALLET          = _emoji("WALLET", "\U0001f4b3")
BANK            = _emoji("BANK", "\U0001f3db\U0000fe0f")
TOTAL           = _emoji("TOTAL", "\U0001f48e")
EARNED          = _emoji("EARNED", "\U0001f4c8")
SPENT           = _emoji("SPENT", "\U0001f4c9")
TROPHY          = _emoji("TROPHY", "\U0001f3c6")
GOLD            = _emoji("GOLD", "\U0001f947")
SILVER          = _emoji("SILVER", "\U0001f948")
BRONZE          = _emoji("BRONZE", "\U0001f949")
COOLDOWN        = _emoji("COOLDOWN", "\u23f3")
DAILY           = _emoji("DAILY", "\U0001f381")
STREAK          = _emoji("STREAK", "\U0001f525")
WORK_BRIEF      = _emoji("WORK_BRIEF", "\U0001f4bc")
BEGGING         = _emoji("BEGGING", "\U0001f64f")
CRIME           = _emoji("CRIME", "\U0001f52b")
GAMBLE          = _emoji("GAMBLE", "\U0001f3b0")
WIN             = _emoji("WIN", "\U0001f389")
LOSE            = _emoji("LOSE", "\U0001f914")
ROB             = _emoji("ROB", "\U0001f9e0")
SHOP            = _emoji("SHOP", "\U0001f6cd\U0000fe0f")
DEPOSIT         = _emoji("DEPOSIT", "\U0001f3e6")
WITHDRAW        = _emoji("WITHDRAW", "\U0001f3e6")
HELP_ECONOMY    = _emoji("HELP_ECONOMY", "\U0001f4b0")
HELP_FUN        = _emoji("HELP_FUN", "\U0001f3a8")

# ── Economy Jobs ──
JOB_CODER       = _emoji("JOB_CODER", "\U0001f4bb")
JOB_DESIGNER    = _emoji("JOB_DESIGNER", "\U0001f3a8")
JOB_CONSULTANT  = _emoji("JOB_CONSULTANT", "\U0001f454")
JOB_TEACHER     = _emoji("JOB_TEACHER", "\U0001f4da")
JOB_MINER       = _emoji("JOB_MINER", "\u26cf\U0000fe0f")
JOB_FISHER      = _emoji("JOB_FISHER", "\U0001f3a3")
JOB_FARMER      = _emoji("JOB_FARMER", "\U0001f33e")
JOB_CHEF        = _emoji("JOB_CHEF", "\U0001f373")
JOB_DOCTOR      = _emoji("JOB_DOCTOR", "\U0001fa7a")
JOB_ENGINEER    = _emoji("JOB_ENGINEER", "\U0001f527")

# ── Games ──
ROCK            = _emoji("ROCK", "\U0001faa8")
PAPER           = _emoji("PAPER", "\U0001f4f0")
SCISSORS        = _emoji("SCISSORS", "\U00002702\U0000fe0f")
COINFLIP        = _emoji("COINFLIP", "\U0001fa99")
DICE            = _emoji("DICE", "\U0001f3b2")
EIGHT_BALL      = _emoji("EIGHT_BALL", "\U0001f52e")
SLOT_MACHINE    = _emoji("SLOT_MACHINE", "\U0001f3b0")
TARGET_GUESS    = _emoji("TARGET_GUESS", "\U0001f3af")
TIE_RESULT      = _emoji("TIE_RESULT", "\U0001f91d")
WIN_RESULT      = _emoji("WIN_RESULT", "\U0001f44d")
LOSE_RESULT     = _emoji("LOSE_RESULT", "\U0001f44e")
TRIVIA_GAME     = _emoji("TRIVIA_GAME", "\U00002753")

# ── Slot Reel ──
SLOT_CHERRY     = _emoji("SLOT_CHERRY", "\U0001f352")
SLOT_LEMON      = _emoji("SLOT_LEMON", "\U0001f34b")
SLOT_ORANGE     = _emoji("SLOT_ORANGE", "\U0001f34a")
SLOT_GRAPE      = _emoji("SLOT_GRAPE", "\U0001f347")
SLOT_DIAMOND    = _emoji("SLOT_DIAMOND", "\U0001f48e")

# ── Music ──
PLAY_BUTTON     = _emoji("PLAY_BUTTON", "\u25b6\U0000fe0f")
QUEUE_MUSIC     = _emoji("QUEUE_MUSIC", "\U0001f3b6")
SKIP_TRACK      = _emoji("SKIP_TRACK", "\u23ed\U0000fe0f")
STOP_BUTTON     = _emoji("STOP_BUTTON", "\u23f9\U0000fe0f")
PAUSE_BUTTON    = _emoji("PAUSE_BUTTON", "\u23f8\U0000fe0f")
RESUME_BUTTON   = _emoji("RESUME_BUTTON", "\u25b6\U0000fe0f")
LEAVE_VC        = _emoji("LEAVE_VC", "\U0001f44b")
HELP_MUSIC      = _emoji("HELP_MUSIC", "\U0001f3b5")

# ── Moderation ──
CHECK_OK        = _emoji("CHECK_OK", "\U00002705")
CROSS_NO        = _emoji("CROSS_NO", "\U0000274c")

# ── Giveaway ──
GIVEAWAY        = _emoji("GIVEAWAY", "\U0001f389")
GIVEAWAY_WIN    = _emoji("GIVEAWAY_WIN", "\U0001f3c6")

# ── Suggestions ──
SUGGESTION      = _emoji("SUGGESTION", "\U0001f4a1")
UPVOTE          = _emoji("UPVOTE", "\U0001f44d")
DOWNVOTE        = _emoji("DOWNVOTE", "\U0001f44e")

# ── Link Moderation ──
LINK_CHANNEL    = _emoji("LINK_CHANNEL", "\U0001f4fa")
LINK_ROLE       = _emoji("LINK_ROLE", "\U0001f3ad")

# ── Server Stats ──
STAT_MEMBERS    = _emoji("STAT_MEMBERS", "\U0001f465")
STAT_HUMANS     = _emoji("STAT_HUMANS", "\U0001f464")
STAT_BOTS       = _emoji("STAT_BOTS", "\U0001f916")
STAT_CHANNELS   = _emoji("STAT_CHANNELS", "\U0001f4c1")
STAT_ROLES      = _emoji("STAT_ROLES", "\U0001f3ad")
ONLINE_DOT      = _emoji("ONLINE_DOT", "\U0001f7e2")
POLL_BAR        = _emoji("POLL_BAR", "\U0001f4ca")

# ── Utility Ext ──
AFK_ICON        = _emoji("AFK_ICON", "\U0001f507")
BIRTHDAY_CAKE   = _emoji("BIRTHDAY_CAKE", "\U0001f382")

# ── Tags ──
REMINDER        = _emoji("REMINDER", "\u23f0")
NOTE_SAVE       = _emoji("NOTE_SAVE", "\U0001f4dd")
TRANSCRIPT_FILE = _emoji("TRANSCRIPT_FILE", "\U0001f4c4")
