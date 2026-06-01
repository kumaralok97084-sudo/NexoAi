"""
Download Twemoji (Twitter Emoji) images for all bot emoji constants.
Twemoji is open-source (CC-BY 4.0) — free for any use.

Usage:  python download_emojis.py
"""

from pathlib import Path
import re
import urllib.request

TWEMOJI_CDN = "https://cdn.jsdelivr.net/gh/twitter/twemoji@latest/assets/72x72"
EMOJIS_DIR = Path("emojis")
EMOJIS_PY = Path("cogs/emojis.py")

UNICODE_ESCAPE_RE = re.compile(r"(\\U[0-9a-fA-F]{8}|\\u[0-9a-fA-F]{4})")


def unicode_escape_to_codepoint(match: str) -> str:
    raw = match.group(0)
    return f"{int(raw[2:], 16):x}"


def extract_codepoints(line: str) -> str | None:
    matches = UNICODE_ESCAPE_RE.findall(line)
    if not matches:
        return None
    codepoints = [f"{int(m[2:], 16):x}" for m in matches]
    return "-".join(codepoints)


def extract_name(line: str) -> str | None:
    m = re.match(r"^(\w+)\s*=", line)
    return m.group(1) if m else None


def main() -> None:
    EMOJIS_DIR.mkdir(exist_ok=True)
    text = EMOJIS_PY.read_text(encoding="utf-8")

    downloaded = 0
    skipped = 0
    failed = 0

    for line in text.splitlines():
        name = extract_name(line)
        if not name or name.startswith("_") or name == "POLL_EMOJIS":
            continue

        cp = extract_codepoints(line)
        if not cp:
            continue

        dest = EMOJIS_DIR / f"{name}.png"
        if dest.exists():
            skipped += 1
            continue

        url = f"{TWEMOJI_CDN}/{cp}.png"
        try:
            urllib.request.urlretrieve(url, dest)
            print(f"  OK  {name} -> {url}")
            downloaded += 1
        except Exception as e:
            print(f"  FAIL  {name} ({url}): {e}")
            failed += 1

    print(f"\nDone: {downloaded} downloaded, {skipped} skipped, {failed} failed")
    if downloaded:
        print(f"\nNow run:  python upload_emojis.py <BOT_TOKEN> <APPLICATION_ID>")


if __name__ == "__main__":
    main()
