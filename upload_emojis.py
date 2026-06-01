"""
Upload emoji images to your Discord bot application as Application Emojis.

Application Emojis work in EVERY server the bot is in (no Nitro needed).

USAGE:
    1. Create an emojis/ folder and put your 128×128 PNG/GIF files there.
    2. Name each file to match the key in _CUSTOM (e.g. "CURRENCY.png").
    3. Run:  python upload_emojis.py <BOT_TOKEN> <APPLICATION_ID>
    4. Copy the printed _CUSTOM dict into cogs/emojis.py.
    5. Restart the bot.

REQUIREMENTS:
    pip install aiohttp
"""

import asyncio
import base64
import sys
from pathlib import Path

import aiohttp

EMOJIS_DIR = Path("emojis")
API = "https://discord.com/api/v10"


async def upload_emoji(
    session: aiohttp.ClientSession,
    token: str,
    app_id: str,
    name: str,
    image_path: Path,
) -> dict:
    data = base64.b64encode(image_path.read_bytes()).decode()
    payload = {"name": name, "image": f"data:image/{image_path.suffix[1:]};base64,{data}"}
    async with session.post(
        f"{API}/applications/{app_id}/emojis",
        headers={"Authorization": f"Bot {token}"},
        json=payload,
    ) as resp:
        body = await resp.json()
        if resp.status == 201:
            e = body
            anim = "a" if e.get("animated") else ""
            print(f"  OK  <{anim}:{e['name']}:{e['id']}>  ({image_path.name})")
            return {"key": name, "value": f"<{anim}:{e['name']}:{e['id']}>"}
        else:
            print(f"  FAIL  {name}: {body}", file=sys.stderr)
            return {}


async def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: python upload_emojis.py <BOT_TOKEN> <APPLICATION_ID>")
        sys.exit(1)

    token, app_id = sys.argv[1], sys.argv[2]
    if not EMOJIS_DIR.is_dir():
        print(f"Create an '{EMOJIS_DIR}/' folder with your emoji PNG/GIF files first.")
        sys.exit(1)

    files = sorted(EMOJIS_DIR.iterdir())
    if not files:
        print(f"No files found in '{EMOJIS_DIR}/'.")
        sys.exit(1)

    print(f"Uploading {len(files)} emojis to application {app_id}...\n")

    results: list[dict] = []
    async with aiohttp.ClientSession() as session:
        for f in files:
            if f.suffix.lower() not in (".png", ".gif", ".webp", ".jpg", ".jpeg"):
                continue
            name = f.stem.upper()[:32]
            result = await upload_emoji(session, token, app_id, name, f)
            if result:
                results.append(result)

    print(f"\nDone. {len(results)}/{len(files)} uploaded.")
    if results:
        print("\nPaste this into cogs/emojis.py:\n")
        lines = ",\n    ".join(f'    {r["key"]!r}: {r["value"]!r}' for r in results)
        print(f"_CUSTOM = {{\n    {lines},\n}}")


if __name__ == "__main__":
    asyncio.run(main())
