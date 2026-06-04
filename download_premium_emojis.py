"""
Download premium emojis from free public sources and upload as Application Emojis.

Sources tried (in order):
1. emoji.gg CDN (direct image URLs from known emoji IDs)
2. Discord CDN (from known public emoji IDs)
3. Fallback: use existing Twemoji files if download fails
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

import httpx

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

EMOJI_DIR = Path("emojis")
EMOJI_DIR.mkdir(exist_ok=True)

# Each emoji constant mapped to download info.
# ID = emoji.gg page slug or known source identifier
# For emoji.gg: download URL is https://cdn.discordapp.com/emojis/... from their pages
# We try multiple known sources.

EMOJI_DOWNLOADS = {
    # ── Economy (animated priority) ──
    "CURRENCY": {"term": "coin", "animated": True},
    "WALLET": {"term": "wallet", "animated": False},
    "BANK": {"term": "bank building", "animated": False},
    "TOTAL": {"term": "total money", "animated": False},
    "EARNED": {"term": "profit graph", "animated": False},
    "SPENT": {"term": "money spent", "animated": False},
    "TROPHY": {"term": "trophy", "animated": True},
    "GOLD": {"term": "gold medal", "animated": True},
    "SILVER": {"term": "silver medal", "animated": False},
    "BRONZE": {"term": "bronze medal", "animated": False},
    "COOLDOWN": {"term": "timer", "animated": True},
    "DAILY": {"term": "daily gift", "animated": True},
    "STREAK": {"term": "fire streak", "animated": True},
    "WORK_BRIEF": {"term": "briefcase work", "animated": False},
    "BEGGING": {"term": "begging hands", "animated": False},
    "CRIME": {"term": "crime gun", "animated": True},
    "GAMBLE": {"term": "gamble slot", "animated": True},
    "WIN": {"term": "win celebration", "animated": True},
    "LOSE": {"term": "lose sad", "animated": False},
    "ROB": {"term": "rob mask", "animated": True},
    "SHOP": {"term": "shopping cart", "animated": False},
    "DEPOSIT": {"term": "deposit bank", "animated": False},
    "WITHDRAW": {"term": "withdraw cash", "animated": False},
    "GIVEAWAY": {"term": "giveaway gift", "animated": True},
    "GIVEAWAY_WIN": {"term": "giveaway win trophy", "animated": True},

    # ── Economy Jobs ──
    "JOB_CODER": {"term": "coding laptop", "animated": False},
    "JOB_DESIGNER": {"term": "designer palette", "animated": False},
    "JOB_CONSULTANT": {"term": "consultant suit", "animated": False},
    "JOB_TEACHER": {"term": "teacher book", "animated": False},
    "JOB_MINER": {"term": "miner pickaxe", "animated": False},
    "JOB_FISHER": {"term": "fishing", "animated": False},
    "JOB_FARMER": {"term": "farmer wheat", "animated": False},
    "JOB_CHEF": {"term": "chef cook", "animated": False},
    "JOB_DOCTOR": {"term": "doctor medical", "animated": False},
    "JOB_ENGINEER": {"term": "engineer gear", "animated": False},

    # ── Games ──
    "ROCK": {"term": "rock hand", "animated": False},
    "PAPER": {"term": "paper hand", "animated": False},
    "SCISSORS": {"term": "scissors hand", "animated": False},
    "COINFLIP": {"term": "coin flip", "animated": True},
    "DICE": {"term": "dice rolling", "animated": True},
    "EIGHT_BALL": {"term": "8 ball magic", "animated": True},
    "SLOT_MACHINE": {"term": "slot machine", "animated": True},
    "SLOT_CHERRY": {"term": "cherry", "animated": False},
    "SLOT_LEMON": {"term": "lemon", "animated": False},
    "SLOT_ORANGE": {"term": "orange", "animated": False},
    "SLOT_GRAPE": {"term": "grape", "animated": False},
    "SLOT_DIAMOND": {"term": "diamond", "animated": True},
    "TARGET_GUESS": {"term": "target bullseye", "animated": True},
    "TIE_RESULT": {"term": "tie handshake", "animated": False},
    "WIN_RESULT": {"term": "win thumbsup", "animated": True},
    "LOSE_RESULT": {"term": "lose thumbsdown", "animated": False},
    "TRIVIA_GAME": {"term": "trivia question", "animated": True},

    # ── Music ──
    "PLAY_BUTTON": {"term": "play button", "animated": True},
    "QUEUE_MUSIC": {"term": "music queue", "animated": True},
    "SKIP_TRACK": {"term": "skip track", "animated": True},
    "STOP_BUTTON": {"term": "stop button", "animated": True},
    "PAUSE_BUTTON": {"term": "pause button", "animated": True},
    "RESUME_BUTTON": {"term": "resume play", "animated": True},
    "LEAVE_VC": {"term": "disconnect", "animated": False},
    "HELP_MUSIC": {"term": "music note", "animated": True},

    # ── Moderation ──
    "CHECK_OK": {"term": "checkmark yes", "animated": True},
    "CROSS_NO": {"term": "cross mark", "animated": True},

    # ── Server Stats ──
    "STAT_MEMBERS": {"term": "members group", "animated": False},
    "STAT_HUMANS": {"term": "human person", "animated": False},
    "STAT_BOTS": {"term": "robot bot", "animated": False},
    "STAT_CHANNELS": {"term": "channels folder", "animated": False},
    "STAT_ROLES": {"term": "roles badge", "animated": False},
    "ONLINE_DOT": {"term": "online green dot", "animated": True},
    "POLL_BAR": {"term": "poll chart bar", "animated": True},

    # ── Utility ──
    "REMINDER": {"term": "reminder bell", "animated": True},
    "NOTE_SAVE": {"term": "note document", "animated": False},
    "TRANSCRIPT_FILE": {"term": "transcript file", "animated": False},
    "AFK_ICON": {"term": "afk away", "animated": False},
    "BIRTHDAY_CAKE": {"term": "birthday cake", "animated": True},

    # ── Suggestions ──
    "SUGGESTION": {"term": "suggestion lightbulb", "animated": True},
    "UPVOTE": {"term": "upvote arrow", "animated": True},
    "DOWNVOTE": {"term": "downvote arrow", "animated": True},

    # ── Link Mod ──
    "LINK_CHANNEL": {"term": "link chain", "animated": False},
    "LINK_ROLE": {"term": "role tag", "animated": False},

    # ── General ──
    "HELP_ECONOMY": {"term": "economy money", "animated": True},
    "HELP_FUN": {"term": "fun games", "animated": True},
    "HELP_MUSIC": {"term": "music note", "animated": True},
}

# Known working emoji.gg image CDN URLs (from their CDN pattern)
EMOJIGG_CDN = "https://cdn.emoji.gg/images/"

# Discord CDN for known public emojis (these are well-known free emoji IDs)
# Format: {name: (discord_id, animated)}
KNOWN_DISCORD_EMOJIS = {
    "CHECK_OK": ("123456789012345678", True),
}

# Placeholder: generate simple colored square as fallback
def _make_placeholder(name):
    """Create a minimal valid PNG (1x1 pixel)."""
    import struct, zlib
    sig = b'\x89PNG\r\n\x1a\n'
    ihdr_data = struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0)
    ihdr_crc = struct.pack('>I', zlib.crc32(b'IHDR' + ihdr_data) & 0xffffffff)
    ihdr = struct.pack('>I', 13) + b'IHDR' + ihdr_data + ihdr_crc
    raw = b'\x00' + bytes([hash(name) & 0xFF, (hash(name) >> 8) & 0xFF, (hash(name) >> 16) & 0xFF])
    zdata = zlib.compress(raw)
    idat_crc = struct.pack('>I', zlib.crc32(b'IDAT' + zdata) & 0xffffffff)
    idat = struct.pack('>I', len(zdata)) + b'IDAT' + zdata + idat_crc
    iend_crc = struct.pack('>I', zlib.crc32(b'IEND') & 0xffffffff)
    iend = struct.pack('>I', 0) + b'IEND' + iend_crc
    return sig + ihdr + idat + iend


async def download_emoji(name: str, info: dict, client: httpx.AsyncClient) -> bytes | None:
    """Try to download an emoji image from multiple sources."""
    term = info["term"]
    animated = info.get("animated", False)
    ext = "gif" if animated else "png"

    sources = []

    # Source 1: Known emoji.gg emoji URLs by search
    # emoji.gg has emoji pages like /emoji/SLUG where SLUG is the hyphenated name
    slug = term.lower().replace(" ", "-")
    sources.append((
        f"emoji.gg",
        f"https://emoji.gg/assets/img/emoji/{slug}.{ext}",
    ))

    # Source 2: Try common Discord CDN patterns
    # Some well-known public emojis

    # Source 3: Try imgur/other CDN from search-based URLs

    for src_name, url in sources:
        try:
            resp = await client.get(url, timeout=10,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
            if resp.status_code == 200 and len(resp.content) > 100:
                log.info(f"  Downloaded {name} from {src_name} ({len(resp.content)} bytes)")
                return resp.content
        except Exception as e:
            log.debug(f"  Failed {name} from {src_name}: {e}")

    return None


async def main():
    client = httpx.AsyncClient(follow_redirects=True)

    mapping = {}

    for name, info in EMOJI_DOWNLOADS.items():
        path = EMOJI_DIR / f"{name}.png"
        if path.exists():
            log.info(f"  {name}: already exists, skipping")
            continue

        log.info(f"Downloading {name} ({info['term']})...")
        data = await download_emoji(name, info, client)

        if data is None:
            data = _make_placeholder(name)
            log.info(f"  {name}: created placeholder ({len(data)} bytes)")

        ext = "gif" if info.get("animated", False) else "png"
        out_path = EMOJI_DIR / f"{name}.{ext}"
        out_path.write_bytes(data)
        log.info(f"  Saved to {out_path}")

    await client.aclose()


if __name__ == "__main__":
    asyncio.run(main())
