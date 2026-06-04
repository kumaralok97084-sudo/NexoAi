"""
Upload emoji images to your Discord bot application as Application Emojis.

Application Emojis work in EVERY server the bot is in (no Nitro needed).

USAGE:
    python upload_emojis.py <BOT_TOKEN>
"""

import asyncio
import base64
import random
import sys
from pathlib import Path

import aiohttp

EMOJIS_DIR = Path("emojis")
API = "https://discord.com/api/v10"


async def rate_limited_request(
    session: aiohttp.ClientSession,
    method: str,
    url: str,
    headers: dict,
    json_body: dict | None = None,
    max_retries: int = 3,
) -> tuple[int, dict | None]:
    for attempt in range(max_retries):
        kwargs = {"headers": headers}
        if json_body is not None:
            kwargs["json"] = json_body
        async with getattr(session, method)(url, **kwargs) as resp:
            text = await resp.text()
            body = None
            ct = resp.headers.get("content-type", "")
            if "application/json" in ct or "application" in ct:
                try:
                    import json as _json
                    body = _json.loads(text) if text.strip() else None
                except Exception:
                    body = None
            if resp.status == 429 and body is not None:
                retry_after = body.get("retry_after", 1)
                jitter = random.uniform(0.5, 1.5)
                wait = retry_after * jitter
                print(f"  RATE_LIMITED, waiting {wait:.1f}s (attempt {attempt+1}/{max_retries})", file=sys.stderr)
                await asyncio.sleep(wait)
                continue
            return resp.status, body
    return resp.status, body


async def get_app_id(session: aiohttp.ClientSession, token: str) -> str:
    status, body = await rate_limited_request(
        session, "get",
        f"{API}/oauth2/applications/@me",
        {"Authorization": f"Bot {token}"},
    )
    return body["id"]


async def get_existing_emojis(
    session: aiohttp.ClientSession, token: str, app_id: str
) -> list[dict]:
    status, body = await rate_limited_request(
        session, "get",
        f"{API}/applications/{app_id}/emojis",
        {"Authorization": f"Bot {token}"},
    )
    return body.get("items", [])


async def delete_emoji(
    session: aiohttp.ClientSession, token: str, app_id: str, emoji_id: str
) -> None:
    status, body = await rate_limited_request(
        session, "delete",
        f"{API}/applications/{app_id}/emojis/{emoji_id}",
        {"Authorization": f"Bot {token}"},
    )
    if status not in (204, 200, 404):
        print(f"    DELETE FAIL {emoji_id}: {body}", file=sys.stderr)


async def upload_emoji(
    session: aiohttp.ClientSession,
    token: str,
    app_id: str,
    name: str,
    image_path: Path,
) -> dict | None:
    data = base64.b64encode(image_path.read_bytes()).decode()
    ext = "gif" if image_path.suffix.lower() == ".gif" else "png"
    payload = {"name": name, "image": f"data:image/{ext};base64,{data}"}
    status, body = await rate_limited_request(
        session, "post",
        f"{API}/applications/{app_id}/emojis",
        {"Authorization": f"Bot {token}"},
        payload,
    )
    if status == 201:
        e = body
        anim = "a" if e.get("animated") else ""
        print(f"  OK  <{anim}:{e['name']}:{e['id']}>  ({image_path.name})")
        return {"key": name, "value": f"<{anim}:{e['name']}:{e['id']}>"}
    else:
        print(f"  FAIL  {name}: {body}", file=sys.stderr)
        return None


async def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python upload_emojis.py <BOT_TOKEN>")
        sys.exit(1)

    token = sys.argv[1]
    if not EMOJIS_DIR.is_dir():
        print(f"Create an '{EMOJIS_DIR}/' folder with your emoji PNG/GIF files first.")
        sys.exit(1)

    files = sorted(EMOJIS_DIR.iterdir())
    files = [f for f in files if f.suffix.lower() in (".png", ".gif")]
    if not files:
        print(f"No PNG/GIF files found in '{EMOJIS_DIR}/'.")
        sys.exit(1)

    async with aiohttp.ClientSession() as session:
        app_id = await get_app_id(session, token)

        # Get existing emojis and delete those with matching names
        existing = await get_existing_emojis(session, token, app_id)
        wanted = {f.stem.upper()[:32] for f in files}
        to_delete = [e for e in existing if e["name"] in wanted]
        if to_delete:
            print(f"Deleting {len(to_delete)} old emojis (sequential, 0.5s apart)...")
            for i, e in enumerate(to_delete):
                await delete_emoji(session, token, app_id, e["id"])
                if i % 5 == 4:
                    await asyncio.sleep(0.5)

        # Upload sequentially with small delay
        print(f"\nUploading {len(files)} emojis to application {app_id}...\n")

        results: list[dict] = []
        for i, f in enumerate(files):
            name = f.stem.upper()[:32]
            result = await upload_emoji(session, token, app_id, name, f)
            if result:
                results.append(result)
            if i % 5 == 4:
                await asyncio.sleep(0.3)

    print(f"\nDone. {len(results)}/{len(files)} uploaded.")
    if results:
        print("\nPaste this into cogs/emojis.py:\n")
        lines = ",\n    ".join(f'    {r["key"]!r}: {r["value"]!r}' for r in results)
        print(f"_CUSTOM = {{\n    {lines},\n}}")


if __name__ == "__main__":
    asyncio.run(main())
