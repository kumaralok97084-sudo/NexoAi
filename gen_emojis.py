"""Generate premium NQN-style emojis with hand-drawn vector icons."""

import math
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter

EMOJI_DIR = Path("emojis")
EMOJI_DIR.mkdir(exist_ok=True)
S = 128
C = S // 2

def _font(size=32):
    for name in ["segoeuib.ttf", "segoeui.ttf", "arialbd.ttf", "arial.ttf"]:
        p = f"C:/Windows/Fonts/{name}"
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()

def _gradient_circle(draw, cx, cy, r, c1, c2):
    for i in range(r, 0, -1):
        ratio = i / r
        col = tuple(int(a + (b - a) * (1 - ratio)) for a, b in zip(c1, c2))
        draw.ellipse([cx - i, cy - i, cx + i, cy + i], fill=col + (255,))

def _glow(draw, cx, cy, r, color, steps=10):
    for i in range(steps, 0, -1):
        alpha = int(35 * (1 - i / steps))
        draw.ellipse([cx - r * i / steps, cy - r * i / steps,
                      cx + r * i / steps, cy + r * i / steps],
                     fill=(*color, alpha))

THEMES = {
    "gold":   ((255, 215, 0),   (200, 130, 0)),
    "purple": ((180, 100, 255), (90,  40, 180)),
    "blue":   ((60,  160, 255), (30,  80, 180)),
    "green":  ((50,  210, 100), (0,   130, 50)),
    "red":    ((255, 80,  80),  (180, 30,  30)),
    "teal":   ((0,   210, 210), (0,   120, 120)),
    "orange": ((255, 170, 50),  (210, 100, 0)),
    "pink":   ((255, 110, 190), (190, 50,  120)),
    "grey":   ((160, 160, 170), (90,  90,  100)),
    "cyan":   ((0,   230, 255), (0,   150, 200)),
    "dark":   ((60,  60,  80),  (25,  25,  40)),
    "lime":   ((100, 255, 50),  (50,  180, 20)),
    "coral":   ((255, 120, 80), (200, 70, 40)),
}

def bg(draw, theme):
    c1, c2 = THEMES.get(theme, THEMES["grey"])
    _glow(draw, C, C, 56, c1)
    _gradient_circle(draw, C, C, 52, c1, c2)
    draw.ellipse([C-44, C-44, C+44, C+44], outline=(255, 255, 255, 40), width=1)
    draw.ellipse([C-8, C-36, C+4, C-18], fill=(255, 255, 255, 45))

def _rr(draw, x1, y1, x2, y2, r, fill, outline=None, width=0):
    draw.rounded_rectangle([x1, y1, x2, y2], radius=r, fill=fill, outline=outline, width=width)

# ── Economy Icons ──

def coin(draw):
    _rr(draw, C-28, C-20, C+28, C+20, 18, (255, 215, 0, 230))
    draw.rounded_rectangle([C-24, C-16, C+24, C+16], radius=14, outline=(200, 160, 0, 200), width=2)
    f = _font(34); bb = draw.textbbox((0, 0), "$", font=f)
    draw.text((C-(bb[2]-bb[0])//2, C-(bb[3]-bb[1])//2-1), "$", fill=(140, 80, 0), font=f)

def wallet(draw):
    w, h = 44, 30
    x1, y1 = C-w//2, C-h//2
    _rr(draw, x1, y1, x1+w, y1+h, 6, (255, 215, 0, 230))
    _rr(draw, x1, y1-4, x1+w, y1+8, 4, (200, 170, 0, 200))
    draw.ellipse([x1+w-10, y1+6, x1+w+2, y1+18], fill=(255, 230, 50, 230))

def bank(draw):
    _rr(draw, C-32, C-14, C+32, C+24, 4, (255, 215, 0, 230))
    draw.polygon([C-34, C-14, C, C-34, C+34, C-14], fill=(200, 170, 0, 230))
    for x in [C-22, C-8, C+8, C+22]:
        draw.rectangle([x-3, C-8, x+3, C+18], fill=(180, 140, 0, 200))
    draw.rectangle([C-6, C+4, C+6, C+24], fill=(180, 140, 0, 200))

def chart_up(draw):
    _rr(draw, C-24, C-20, C+24, C+22, 4, (255, 215, 0, 230))
    draw.rectangle([C-16, C-6, C-8, C+12], fill=(180, 140, 0, 200))
    draw.rectangle([C-6, C+0, C+2, C+12], fill=(180, 140, 0, 200))
    draw.rectangle([C+4, C-12, C+12, C+12], fill=(180, 140, 0, 200))

def chart_down(draw):
    _rr(draw, C-24, C-20, C+24, C+22, 4, (255, 215, 0, 230))
    draw.rectangle([C-16, C-12, C-8, C+8], fill=(180, 140, 0, 200))
    draw.rectangle([C-6, C-6, C+2, C+8], fill=(180, 140, 0, 200))
    draw.rectangle([C+4, C+2, C+12, C+8], fill=(180, 140, 0, 200))

def trophy(draw):
    draw.polygon([C-18, C-22, C-22, C+6, C+22, C+6, C+18, C-22], fill=(255, 215, 0, 230))
    _rr(draw, C-14, C+6, C+14, C+20, 4, (200, 170, 0, 200))
    draw.arc([C-30, C-18, C-8, C+4], 90, 270, fill=(200, 170, 0, 200), width=3)
    draw.arc([C+8, C-18, C+30, C+4], -90, 90, fill=(200, 170, 0, 200), width=3)
    f = _font(20); draw.text((C-10, C-24), "\u2605", fill=(255, 230, 50), font=f)

def medal(draw, rank):
    draw.ellipse([C-24, C-28, C+24, C+20], fill=(255, 215, 0, 230))
    draw.ellipse([C-18, C-22, C+18, C+14], fill=(200, 160, 0, 200))
    draw.polygon([C-8, C-28, C+8, C-28, C+4, C-18, C-4, C-18], fill=(255, 50, 50, 200))
    f = _font(26); bb = draw.textbbox((0, 0), rank, font=f)
    draw.text((C-(bb[2]-bb[0])//2, C-(bb[3]-bb[1])//2-6), rank, fill=(255, 255, 255), font=f)

def bell(draw):
    draw.pieslice([C-22, C-28, C+22, C+18], 180, 0, fill=(255, 200, 50, 230))
    draw.ellipse([C-24, C+10, C+24, C+22], fill=(255, 200, 50, 230))
    draw.ellipse([C-6, C+14, C+6, C+26], fill=(200, 150, 30, 230))
    draw.ellipse([C-8, C-32, C+8, C-20], fill=(200, 150, 30, 230))

def gift(draw):
    _rr(draw, C-22, C-6, C+22, C+22, 4, (255, 100, 150, 230))
    draw.rectangle([C-4, C-6, C+4, C+22], fill=(255, 50, 100, 230))
    draw.rectangle([C-22, C-2, C+22, C+6], fill=(255, 50, 100, 230))
    draw.polygon([C-22, C-14, C, C-28, C+22, C-14], fill=(255, 150, 200, 230))

def flame(draw):
    f = _font(36); draw.text((C-15, C-10), "\U0001f525", fill=(255, 200, 50), font=f)

def briefcase(draw):
    _rr(draw, C-28, C-4, C+28, C+22, 6, (100, 180, 255, 230))
    _rr(draw, C-28, C-4, C+28, C+22, 6, None, (60, 140, 220, 200), 2)
    _rr(draw, C-8, C-14, C+8, C-4, 4, (100, 180, 255, 230))
    _rr(draw, C-8, C-14, C+8, C-4, 4, None, (60, 140, 220, 200), 2)

def handshake(draw):
    f = _font(30); draw.text((C-15, C-10), "\U0001f91d", fill=(255, 255, 255), font=f)

def gavel(draw):
    _rr(draw, C-20, C-18, C+20, C-6, 4, (180, 140, 80, 230))
    draw.rectangle([C-4, C-6, C+4, C+22], fill=(140, 100, 50, 230))

def crown(draw, color="gold"):
    c = THEMES[color][0][:3] if color in THEMES else (255, 215, 0)
    c2 = THEMES[color][1][:3] if color in THEMES else (200, 170, 0)
    draw.polygon([C-28, C+10, C-24, C-22, C-12, C-6, C, C-26, C+12, C-6, C+24, C-22, C+28, C+10],
                 fill=c + (230,))
    draw.rectangle([C-28, C+2, C+28, C+12], fill=c2 + (230,))
    for x in [C-20, C, C+20]:
        draw.ellipse([x-4, C-6, x+4, C+2], fill=(255, 50, 50, 230))
    for x in [C-24, C-12, C+12, C+24]:
        draw.ellipse([x-2, C-24, x+2, C-18], fill=(255, 255, 200, 230))

def dice(draw):
    _rr(draw, C-24, C-24, C+24, C+24, 8, (255, 255, 255, 230))
    _rr(draw, C-22, C-22, C+22, C+22, 6, (230, 230, 230, 200))
    for x, y in [(C-8, C-8), (C+8, C-8), (C, C), (C-8, C+8), (C+8, C+8)]:
        draw.ellipse([x-4, y-4, x+4, y+4], fill=(60, 60, 80, 230))

def slot(draw):
    _rr(draw, C-30, C-30, C+30, C+28, 8, (180, 50, 50, 230))
    for cx in [C-16, C, C+16]:
        _rr(draw, cx-10, C-22, cx+10, C+6, 4, (200, 200, 220, 230))
    syms = ["\U0001f34b", "\U0001f352", "\U0001f34a"]
    for cx, s in zip([C-16, C, C+16], syms):
        f = _font(16); bb = draw.textbbox((0, 0), s, font=f)
        draw.text((cx-(bb[2]-bb[0])//2, C-14), s, font=f)
    draw.rectangle([C+30, C-26, C+34, C-10], fill=(200, 200, 200, 230))
    draw.ellipse([C+28, C-32, C+36, C-24], fill=(255, 50, 50, 230))

def target(draw):
    draw.ellipse([C-26, C-26, C+26, C+26], outline=(255, 255, 255, 200), width=4)
    draw.ellipse([C-18, C-18, C+18, C+18], outline=(255, 255, 255, 200), width=4)
    draw.ellipse([C-10, C-10, C+10, C+10], outline=(255, 255, 255, 200), width=4)
    draw.ellipse([C-6, C-6, C+6, C+6], fill=(255, 50, 50, 230))
    for x1, y1, x2, y2 in [(C-2, C-30, C+2, C-20), (C-2, C+20, C+2, C+30),
                           (C-30, C-2, C-20, C+2), (C+20, C-2, C+30, C+2)]:
        draw.rectangle([x1, y1, x2, y2], fill=(255, 50, 50, 200))

def eight_ball(draw):
    draw.ellipse([C-24, C-28, C+24, C+28], fill=(30, 30, 40, 230))
    draw.ellipse([C-20, C-24, C+20, C+24], fill=(50, 50, 60, 230))
    f = _font(28); bb = draw.textbbox((0, 0), "8", font=f)
    draw.text((C-(bb[2]-bb[0])//2, C-(bb[3]-bb[1])//2-2), "8", fill=(255, 255, 255), font=f)
    draw.ellipse([C-12, C-16, C-2, C-6], fill=(255, 255, 255, 40))

def lightbulb(draw):
    draw.ellipse([C-18, C-20, C+18, C+12], fill=(255, 230, 50, 230))
    draw.rectangle([C-8, C+12, C+8, C+22], fill=(180, 180, 180, 230))
    for angle in [0, 45, 90, 135]:
        rad = math.radians(angle)
        x1 = C + int(22 * math.cos(rad))
        y1 = C-8 + int(22 * math.sin(rad))
        x2 = C + int(30 * math.cos(rad))
        y2 = C-8 + int(30 * math.sin(rad))
        draw.line([x1, y1, x2, y2], fill=(255, 230, 50, 150), width=2)

def shield(draw, symbol, clr):
    px = [C, C-28, C-28, C+10, C, C-10, C+28, C+28]
    py = [C-30, C-14, C+12, C+24, C+30, C+24, C+12, C-14]
    draw.polygon(list(zip(px, py)), fill=clr + (230,))
    draw.polygon(list(zip(px, py)), outline=(255, 255, 255, 60), width=2)
    f = _font(36); bb = draw.textbbox((0, 0), symbol, font=f)
    draw.text((C-(bb[2]-bb[0])//2, C-(bb[3]-bb[1])//2), symbol, fill=(255, 255, 255), font=f)

def music_note(draw):
    draw.rectangle([C+2, C-24, C+8, C+12], fill=(255, 255, 255, 230))
    draw.ellipse([C+2, C-28, C+22, C-8], fill=(255, 255, 255, 230))
    draw.ellipse([C-10, C+2, C+8, C+18], fill=(255, 255, 255, 230))

def play(draw):
    draw.polygon([C-16, C-20, C-16, C+20, C+18, C], fill=(255, 255, 255, 230))

def pause(draw):
    _rr(draw, C-16, C-20, C-4, C+20, 4, (255, 255, 255, 230))
    _rr(draw, C+4, C-20, C+16, C+20, 4, (255, 255, 255, 230))

def stop(draw):
    _rr(draw, C-16, C-20, C+16, C+20, 6, (255, 255, 255, 230))

def skip(draw):
    draw.polygon([C-18, C-20, C-18, C+20, C+2, C], fill=(255, 255, 255, 230))
    draw.polygon([C+2, C-20, C+2, C+20, C+22, C], fill=(255, 255, 255, 230))

def queue(draw):
    for i, x in enumerate([-14, -2, 10]):
        draw.rectangle([C+x, C-14, C+x+6, C+14], fill=(255, 255, 255, 200-i*30))

def wave(draw):
    f = _font(36); draw.text((C-15, C-10), "\U0001f44b", fill=(255, 255, 255), font=f)

def people(draw):
    draw.ellipse([C-24, C-28, C-2, C-8], fill=(255, 255, 255, 200))
    draw.polygon([C-26, C-6, C-24, C+10, C-14, C+10, C-12, C-2, C-16, C-10, C-26, C-6],
                 fill=(255, 255, 255, 200))
    draw.ellipse([C+2, C-22, C+24, C-2], fill=(255, 255, 255, 200))
    draw.polygon([C, C, C+2, C+16, C+12, C+16, C+14, C+4, C+10, C-4, C, C],
                 fill=(255, 255, 255, 200))

def online_dot(draw):
    _glow(draw, C, C, 30, (50, 220, 80))
    draw.ellipse([C-18, C-18, C+18, C+18], fill=(50, 220, 80, 230))
    draw.ellipse([C-10, C-10, C+10, C+10], fill=(120, 255, 150, 200))

def note(draw):
    _rr(draw, C-22, C-28, C+22, C+28, 6, (255, 200, 50, 230))
    for y in range(C-14, C+22, 8):
        draw.rectangle([C-14, y, C+14, y+2], fill=(200, 150, 30, 200))

def cake(draw):
    _rr(draw, C-28, C-2, C+28, C+26, 4, (255, 180, 200, 230))
    _rr(draw, C-20, C-14, C+20, C-2, 4, (255, 200, 220, 230))
    _rr(draw, C-14, C-24, C+14, C-14, 4, (255, 220, 240, 230))
    draw.rectangle([C-3, C-38, C+3, C-24], fill=(255, 100, 100, 230))
    draw.ellipse([C-5, C-44, C+5, C-34], fill=(255, 200, 50, 230))
    draw.ellipse([C-3, C-42, C+3, C-36], fill=(255, 255, 200, 230))

# ── New Feature Icons ──

def _chart_bar(draw):
    _rr(draw, C-24, C-20, C+24, C+22, 4, (255, 215, 0, 230))
    for i, (x, h) in enumerate([(-14, -14), (-6, -8), (2, -18), (10, -4)]):
        draw.rectangle([C+x, C+h, C+x+4, C+12], fill=(180, 140, 0, 200))

def _horse(draw):
    f = _font(30); draw.text((C-15, C-10), "\U0001f40e", fill=(255, 200, 100), font=f)

def _ticket_lottery(draw):
    _rr(draw, C-24, C-18, C+24, C+20, 6, (255, 100, 150, 230))
    draw.text((C-12, C-10), "LOT", fill=(255, 255, 255), font=_font(22))

def _swords(draw):
    f = _font(30); draw.text((C-15, C-10), "\u2694", fill=(255, 200, 50), font=f)

def _mask_heist(draw):
    f = _font(30); draw.text((C-15, C-10), "\U0001f9e0", fill=(200, 200, 200), font=f)

def _fish_hook(draw):
    f = _font(30); draw.text((C-15, C-10), "\U0001f3a3", fill=(100, 200, 200), font=f)

def _pick(draw):
    f = _font(30); draw.text((C-15, C-10), "\u26cf", fill=(200, 180, 100), font=f)

def _craft(draw):
    f = _font(24); draw.text((C-18, C-10), "\U0001f528", fill=(200, 200, 200), font=f)

def _gavel_auction(draw):
    _rr(draw, C-16, C-18, C+16, C-6, 4, (180, 140, 80, 230))
    draw.rectangle([C-3, C-6, C+3, C+20], fill=(140, 100, 50, 230))

def _paw(draw):
    f = _font(30); draw.text((C-15, C-10), "\U0001f43e", fill=(255, 200, 150), font=f)

def _seedling(draw):
    f = _font(30); draw.text((C-15, C-10), "\U0001f331", fill=(100, 220, 100), font=f)

def _translate_icon(draw):
    f = _font(24); draw.text((C-20, C-10), "A\u2192\u0410", fill=(100, 200, 255), font=f)

def _eye(draw):
    f = _font(30); draw.text((C-15, C-10), "\U0001f441", fill=(200, 200, 255), font=f)

def _fire_roast(draw):
    f = _font(30); draw.text((C-15, C-10), "\U0001f525", fill=(255, 150, 50), font=f)

def _heart(draw):
    f = _font(30); draw.text((C-15, C-10), "\u2764", fill=(255, 80, 80), font=f)

def _book(draw):
    _rr(draw, C-18, C-24, C+18, C+24, 4, (200, 150, 100, 230))
    draw.rectangle([C-14, C-18, C+14, C+20], fill=(240, 200, 140, 230))
    for y in range(C-10, C+16, 7):
        draw.line([C-10, y, C+10, y], fill=(180, 130, 60, 180), width=1)

def _pen(draw):
    f = _font(30); draw.text((C-15, C-10), "\U0001f4dd", fill=(255, 200, 50), font=f)

def _code_icon(draw):
    f = _font(24); draw.text((C-20, C-10), "</>", fill=(100, 200, 255), font=f)

def _search_icon(draw):
    f = _font(30); draw.text((C-15, C-10), "\U0001f50d", fill=(200, 200, 200), font=f)

def _ship_icon(draw):
    f = _font(30); draw.text((C-15, C-10), "\U0001f48d", fill=(255, 100, 150), font=f)

def _crystal(draw):
    f = _font(30); draw.text((C-15, C-10), "\U0001f52e", fill=(180, 100, 255), font=f)

def _muscle(draw):
    f = _font(30); draw.text((C-15, C-10), "\U0001f4aa", fill=(255, 200, 100), font=f)

def _thinking(draw):
    f = _font(30); draw.text((C-15, C-10), "\U0001f914", fill=(200, 200, 200), font=f)

def _clap(draw):
    f = _font(30); draw.text((C-15, C-10), "\U0001f44f", fill=(255, 200, 100), font=f)

def _laugh(draw):
    f = _font(30); draw.text((C-15, C-10), "\U0001f604", fill=(255, 255, 100), font=f)

def _cry_laugh(draw):
    f = _font(30); draw.text((C-15, C-10), "\U0001f602", fill=(255, 255, 100), font=f)

def _sunglasses(draw):
    f = _font(30); draw.text((C-15, C-10), "\U0001f60e", fill=(200, 200, 200), font=f)

def _party(draw):
    f = _font(30); draw.text((C-15, C-10), "\U0001f389", fill=(255, 200, 50), font=f)

def _crossed_swords(draw):
    f = _font(30); draw.text((C-15, C-10), "\u2694", fill=(200, 200, 200), font=f)

def _skull(draw):
    f = _font(30); draw.text((C-15, C-10), "\U0001f480", fill=(200, 200, 200), font=f)

def _flag(draw):
    f = _font(30); draw.text((C-15, C-10), "\U0001f3c1", fill=(255, 50, 50), font=f)

def _tada(draw):
    f = _font(30); draw.text((C-15, C-10), "\U0001f38a", fill=(255, 200, 50), font=f)

def _microphone(draw):
    f = _font(30); draw.text((C-15, C-10), "\U0001f3a4", fill=(200, 200, 200), font=f)

def _headphone(draw):
    f = _font(30); draw.text((C-15, C-10), "\U0001f3a7", fill=(100, 200, 255), font=f)

def _radio(draw):
    f = _font(24); draw.text((C-20, C-10), "\U0001f4fb", fill=(100, 200, 255), font=f)

def _soundboard(draw):
    f = _font(24); draw.text((C-20, C-10), "\U0001f399", fill=(200, 150, 100), font=f)

def _github(draw):
    f = _font(24); draw.text((C-20, C-10), "\U0001f5a5", fill=(200, 200, 200), font=f)

def _twitch(draw):
    f = _font(24); draw.text((C-20, C-10), "\U0001f3ae", fill=(180, 100, 255), font=f)

def _youtube_icon(draw):
    f = _font(24); draw.text((C-20, C-10), "\U0001f4f9", fill=(255, 50, 50), font=f)

def _globe(draw):
    f = _font(30); draw.text((C-15, C-10), "\U0001f30d", fill=(100, 200, 255), font=f)

def _money_exchange(draw):
    f = _font(24); draw.text((C-20, C-10), "\U0001f4b1", fill=(100, 255, 100), font=f)

def _newspaper(draw):
    f = _font(24); draw.text((C-20, C-10), "\U0001f4f0", fill=(200, 200, 200), font=f)

def _wikipedia(draw):
    f = _font(24); draw.text((C-20, C-10), "\U0001f4d6", fill=(200, 200, 200), font=f)

def _movie(draw):
    f = _font(24); draw.text((C-20, C-10), "\U0001f3ac", fill=(255, 200, 50), font=f)

def _steam_icon(draw):
    f = _font(24); draw.text((C-20, C-10), "\U0001f3ae", fill=(100, 150, 255), font=f)

def _bitcoin(draw):
    f = _font(24); draw.text((C-18, C-10), "\u0243", fill=(255, 180, 50), font=f)

def _chart_line(draw):
    f = _font(24); draw.text((C-18, C-10), "\U0001f4c8", fill=(100, 255, 100), font=f)

def _connect4(draw):
    _rr(draw, C-20, C-24, C+20, C+24, 6, (50, 100, 200, 230))
    for y in [-14, -4, 6, 16]:
        for x in [-10, 0, 10]:
            draw.ellipse([C+x-4, C+y-4, C+x+4, C+y+4], fill=(255, 200, 50, 230), outline=(255, 255, 255, 100))

def _tic(draw):
    _rr(draw, C-22, C-22, C+22, C+22, 6, (200, 100, 200, 230))
    draw.line([C-12, C-12, C+12, C+12], fill=(255, 255, 255, 200), width=4)
    draw.line([C+12, C-12, C-12, C+12], fill=(255, 255, 255, 200), width=4)

def _hangman(draw):
    draw.line([C-20, C+20, C+20, C+20], fill=(255, 255, 255, 200), width=3)
    draw.line([C, C+20, C, C-24], fill=(255, 255, 255, 200), width=3)
    draw.line([C, C-24, C+12, C-24], fill=(255, 255, 255, 200), width=3)
    draw.line([C+12, C-24, C+12, C-18], fill=(255, 255, 255, 200), width=3)
    draw.ellipse([C+8, C-18, C+16, C-10], fill=(255, 255, 255, 200))
    draw.line([C+12, C-10, C+12, C+0], fill=(255, 255, 255, 200), width=3)
    draw.line([C+8, C-4, C+12, C-6, C+16, C-4], fill=(255, 255, 255, 200), width=2)
    draw.line([C+8, C+4, C+12, C+0, C+16, C+4], fill=(255, 255, 255, 200), width=2)

def _blackjack(draw):
    f = _font(28); draw.text((C-15, C-10), "\U0001f0cf", fill=(255, 50, 50), font=f)

def _type(draw):
    f = _font(24); draw.text((C-20, C-10), "ABC", fill=(100, 200, 255), font=f)

def _abc(draw):
    f = _font(24); draw.text((C-20, C-10), "Aa", fill=(100, 200, 255), font=f)

def _would_you(draw):
    f = _font(24); draw.text((C-20, C-10), "WYR", fill=(255, 150, 200), font=f)

def _never(draw):
    f = _font(20); draw.text((C-22, C-10), "NHIE", fill=(255, 100, 150), font=f)

def _truth_icon(draw):
    f = _font(24); draw.text((C-15, C-10), "T", fill=(100, 200, 255), font=f)

def _dare_icon(draw):
    f = _font(24); draw.text((C-15, C-10), "D", fill=(255, 100, 100), font=f)

def _horoscope(draw):
    f = _font(24); draw.text((C-15, C-10), "\u264c", fill=(180, 100, 255), font=f)

def _joke_icon(draw):
    f = _font(24); draw.text((C-15, C-10), "\U0001f601", fill=(255, 200, 50), font=f)

def _quote_icon(draw):
    f = _font(24); draw.text((C-15, C-10), "\u201c", fill=(200, 200, 200), font=f)

def _rep_icon(draw):
    f = _font(24); draw.text((C-15, C-10), "\u2b50", fill=(255, 215, 0), font=f)

def _ring(draw):
    f = _font(24); draw.text((C-15, C-10), "\U0001f48d", fill=(255, 200, 200), font=f)

def _badge(draw):
    f = _font(24); draw.text((C-15, C-10), "\U0001f3c5", fill=(255, 215, 0), font=f)

def _friend(draw):
    f = _font(24); draw.text((C-15, C-10), "\U0001f465", fill=(100, 200, 255), font=f)

def _clan(draw):
    f = _font(24); draw.text((C-15, C-10), "\U0001f3f9", fill=(255, 100, 50), font=f)

def _party_popper(draw):
    f = _font(30); draw.text((C-15, C-10), "\U0001f389", fill=(255, 200, 50), font=f)

# ── Icon registry ──

ICONS = {
    "CURRENCY":    (coin, "gold"),
    "WALLET":      (wallet, "gold"),
    "BANK":        (bank, "gold"),
    "TOTAL":       (chart_up, "gold"),
    "EARNED":      (chart_up, "green"),
    "SPENT":       (chart_down, "red"),
    "TROPHY":      (trophy, "gold"),
    "GOLD":        (lambda d: medal(d, "1"), "gold"),
    "SILVER":      (lambda d: medal(d, "2"), "grey"),
    "BRONZE":      (lambda d: medal(d, "3"), "orange"),
    "COOLDOWN":    (bell, "orange"),
    "DAILY":       (gift, "gold"),
    "STREAK":      (flame, "orange"),
    "WORK_BRIEF":  (briefcase, "blue"),
    "BEGGING":     (handshake, "orange"),
    "CRIME":       (gavel, "red"),
    "GAMBLE":      (dice, "purple"),
    "WIN":         (lambda d: crown(d, "gold"), "gold"),
    "LOSE":        (lambda d: crown(d, "grey"), "grey"),
    "ROB":         (lambda d: crown(d, "dark"), "dark"),
    "SHOP":        (lambda d: shop(d), "gold"),
    "DEPOSIT":     (lambda d: deposit(d), "green"),
    "WITHDRAW":    (lambda d: withdraw(d), "red"),
    "GIVEAWAY":    (gift, "pink"),
    "GIVEAWAY_WIN":(gift, "gold"),
    # Jobs
    "JOB_CODER":     (lambda d: icon_text(d, "</>", (100, 200, 255)), "blue"),
    "JOB_DESIGNER":  (lambda d: icon_text(d, "\U0001f3a8", (255, 100, 180)), "purple"),
    "JOB_CONSULTANT":(briefcase, "blue"),
    "JOB_TEACHER":   (lambda d: icon_text(d, "\U0001f4da", (255, 255, 255)), "blue"),
    "JOB_MINER":     (lambda d: icon_text(d, "\u26cf", (200, 200, 200)), "orange"),
    "JOB_FISHER":    (lambda d: icon_text(d, "\U0001f3a3", (100, 200, 200)), "teal"),
    "JOB_FARMER":    (lambda d: icon_text(d, "\U0001f33e", (100, 220, 100)), "green"),
    "JOB_CHEF":      (lambda d: icon_text(d, "\U0001f373", (255, 200, 50)), "orange"),
    "JOB_DOCTOR":    (lambda d: icon_text(d, "\u2695", (255, 255, 255)), "red"),
    "JOB_ENGINEER":  (lambda d: icon_text(d, "\u2699", (100, 200, 255)), "blue"),
    # Games
    "ROCK":         (lambda d: icon_text(d, "\U0001faa8", (255, 255, 255)), "grey"),
    "PAPER":        (lambda d: icon_text(d, "\U0001f4f0", (255, 255, 255)), "blue"),
    "SCISSORS":     (lambda d: icon_text(d, "\u2702", (255, 255, 255)), "red"),
    "COINFLIP":     (lambda d: coinflip(d), "gold"),
    "DICE":         (dice, "purple"),
    "EIGHT_BALL":   (eight_ball, "dark"),
    "SLOT_MACHINE": (slot, "red"),
    "SLOT_CHERRY":  (lambda d: icon_text(d, "\U0001f352", (255, 50, 50)), "red"),
    "SLOT_LEMON":   (lambda d: icon_text(d, "\U0001f34b", (255, 215, 0)), "gold"),
    "SLOT_ORANGE":  (lambda d: icon_text(d, "\U0001f34a", (255, 160, 50)), "orange"),
    "SLOT_GRAPE":   (lambda d: icon_text(d, "\U0001f347", (180, 100, 255)), "purple"),
    "SLOT_DIAMOND": (lambda d: icon_text(d, "\u2666", (0, 230, 255)), "cyan"),
    "TARGET_GUESS": (target, "green"),
    "TIE_RESULT":   (handshake, "grey"),
    "WIN_RESULT":   (trophy, "gold"),
    "LOSE_RESULT":  (lambda d: icon_text(d, "\U0001f44e", (255, 255, 255)), "grey"),
    "TRIVIA_GAME":  (lambda d: icon_text(d, "?", (255, 255, 255)), "purple"),
    # Music
    "PLAY_BUTTON":  (play, "teal"),
    "QUEUE_MUSIC":  (queue, "teal"),
    "SKIP_TRACK":   (skip, "teal"),
    "STOP_BUTTON":  (stop, "red"),
    "PAUSE_BUTTON": (pause, "teal"),
    "RESUME_BUTTON":(play, "teal"),
    "LEAVE_VC":     (wave, "teal"),
    "HELP_MUSIC":   (music_note, "teal"),
    # Moderation
    "CHECK_OK":     (lambda d: shield(d, "\u2714", THEMES["green"][0]), "green"),
    "CROSS_NO":     (lambda d: shield(d, "\u2718", THEMES["red"][0]), "red"),
    # Stats
    "STAT_MEMBERS": (people, "cyan"),
    "STAT_HUMANS":  (people, "cyan"),
    "STAT_BOTS":    (lambda d: icon_text(d, "\U0001f916", (0, 200, 255)), "cyan"),
    "STAT_CHANNELS":(lambda d: icon_text(d, "\U0001f4c1", (0, 200, 255)), "cyan"),
    "STAT_ROLES":   (lambda d: icon_text(d, "\U0001f3ad", (0, 200, 255)), "cyan"),
    "ONLINE_DOT":   (online_dot, "green"),
    "POLL_BAR":     (lambda d: poll(d), "cyan"),
    # Utility
    "REMINDER":       (bell, "orange"),
    "NOTE_SAVE":      (note, "orange"),
    "TRANSCRIPT_FILE":(note, "orange"),
    "AFK_ICON":       (lambda d: zzz(d), "purple"),
    "BIRTHDAY_CAKE":  (cake, "pink"),
    # Suggestions
    "SUGGESTION":   (lightbulb, "orange"),
    "UPVOTE":       (lambda d: icon_text(d, "\U0001f44d", (255, 255, 255)), "green"),
    "DOWNVOTE":     (lambda d: icon_text(d, "\U0001f44e", (255, 255, 255)), "red"),
    "LINK_CHANNEL": (lambda d: icon_text(d, "\U0001f517", (255, 255, 255)), "pink"),
    "LINK_ROLE":    (lambda d: icon_text(d, "\U0001f517", (255, 255, 255)), "pink"),
    # Help
    "HELP_ECONOMY": (coin, "gold"),
    "HELP_FUN":     (dice, "purple"),
    "HELP_MUSIC":   (music_note, "teal"),
    # ── New Economy ──
    "INVEST":       (_chart_bar, "gold"),
    "HORSE":        (_horse, "coral"),
    "LOTTERY":      (_ticket_lottery, "pink"),
    "BATTLE":       (_swords, "red"),
    "HEIST":        (_mask_heist, "dark"),
    "FISHING":      (_fish_hook, "teal"),
    "MINING":       (_pick, "orange"),
    "CRAFT":        (_craft, "orange"),
    "AUCTION":      (_gavel_auction, "gold"),
    "PET":          (_paw, "pink"),
    "FARMING":      (_seedling, "green"),
    # ── New AI ──
    "TRANSLATE":    (_translate_icon, "blue"),
    "TLDR":         (_eye, "blue"),
    "ROAST":        (_fire_roast, "red"),
    "COMPLIMENT":   (_heart, "pink"),
    "STORY":        (_book, "orange"),
    "POEM":         (_pen, "purple"),
    "EMAIL":        (_pen, "blue"),
    "BRAINSTORM":   (lightbulb, "gold"),
    "QUIZ":         (_crystal, "purple"),
    # ── New Fun ──
    "CONNECT4":     (_connect4, "blue"),
    "TICTACTOE":    (_tic, "purple"),
    "HANGMAN":      (_hangman, "grey"),
    "BLACKJACK":    (_blackjack, "red"),
    "TYPERACE":     (_type, "cyan"),
    "ANAGRAM":      (_abc, "purple"),
    "WOULDYOU":     (_would_you, "pink"),
    "NEVERHAVEIEVER":(_never, "pink"),
    "TRUTH":        (_truth_icon, "blue"),
    "DARE":         (_dare_icon, "red"),
    "SHIP":         (_ship_icon, "pink"),
    "HOROSCOPE":    (_horoscope, "purple"),
    "JOKE":         (_joke_icon, "gold"),
    "FACT":         (_book, "teal"),
    "QUOTE":        (_quote_icon, "gold"),
    # ── Integration ──
    "GITHUB":       (_github, "dark"),
    "TWITCH":       (_twitch, "purple"),
    "YOUTUBE":      (_youtube_icon, "red"),
    "TIMEZONE":     (_globe, "cyan"),
    "CURRENCY_CONV":(_money_exchange, "green"),
    "NEWS":         (_newspaper, "blue"),
    "URBAN":        (_book, "purple"),
    "WIKI":         (_wikipedia, "blue"),
    "IMDB":         (_movie, "gold"),
    "STEAM":        (_steam_icon, "blue"),
    "CRYPTO":       (_bitcoin, "gold"),
    "STOCK":        (_chart_line, "green"),
    "REDDIT":       (_globe, "orange"),
    "XKCD":         (_laugh, "blue"),
    # ── Media ──
    "RADIO":        (_radio, "teal"),
    "SOUNDBOARD":   (_soundboard, "orange"),
    "SPOTIFY":      (_headphone, "green"),
    # ── Social ──
    "REP":          (_rep_icon, "gold"),
    "MARRY":        (_ring, "pink"),
    "PROFILE":      (_badge, "cyan"),
    "BADGES":       (_badge, "gold"),
    "FRIEND":       (_friend, "blue"),
    "CLAN":         (_clan, "red"),
    # ── New Utility ──
    "QRCODE":       (lambda d: icon_text(d, "\U0001f4bb", (100, 200, 255)), "blue"),
    "PASSWORD":     (lambda d: icon_text(d, "\U0001f511", (100, 200, 255)), "cyan"),
    "HASH":         (lambda d: icon_text(d, "\u0023", (180, 100, 255)), "purple"),
    "SHORTEN":      (lambda d: icon_text(d, "\U0001f517", (100, 200, 255)), "blue"),
    "MATH":         (lambda d: icon_text(d, "\U0001f5a9", (100, 200, 255)), "cyan"),
    "BASE64":       (lambda d: icon_text(d, "b64", (180, 100, 255)), "purple"),
    "LYRICS":       (lambda d: icon_text(d, "\U0001f3a4", (100, 200, 200)), "teal"),
    "MUSIC_NEW":    (music_note, "teal"),
    # ── Moderation ──
    "JAIL":         (lambda d: icon_text(d, "\U0001f512", (255, 100, 100)), "red"),
    "REPORT":       (lambda d: icon_text(d, "\U0001f3c1", (255, 80, 80)), "red"),
    "APPEAL":       (lambda d: icon_text(d, "\u2764", (255, 100, 150)), "pink"),
    "NOTEBOOK":     (lambda d: icon_text(d, "\U0001f4d3", (255, 180, 50)), "orange"),
    # ── Server ──
    "VOICE":        (lambda d: icon_text(d, "\U0001f3a7", (100, 200, 200)), "teal"),
    "BUTTON":       (lambda d: icon_text(d, "\U0001f446", (100, 200, 255)), "cyan"),
    "BIRTHDAY":     (cake, "pink"),
    "COUNTDOWN":    (lambda d: icon_text(d, "\u23f1", (100, 200, 255)), "cyan"),
    "TEMPLATE":     (lambda d: icon_text(d, "\U0001f4cb", (100, 200, 255)), "blue"),
}

def shop(draw):
    _rr(draw, C-24, C-10, C+24, C+22, 4, (255, 215, 0, 230))
    draw.polygon([C-28, C-10, C, C-30, C+28, C-10], fill=(200, 170, 0, 230))

def deposit(draw):
    f = _font(28); draw.text((C-16, C-8), "\u2193", fill=(50, 210, 100), font=f)
    _rr(draw, C-20, C+2, C+20, C+16, 4, (50, 210, 100, 200))

def withdraw(draw):
    f = _font(28); draw.text((C-16, C-10), "\u2191", fill=(255, 80, 80), font=f)
    _rr(draw, C-20, C-16, C+20, C-2, 4, (255, 80, 80, 200))

def coinflip(draw):
    draw.ellipse([C-18, C-18, C+18, C+18], fill=(255, 215, 0, 230))
    f = _font(22); draw.text((C-10, C-6), "$", fill=(180, 130, 0), font=f)

def poll(draw):
    for x, h in [(-16, -8), (-8, -14), (0, -4), (8, -18), (16, -10)]:
        _rr(draw, C+x, C+h, C+x+6, C+16, 2, (0, 200, 255, 200))

def zzz(draw):
    f = _font(24)
    draw.text((C-25, C-10), "Z", fill=(180, 100, 255), font=f)
    draw.text((C-5, C-14), "Z", fill=(200, 140, 255), font=f)
    draw.text((C+10, C-18), "Z", fill=(220, 180, 255), font=f)

def icon_text(draw, text, color):
    f = _font(30); bb = draw.textbbox((0, 0), text, font=f)
    draw.text((C-(bb[2]-bb[0])//2, C-(bb[3]-bb[1])//2), text, fill=color, font=f)



ANIMATED = {
    "CURRENCY","DAILY","STREAK","COOLDOWN","TROPHY","GOLD","WIN","CRIME","GAMBLE",
    "GIVEAWAY","GIVEAWAY_WIN","CHECK_OK","CROSS_NO","ONLINE_DOT","POLL_BAR",
    "REMINDER","BIRTHDAY_CAKE","PLAY_BUTTON","QUEUE_MUSIC","SKIP_TRACK",
    "STOP_BUTTON","PAUSE_BUTTON","RESUME_BUTTON","COINFLIP","DICE","EIGHT_BALL",
    "SLOT_MACHINE","SLOT_DIAMOND","TARGET_GUESS","WIN_RESULT","TRIVIA_GAME",
    "SUGGESTION","UPVOTE","DOWNVOTE","HELP_MUSIC","HELP_ECONOMY","HELP_FUN",
    "INVEST","LOTTERY","BATTLE","HEIST","FISHING","MINING","CRAFT","AUCTION",
    "CONNECT4","BLACKJACK","TYPERACE","HOROSCOPE","JOKE","QUOTE","REP","BIRTHDAY",
    "COUNTDOWN","TRANSLATE","TLDR","ROAST","STORY","QUIZ","RADIO","NEWS",
}

NAMES = [
    "CURRENCY","WALLET","BANK","TOTAL","EARNED","SPENT","TROPHY","GOLD","SILVER","BRONZE",
    "COOLDOWN","DAILY","STREAK","WORK_BRIEF","BEGGING","CRIME","GAMBLE","WIN","LOSE","ROB",
    "SHOP","DEPOSIT","WITHDRAW","GIVEAWAY","GIVEAWAY_WIN",
    "JOB_CODER","JOB_DESIGNER","JOB_CONSULTANT","JOB_TEACHER","JOB_MINER","JOB_FISHER",
    "JOB_FARMER","JOB_CHEF","JOB_DOCTOR","JOB_ENGINEER",
    "ROCK","PAPER","SCISSORS","COINFLIP","DICE","EIGHT_BALL","SLOT_MACHINE",
    "SLOT_CHERRY","SLOT_LEMON","SLOT_ORANGE","SLOT_GRAPE","SLOT_DIAMOND",
    "TARGET_GUESS","TIE_RESULT","WIN_RESULT","LOSE_RESULT","TRIVIA_GAME",
    "PLAY_BUTTON","QUEUE_MUSIC","SKIP_TRACK","STOP_BUTTON","PAUSE_BUTTON","RESUME_BUTTON","LEAVE_VC","HELP_MUSIC",
    "CHECK_OK","CROSS_NO",
    "STAT_MEMBERS","STAT_HUMANS","STAT_BOTS","STAT_CHANNELS","STAT_ROLES","ONLINE_DOT","POLL_BAR",
    "REMINDER","NOTE_SAVE","TRANSCRIPT_FILE","AFK_ICON","BIRTHDAY_CAKE",
    "SUGGESTION","UPVOTE","DOWNVOTE","LINK_CHANNEL","LINK_ROLE",
    "HELP_ECONOMY","HELP_FUN","HELP_MUSIC",
    # New Economy
    "INVEST","HORSE","LOTTERY","BATTLE","HEIST","FISHING","MINING","CRAFT","AUCTION","PET","FARMING",
    # New AI
    "TRANSLATE","TLDR","ROAST","COMPLIMENT","STORY","POEM","EMAIL","BRAINSTORM","QUIZ",
    # New Fun
    "CONNECT4","TICTACTOE","HANGMAN","BLACKJACK","TYPERACE","ANAGRAM","WOULDYOU","NEVERHAVEIEVER",
    "TRUTH","DARE","SHIP","HOROSCOPE","JOKE","FACT","QUOTE",
    # Integration
    "GITHUB","TWITCH","YOUTUBE","TIMEZONE","CURRENCY_CONV","NEWS","URBAN","WIKI","IMDB","STEAM","CRYPTO","STOCK","REDDIT","XKCD",
    # Media
    "RADIO","SOUNDBOARD","SPOTIFY",
    # Social
    "REP","MARRY","PROFILE","BADGES","FRIEND","CLAN",
    # New Utility
    "QRCODE","PASSWORD","HASH","SHORTEN","MATH","BASE64","LYRICS","MUSIC_NEW",
    # Moderation
    "JAIL","REPORT","APPEAL","NOTEBOOK",
    # Server
    "VOICE","BUTTON","BIRTHDAY","COUNTDOWN","TEMPLATE",
]

def generate(name):
    info = ICONS.get(name)
    if info is None:
        img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        bg(draw, "grey")
        return img
    func, theme = info
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    bg(draw, theme)
    func(draw)
    return img


def main():
    for name in NAMES:
        is_anim = name in ANIMATED
        ext = "gif" if is_anim else "png"
        path = EMOJI_DIR / f"{name}.{ext}"

        img = generate(name)
        if is_anim:
            frames = [img]
            img2 = img.copy()
            d2 = ImageDraw.Draw(img2)
            d2.ellipse([18, 18, 110, 110], outline=(255, 255, 255, 60), width=2)
            frames.append(img2)
            frames[0].save(path, save_all=True, append_images=frames[1:],
                          loop=0, duration=2000, disposal=2)
        else:
            img.save(path)
        print(f"  {name:20s} -> {path.name:30s} ({path.stat().st_size:>6d}b)")

    print(f"\nDone! {len(NAMES)} emojis generated.")


if __name__ == "__main__":
    main()
