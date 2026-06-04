"""Generate premium NQN-style emojis with hand-drawn vector icons.

Uses geometric shapes (ellipses, arcs, polygons, paths) instead of text
characters for a premium look matching bots like Wick and Zynrax.
"""

import math
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter

EMOJI_DIR = Path("emojis")
EMOJI_DIR.mkdir(exist_ok=True)
S = 128
C = S // 2
F2 = 256
C2 = F2 // 2

FONT_CACHE: dict[int, ImageFont.FreeTypeFont] = {}

def _font(size=32):
    if size in FONT_CACHE:
        return FONT_CACHE[size]
    for name in ["segoeuib.ttf", "segoeui.ttf", "arialbd.ttf", "arial.ttf"]:
        p = f"C:/Windows/Fonts/{name}"
        if os.path.exists(p):
            try:
                f = ImageFont.truetype(p, size)
                FONT_CACHE[size] = f
                return f
            except Exception:
                continue
    f = ImageFont.load_default()
    FONT_CACHE[size] = f
    return f

def _gradient_circle(draw, cx, cy, r, c1, c2):
    for i in range(r, 0, -1):
        ratio = i / r
        col = tuple(int(a + (b - a) * (1 - ratio)) for a, b in zip(c1, c2))
        draw.ellipse([cx - i, cy - i, cx + i, cy + i], fill=col + (255,))

def _glow(draw, cx, cy, r, color, steps=10):
    for i in range(steps, 0, -1):
        alpha = int(35 * (1 - i / steps))
        dr = int(r * i / steps)
        draw.ellipse([cx - dr, cy - dr, cx + dr, cy + dr], fill=(*color, alpha))

def _ring(draw, cx, cy, r, width, color, alpha=255):
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(*color, alpha), width=width)

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
    "coral":  ((255, 120, 80), (200, 70, 40)),
}

def _make_bg(c1, c2):
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    _glow(draw, C, C, 60, c1)
    _gradient_circle(draw, C, C, 52, c1, c2)
    r2, g2, b2 = c2
    _ring(draw, C, C, 52, 3, (min(255, r2 + 60), min(255, g2 + 60), min(255, b2 + 60)))
    return img, draw

def _icon_circle(draw, cx, cy, r, color, alpha=220):
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*color, alpha))

def _icon_rect(draw, x1, y1, x2, y2, color, alpha=220, radius=0):
    x1, x2 = min(x1, x2), max(x1, x2)
    y1, y2 = min(y1, y2), max(y1, y2)
    if radius:
        draw.rounded_rectangle([x1, y1, x2, y2], radius=radius, fill=(*color, alpha))
    else:
        draw.rectangle([x1, y1, x2, y2], fill=(*color, alpha))

def _icon_tri(draw, cx, cy, r, color, alpha=220, rot=0):
    points = []
    for i in range(3):
        a = math.radians(rot + i * 120 - 90)
        points.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    draw.polygon(points, fill=(*color, alpha))

def _icon_diamond(draw, cx, cy, r, color, alpha=220):
    draw.polygon([(cx, cy - r), (cx + r * 0.7, cy), (cx, cy + r), (cx - r * 0.7, cy)], fill=(*color, alpha))

def _icon_star(draw, cx, cy, r, color, alpha=220, points=5):
    pts = []
    for i in range(points * 2):
        a = math.radians(i * 180 / points - 90)
        radius = r if i % 2 == 0 else r * 0.4
        pts.append((cx + radius * math.cos(a), cy + radius * math.sin(a)))
    draw.polygon(pts, fill=(*color, alpha))

# ══════════════════════════════════════════════════════════════
#  ICON DRAWING FUNCTIONS — each draws the icon in the center
# ══════════════════════════════════════════════════════════════

def _coin(draw):
    """Gold coin with $."""
    _icon_circle(draw, C, C, 22, (255, 215, 0))
    _icon_circle(draw, C, C, 18, (200, 130, 0), 100)
    f = _font(28); draw.text((C - 8, C - 15), "$", fill=(255, 255, 255), font=f)

def _wallet(draw):
    """Wallet with flap."""
    _icon_rect(draw, C - 22, C - 14, C + 22, C + 14, (255, 255, 255), radius=5)
    _icon_rect(draw, C - 10, C - 18, C + 10, C - 10, (200, 200, 200), radius=3)
    _icon_circle(draw, C + 6, C - 2, 4, (255, 215, 0))

def _bank(draw):
    """Bank with columns."""
    _icon_rect(draw, C - 24, C + 2, C + 24, C + 18, (255, 255, 255), radius=2)
    _icon_tri(draw, C, C - 6, 22, (255, 255, 255))
    cw = 5
    for x in range(-12, 16, 7):
        _icon_rect(draw, C + x, C - 4, C + x + cw, C + 18, (200, 200, 200))

def _trophy(draw):
    """Trophy cup."""
    _icon_rect(draw, C - 12, C - 4, C + 12, C + 16, (255, 215, 0), radius=6)
    _icon_rect(draw, C - 16, C + 16, C + 16, C + 20, (200, 130, 0), radius=2)
    for dx in [-16, 12]:
        _icon_rect(draw, C + dx, C - 6, C + dx + 4, C + 2, (255, 215, 0), radius=2)

def _crown(draw):
    """Crown with jewels."""
    pts = []
    for i in range(3):
        a = math.radians(i * 120 - 90)
        pts.append((C + 18 * math.cos(a), C - 6 + 18 * math.sin(a)))
    draw.polygon([(C - 22, C + 18), *pts, (C + 22, C + 18)], fill=(255, 215, 0))
    _icon_circle(draw, C, C + 10, 4, (255, 50, 50))
    _icon_circle(draw, C - 12, C - 2, 3, (50, 200, 255))
    _icon_circle(draw, C + 12, C - 2, 3, (50, 200, 255))

def _medal(draw):
    """Medal with star."""
    _icon_circle(draw, C, C - 4, 16, (255, 215, 0))
    _icon_star(draw, C, C - 4, 8, (200, 130, 0))
    _icon_rect(draw, C - 2, C + 10, C + 2, C + 22, (200, 130, 0))

def _dice_icon(draw):
    _icon_rect(draw, C - 18, C - 18, C + 18, C + 18, (255, 255, 255), radius=6)
    for px, py in [(-8, -8), (8, 8), (-8, 8), (8, -8), (0, 0)]:
        _icon_circle(draw, C + px, C + py, 3, (60, 60, 80))

def _slot_machine(draw):
    _icon_rect(draw, C - 22, C - 20, C + 22, C + 20, (255, 255, 255), radius=4)
    _icon_rect(draw, C - 18, C - 14, C + 18, C + 6, (60, 60, 80), radius=2)
    for i, (s, col) in enumerate([("🍒", (255, 50, 50)), ("🔔", (255, 215, 0)), ("7", (50, 255, 50))]):
        f = _font(16); draw.text((C - 16 + i * 18, C - 12), s, font=f)
    _icon_rect(draw, C - 20, C + 10, C + 20, C + 16, (255, 100, 50), radius=2)

def _shield_check(draw):
    draw.polygon([(C, C - 24), (C + 22, C - 14), (C + 22, C + 4), (C, C + 22), (C - 22, C + 4), (C - 22, C - 14)], fill=(50, 210, 100))
    _icon_rect(draw, C - 12, C - 2, C + 10, C + 14, (255, 255, 255), radius=2)
    draw.line([(C - 8, C + 6), (C - 2, C + 12), (C + 8, C)], fill=(50, 210, 100), width=3)

def _shield_x(draw):
    draw.polygon([(C, C - 24), (C + 22, C - 14), (C + 22, C + 4), (C, C + 22), (C - 22, C + 4), (C - 22, C - 14)], fill=(255, 80, 80))
    draw.line([(C - 10, C - 6), (C + 10, C + 10)], fill=(255, 255, 255), width=3)
    draw.line([(C + 10, C - 6), (C - 10, C + 10)], fill=(255, 255, 255), width=3)

def _music_note(draw):
    pts = []
    for i in range(3):
        a = math.radians(i * 120 - 60)
        pts.append((C + 22 * math.cos(a), C + 22 * math.sin(a)))
    draw.polygon(pts, fill=(50, 210, 210))
    _icon_circle(draw, C, C + 10, 6, (255, 255, 255))
    draw.rectangle([C - 2, C - 10, C + 2, C + 6], fill=(255, 255, 255))

def _play(draw):
    _icon_tri(draw, C, C, 18, (255, 255, 255), rot=90)

def _pause(draw):
    _icon_rect(draw, C - 10, C - 16, C - 3, C + 16, (255, 255, 255), radius=2)
    _icon_rect(draw, C + 3, C - 16, C + 10, C + 16, (255, 255, 255), radius=2)

def _skip(draw):
    draw.polygon([(C - 18, C - 16), (C + 2, C), (C - 18, C + 16)], fill=(255, 255, 255))
    _icon_rect(draw, C + 4, C - 16, C + 10, C + 16, (255, 255, 255), radius=2)

def _stop(draw):
    _icon_rect(draw, C - 14, C - 14, C + 14, C + 14, (255, 255, 255), radius=4)

def _queue(draw):
    for i in range(3):
        w = 6 + i * 6
        _icon_rect(draw, C - 16, C - 12 + i * 12, C - 16 + w, C - 6 + i * 12, (255, 255, 255), radius=2)

def _wave(draw):
    pts = []
    for x in range(-18, 20, 4):
        pts.append((C + x, C + 10 * math.sin(x * 0.3)))
    for i in range(len(pts) - 1):
        draw.line([pts[i], pts[i + 1]], fill=(255, 255, 255), width=3)

def _users(draw):
    for dx in [-10, 10]:
        _icon_circle(draw, C + dx, C - 4, 10, (255, 255, 255))
    body = [(C - 22, C + 22), (C + 22, C + 22), (C + 14, C + 2), (C - 14, C + 2)]
    draw.polygon(body, fill=(255, 255, 255))

def _online(draw):
    _icon_circle(draw, C, C, 18, (50, 210, 100))
    _icon_circle(draw, C, C, 12, (100, 255, 150))

def _bell(draw):
    draw.pieslice([C - 14, C - 22, C + 14, C + 6], 180, 0, fill=(255, 215, 0))
    _icon_circle(draw, C, C + 10, 6, (255, 215, 0))
    _icon_circle(draw, C, C + 10, 3, (255, 255, 255))

def _document(draw):
    _icon_rect(draw, C - 16, C - 20, C + 16, C + 20, (255, 255, 255), radius=2)
    for y in range(C - 12, C + 16, 6):
        _icon_rect(draw, C - 10, y, C + 10, y + 2, (200, 200, 200))

def _cake(draw):
    _icon_rect(draw, C - 18, C + 2, C + 18, C + 20, (255, 180, 200), radius=2)
    _icon_rect(draw, C - 5, C - 10, C + 5, C + 2, (255, 200, 220))
    for dx in [-12, 0, 12]:
        _icon_circle(draw, C + dx, C + 10, 2, (255, 100, 150))
    for dx in [-6, 6]:
        draw.line([(C + dx, C - 10), (C + dx, C - 20)], fill=(255, 200, 100), width=2)
        _icon_circle(draw, C + dx, C - 22, 3, (255, 200, 100))

def _lightbulb(draw):
    draw.pieslice([C - 14, C - 24, C + 14, C + 4], 180, 0, fill=(255, 215, 0))
    _icon_rect(draw, C - 4, C + 2, C + 4, C + 12, (255, 215, 0))
    for a in range(0, 360, 45):
        r = math.radians(a)
        x = C + 26 * math.cos(r)
        y = C - 10 + 26 * math.sin(r)
        _icon_circle(draw, x, y, 2, (255, 215, 0))

def _gear(draw):
    _icon_circle(draw, C, C, 16, (150, 150, 160))
    _icon_circle(draw, C, C, 8, (100, 100, 110))
    for a in range(0, 360, 60):
        r = math.radians(a)
        _icon_rect(draw, C + 12 * math.cos(r) - 3, C + 12 * math.sin(r) - 3, C + 20 * math.cos(r) + 3, C + 20 * math.sin(r) + 3, (150, 150, 160), radius=2)

def _briefcase(draw):
    _icon_rect(draw, C - 20, C + 2, C + 20, C + 20, (100, 160, 255), radius=4)
    _icon_rect(draw, C - 12, C - 6, C + 12, C + 2, (100, 160, 255), radius=4)
    _icon_rect(draw, C - 4, C - 10, C + 4, C - 6, (100, 160, 255))

def _hammer(draw):
    draw.line([(C + 6, C - 24), (C - 10, C + 18)], fill=(150, 150, 160), width=4)
    _icon_rect(draw, C - 16, C - 22, C + 8, C - 10, (150, 150, 160), radius=4)

def _tools(draw):
    _icon_circle(draw, C, C - 4, 14, (100, 200, 255))
    _icon_rect(draw, C - 2, C + 8, C + 2, C + 22, (100, 200, 255))

def _palette(draw):
    _icon_circle(draw, C, C, 18, (255, 200, 100))
    _icon_circle(draw, C + 8, C - 6, 6, (255, 100, 100))
    _icon_circle(draw, C - 6, C - 6, 6, (100, 200, 255))
    _icon_circle(draw, C, C + 10, 6, (100, 255, 100))

def _books(draw):
    for i, col in enumerate([(255, 100, 100), (100, 200, 255), (100, 255, 100)]):
        x = C - 18 + i * 12
        _icon_rect(draw, x, C - 18, x + 8, C + 18, col, radius=2)

def _pickaxe(draw):
    draw.line([(C - 4, C - 22), (C + 4, C + 22)], fill=(150, 150, 160), width=4)
    _icon_tri(draw, C, C - 22, 10, (200, 150, 100), rot=180)

def _fish(draw):
    draw.pieslice([C - 18, C - 12, C + 4, C + 12], 0, 180, fill=(50, 210, 210))
    draw.polygon([(C + 4, C - 12), (C + 18, C), (C + 4, C + 12)], fill=(50, 210, 210))
    _icon_circle(draw, C - 6, C - 2, 3, (255, 255, 255))

def _plant(draw):
    draw.line([(C, C + 18), (C, C - 6)], fill=(50, 210, 100), width=3)
    for a in [-15, 15]:
        r = math.radians(a)
        draw.line([(C, C - 6), (C + 12 * math.cos(r), C - 16 * math.sin(r))], fill=(50, 210, 100), width=2)
    _icon_circle(draw, C, C - 4, 4, (255, 200, 100))

def _chef(draw):
    _icon_circle(draw, C, C - 4, 16, (255, 255, 255))
    _icon_rect(draw, C - 10, C + 10, C + 10, C + 22, (255, 255, 255))
    _icon_rect(draw, C - 18, C - 6, C + 18, C + 2, (255, 255, 255))

def _caduceus(draw):
    draw.line([(C, C - 22), (C, C + 18)], fill=(255, 255, 255), width=3)
    for a in [-30, 30]:
        r = math.radians(a)
        draw.line([(C, C - 8), (C + 14 * math.cos(r), C - 8 + 14 * math.sin(r))], fill=(255, 255, 255), width=3)

def _chart_bar(draw):
    for i, h in enumerate([10, 16, 6, 22]):
        x = C - 16 + i * 10
        _icon_rect(draw, x, C + 18 - h, x + 6, C + 18, (100, 200, 255))

def _horse(draw):
    draw.arc([C - 18, C - 18, C + 18, C + 18], 0, 180, fill=(200, 150, 100), width=4)
    _icon_circle(draw, C + 8, C - 4, 4, (200, 150, 100))
    draw.line([(C + 8, C - 2), (C + 8, C + 14)], fill=(200, 150, 100), width=3)

def _ticket_lottery(draw):
    _icon_rect(draw, C - 20, C - 12, C + 20, C + 12, (255, 215, 0), radius=6)
    draw.arc([C - 4, C - 12, C + 4, C + 12], 90, 270, fill=(60, 60, 80), width=3)

def _swords(draw):
    draw.line([(C - 16, C - 20), (C + 16, C + 20)], fill=(200, 200, 210), width=4)
    draw.line([(C + 16, C - 20), (C - 16, C + 20)], fill=(200, 200, 210), width=4)
    _icon_tri(draw, C - 16, C - 20, 8, (200, 200, 210))
    _icon_tri(draw, C + 16, C + 20, 8, (200, 200, 210), rot=180)

def _mask_heist(draw):
    draw.ellipse([C - 18, C - 10, C + 18, C + 14], fill=(50, 50, 70))
    for x in [-8, 8]:
        draw.ellipse([C + x - 4, C - 2, C + x + 4, C + 4], fill=(180, 180, 200))

def _fish_hook(draw):
    draw.line([(C, C - 20), (C, C + 4)], fill=(150, 150, 160), width=3)
    draw.arc([C - 8, C, C + 8, C + 16], 0, 180, fill=(150, 150, 160), width=3)

def _pick(draw):
    draw.line([(C - 4, C - 20), (C + 4, C + 18)], fill=(200, 150, 100), width=4)
    _icon_rect(draw, C - 8, C + 18, C + 8, C + 24, (200, 150, 100), radius=2)

def _craft(draw):
    _icon_rect(draw, C - 16, C + 2, C + 16, C + 20, (150, 100, 200), radius=2)
    draw.line([(C, C - 16), (C, C + 2)], fill=(150, 100, 200), width=3)
    draw.line([(C - 18, C - 8), (C + 18, C - 8)], fill=(150, 100, 200), width=3)

def _gavel_auction(draw):
    _icon_rect(draw, C - 14, C - 8, C + 14, C + 20, (200, 150, 100), radius=2)
    _icon_rect(draw, C - 6, C - 8, C + 6, C - 14, (200, 150, 100))
    draw.line([(C - 14, C + 20), (C + 14, C + 20)], fill=(200, 150, 100), width=3)

def _paw(draw):
    for dx, dy in [(-8, -6), (8, -6), (-12, 4), (-4, 2), (4, 2), (12, 4)]:
        _icon_circle(draw, C + dx, C + dy, 5, (255, 200, 200))

def _seedling(draw):
    draw.line([(C, C + 18), (C, C - 8)], fill=(50, 210, 100), width=3)
    draw.pieslice([C - 10, C - 20, C + 10, C], 180, 0, fill=(50, 210, 100))

def _translate_icon(draw):
    _icon_circle(draw, C, C, 18, (100, 200, 255))
    draw.text((C - 6, C - 4), "A", fill=(255, 255, 255), font=_font(16))
    draw.text((C + 2, C + 2), "あ", fill=(255, 255, 255), font=_font(14))

def _eye(draw):
    draw.ellipse([C - 20, C - 10, C + 20, C + 10], fill=(255, 255, 255))
    _icon_circle(draw, C, C, 6, (60, 160, 255))

def _fire_roast(draw):
    for a in range(0, 360, 30):
        r = math.radians(a)
        _icon_circle(draw, C + 16 * math.cos(r), C + 16 * math.sin(r), 3, (255, 150, 50))
    _icon_tri(draw, C, C + 4, 10, (255, 100, 50), rot=180)

def _heart(draw):
    draw.pieslice([C - 14, C - 14, C, C + 2], 180, 360, fill=(255, 80, 120))
    draw.pieslice([C, C - 14, C + 14, C + 2], 180, 360, fill=(255, 80, 120))
    draw.polygon([(C - 14, C - 2), (C + 14, C - 2), (C, C + 18)], fill=(255, 80, 120))

def _book(draw):
    _icon_rect(draw, C - 14, C - 18, C + 14, C + 18, (255, 180, 80), radius=3)
    draw.line([(C, C - 18), (C, C + 18)], fill=(200, 130, 30), width=1)

def _pen(draw):
    draw.polygon([(C - 4, C + 18), (C + 16, C - 14), (C + 8, C - 20), (C - 12, C + 12)], fill=(100, 200, 255))

def _code_icon(draw):
    draw.line([(C - 18, C), (C - 6, C - 12), (C - 6, C + 12)], fill=(180, 100, 255), width=3)
    draw.line([(C + 18, C), (C + 6, C - 12), (C + 6, C + 12)], fill=(180, 100, 255), width=3)

def _search_icon(draw):
    _icon_circle(draw, C - 4, C - 4, 14, (100, 200, 255))
    draw.line([(C + 8, C + 8), (C + 20, C + 20)], fill=(100, 200, 255), width=4)

def _ship_icon(draw):
    draw.polygon([(C - 22, C + 8), (C + 22, C + 8), (C + 8, C - 14), (C - 2, C - 4)], fill=(100, 200, 255))
    draw.line([(C, C - 14), (C, C - 24)], fill=(150, 150, 160), width=3)
    draw.polygon([(C, C - 24), (C + 10, C - 14), (C, C - 14)], fill=(255, 255, 255))

def _crystal(draw):
    draw.polygon([(C, C - 22), (C + 14, C - 4), (C + 8, C + 18), (C - 8, C + 18), (C - 14, C - 4)], fill=(200, 150, 255))

def _muscle(draw):
    draw.arc([C - 18, C - 10, C + 4, C + 18], 180, 270, fill=(255, 200, 100), width=5)
    draw.arc([C - 4, C - 10, C + 18, C + 18], 270, 360, fill=(255, 200, 100), width=5)

def _thinking(draw):
    _icon_circle(draw, C, C, 18, (100, 200, 255))
    _icon_circle(draw, C - 6, C - 4, 3, (255, 255, 255))
    _icon_circle(draw, C + 6, C - 4, 3, (255, 255, 255))
    draw.arc([C - 8, C + 2, C + 8, C + 10], 0, 180, fill=(255, 255, 255), width=2)

def _clap(draw):
    for dx in [-10, 10]:
        _icon_circle(draw, C + dx, C, 10, (255, 200, 150))
        _icon_rect(draw, C + dx - 2, C + 8, C + dx + 2, C + 20, (255, 200, 150), radius=2)

def _laugh(draw):
    _icon_circle(draw, C, C, 18, (255, 215, 0))
    _icon_circle(draw, C - 6, C - 4, 3, (60, 60, 80))
    _icon_circle(draw, C + 6, C - 4, 3, (60, 60, 80))
    draw.arc([C - 10, C + 2, C + 10, C + 10], 0, 180, fill=(60, 60, 80), width=2)

def _sunglasses(draw):
    _icon_circle(draw, C, C, 18, (100, 200, 255))
    _icon_rect(draw, C - 16, C - 6, C - 2, C + 6, (30, 30, 50), radius=4)
    _icon_rect(draw, C + 2, C - 6, C + 16, C + 6, (30, 30, 50), radius=4)
    draw.arc([C - 8, C + 6, C + 8, C + 14], 0, 180, fill=(60, 60, 80), width=2)

def _party(draw):
    _icon_tri(draw, C, C + 8, 18, (255, 200, 100))
    draw.line([(C, C - 10), (C, C - 22)], fill=(255, 200, 100), width=3)
    for a in [30, -30]:
        r = math.radians(a)
        draw.line([(C + 14 * math.cos(r), C - 10 + 14 * math.sin(r)), (C + 22 * math.cos(r), C - 18 + 22 * math.sin(r))], fill=(255, 100, 100), width=2)

def _crossed_swords(draw):
    draw.line([(C - 18, C - 22), (C + 18, C + 22)], fill=(200, 200, 210), width=4)
    draw.line([(C + 18, C - 22), (C - 18, C + 22)], fill=(200, 200, 210), width=4)

def _skull(draw):
    draw.ellipse([C - 16, C - 18, C + 16, C + 16], fill=(200, 200, 210))
    for x in [-6, 6]:
        draw.ellipse([C + x - 4, C - 8, C + x + 4, C], fill=(30, 30, 50))
    draw.polygon([(C - 6, C + 4), (C + 6, C + 4), (C + 4, C + 14), (C - 4, C + 14)], fill=(30, 30, 50))

def _flag(draw):
    draw.line([(C, C - 22), (C, C + 22)], fill=(100, 100, 110), width=3)
    draw.polygon([(C, C - 22), (C + 22, C - 14), (C, C - 6)], fill=(255, 80, 80))

def _tada(draw):
    for a in [0, 45, 90, 135]:
        r = math.radians(a)
        draw.line([(C + 14 * math.cos(r), C + 14 * math.sin(r)), (C + 24 * math.cos(r), C + 24 * math.sin(r))], fill=(255, 200, 50), width=2)
    _icon_circle(draw, C, C, 10, (255, 100, 100))
    _icon_circle(draw, C, C, 6, (255, 215, 0))

def _microphone(draw):
    _icon_rect(draw, C - 6, C - 18, C + 6, C + 6, (100, 200, 255), radius=4)
    draw.pieslice([C - 10, C - 2, C + 10, C + 14], 180, 0, fill=(100, 200, 255))

def _headphone(draw):
    draw.arc([C - 16, C - 18, C + 16, C + 10], 0, 180, fill=(100, 200, 255), width=4)
    _icon_rect(draw, C - 20, C - 2, C - 12, C + 14, (100, 200, 255), radius=4)
    _icon_rect(draw, C + 12, C - 2, C + 20, C + 14, (100, 200, 255), radius=4)

def _radio(draw):
    _icon_rect(draw, C - 22, C - 14, C + 22, C + 18, (100, 200, 200), radius=6)
    _icon_circle(draw, C - 8, C + 4, 10, (60, 60, 80))
    _icon_circle(draw, C - 8, C + 4, 6, (100, 200, 255))
    _icon_rect(draw, C + 4, C - 4, C + 18, C + 4, (60, 60, 80), radius=2)
    _icon_rect(draw, C + 4, C + 8, C + 18, C + 14, (60, 60, 80), radius=2)

def _soundboard(draw):
    _icon_rect(draw, C - 22, C - 16, C + 22, C + 16, (200, 100, 50), radius=4)
    for i in range(3):
        _icon_rect(draw, C - 14 + i * 10, C + 2, C - 8 + i * 10, C + 10 - i * 4, (100, 200, 255), radius=2)

def _github(draw):
    _icon_circle(draw, C, C, 18, (50, 50, 50))
    _icon_circle(draw, C, C, 14, (30, 30, 30))
    draw.line([(C, C - 16), (C, C + 16)], fill=(200, 200, 200), width=2)
    draw.line([(C - 16, C), (C + 16, C)], fill=(200, 200, 200), width=2)

def _twitch(draw):
    draw.polygon([(C - 18, C + 22), (C - 18, C - 14), (C - 4, C - 22), (C + 14, C - 22), (C + 18, C - 14), (C + 18, C + 6), (C + 4, C + 20), (C - 4, C + 20)], fill=(100, 50, 200))

def _youtube_icon(draw):
    _icon_rect(draw, C - 22, C - 14, C + 22, C + 14, (255, 50, 50), radius=6)
    draw.polygon([(C - 8, C - 8), (C - 8, C + 8), (C + 14, C)], fill=(255, 255, 255))

def _globe(draw):
    _icon_circle(draw, C, C, 18, (50, 200, 255))
    draw.arc([C - 18, C - 6, C + 18, C + 6], 0, 360, fill=(50, 150, 200), width=2)
    draw.line([(C, C - 18), (C, C + 18)], fill=(50, 150, 200), width=2)

def _money_exchange(draw):
    _icon_circle(draw, C - 6, C, 14, (100, 200, 255))
    _icon_circle(draw, C + 6, C, 14, (100, 200, 255))
    _icon_circle(draw, C, C, 8, (255, 215, 0))

def _newspaper(draw):
    _icon_rect(draw, C - 18, C - 20, C + 18, C + 20, (255, 255, 255), radius=2)
    _icon_rect(draw, C - 14, C - 16, C + 14, C - 12, (200, 50, 50))
    for y in range(-8, 18, 6):
        _icon_rect(draw, C - 14, y, C + 14, y + 2, (200, 200, 200))

def _wikipedia(draw):
    _icon_circle(draw, C, C, 18, (50, 50, 50))
    draw.text((C - 7, C - 6), "W", fill=(255, 255, 255), font=_font(22))

def _movie(draw):
    _icon_rect(draw, C - 22, C - 14, C + 22, C + 14, (100, 200, 255), radius=4)
    draw.polygon([(C - 6, C - 8), (C - 6, C + 8), (C + 14, C)], fill=(255, 255, 255))

def _steam_icon(draw):
    _icon_circle(draw, C, C, 18, (30, 30, 50))
    draw.arc([C - 12, C - 8, C + 4, C + 8], 0, 270, fill=(100, 200, 255), width=4)
    _icon_circle(draw, C + 4, C + 6, 6, (100, 200, 255))

def _bitcoin(draw):
    _icon_circle(draw, C, C, 18, (255, 150, 0))
    draw.text((C - 7, C - 6), "B", fill=(255, 255, 255), font=_font(20))

def _chart_line(draw):
    draw.line([(C - 18, C + 16), (C - 6, C + 6), (C + 4, C + 10), (C + 18, C - 2)], fill=(50, 210, 100), width=3)
    _icon_circle(draw, C + 18, C - 2, 3, (50, 210, 100))

def _connect4(draw):
    for i, col in enumerate([(255, 50, 50), (255, 215, 0)]):
        _icon_circle(draw, C - 6 + i * 12, C - 4, 6, col)
    _icon_rect(draw, C - 22, C + 8, C + 22, C + 18, (50, 100, 200), radius=2)

def _tic(draw):
    _icon_rect(draw, C - 20, C - 20, C + 20, C + 20, (50, 50, 70), radius=4)
    draw.line([(C - 10, C), (C - 12, C + 12), (C + 12, C - 8)], fill=(50, 210, 100), width=3)

def _hangman(draw):
    draw.line([(C - 18, C + 20), (C + 18, C + 20)], fill=(100, 100, 110), width=3)
    draw.line([(C - 6, C + 20), (C - 6, C - 18)], fill=(100, 100, 110), width=3)
    draw.line([(C - 6, C - 18), (C + 10, C - 18)], fill=(100, 100, 110), width=3)
    draw.line([(C + 10, C - 18), (C + 10, C - 14)], fill=(100, 100, 110), width=3)
    _icon_circle(draw, C + 10, C - 10, 5, (100, 100, 110))
    draw.line([(C + 10, C - 4), (C + 10, C + 6)], fill=(100, 100, 110), width=3)

def _blackjack(draw):
    _icon_rect(draw, C - 16, C - 20, C + 16, C + 20, (255, 255, 255), radius=4)
    draw.text((C - 5, C - 8), "A", fill=(255, 50, 50), font=_font(24))
    _icon_circle(draw, C - 12, C + 4, 8, (255, 215, 0))
    _icon_circle(draw, C + 12, C + 4, 8, (255, 215, 0))

def _type(draw):
    _icon_rect(draw, C - 20, C - 14, C + 20, C + 14, (100, 200, 255), radius=4)
    draw.text((C - 7, C - 6), "A", fill=(255, 255, 255), font=_font(20))

def _abc(draw):
    _icon_rect(draw, C - 20, C - 14, C + 20, C + 14, (150, 100, 200), radius=4)
    for i, s in enumerate(["A", "B", "C"]):
        draw.text((C - 14 + i * 12, C - 7), s, fill=(255, 255, 255), font=_font(16))

def _would_you(draw):
    _icon_circle(draw, C - 8, C - 4, 10, (100, 200, 255))
    _icon_circle(draw, C + 8, C - 4, 10, (255, 200, 100))
    draw.text((C - 14, C + 6), "?", fill=(255, 255, 255), font=_font(14))

def _never(draw):
    _icon_circle(draw, C, C, 18, (255, 100, 100))
    _icon_circle(draw, C, C, 12, (255, 255, 255))
    draw.text((C - 8, C - 7), "X", fill=(255, 100, 100), font=_font(22))

def _truth_icon(draw):
    _icon_circle(draw, C, C, 18, (150, 100, 200))
    draw.text((C - 7, C - 7), "T", fill=(255, 255, 255), font=_font(22))

def _dare_icon(draw):
    _icon_circle(draw, C, C, 18, (255, 150, 50))
    draw.text((C - 7, C - 7), "D", fill=(255, 255, 255), font=_font(22))

def _horoscope(draw):
    _icon_circle(draw, C, C, 18, (255, 215, 0))
    draw.arc([C - 14, C - 14, C + 14, C + 14], 0, 270, fill=(255, 255, 255), width=3)
    _icon_circle(draw, C, C, 4, (255, 255, 255))

def _joke_icon(draw):
    _icon_circle(draw, C, C, 18, (255, 215, 0))
    draw.line([(C - 10, C - 4), (C + 10, C - 4)], fill=(60, 60, 80), width=2)
    draw.arc([C - 10, C + 2, C + 10, C + 10], 0, 180, fill=(60, 60, 80), width=2)

def _quote_icon(draw):
    draw.pieslice([C - 18, C - 18, C, C + 2], 180, 360, fill=(100, 200, 255))
    draw.pieslice([C, C - 18, C + 18, C + 2], 180, 360, fill=(100, 200, 255))
    draw.polygon([(C - 18, C - 2), (C + 18, C - 2), (C, C + 18)], fill=(100, 200, 255))

def _rep_icon(draw):
    _icon_star(draw, C, C, 16, (255, 215, 0))

def _ring_icon(draw):
    _icon_circle(draw, C, C, 14, (255, 215, 0))
    _icon_circle(draw, C, C, 8, (200, 130, 0))
    _icon_diamond(draw, C, C, 6, (255, 255, 255))

def _badge(draw):
    draw.polygon([(C, C - 22), (C + 16, C - 10), (C + 16, C + 8), (C, C + 20), (C - 16, C + 8), (C - 16, C - 10)], fill=(100, 200, 255))
    _icon_circle(draw, C, C - 2, 8, (255, 255, 255))
    _icon_star(draw, C, C - 2, 4, (100, 200, 255))

def _friend(draw):
    _icon_circle(draw, C - 6, C - 6, 12, (100, 200, 255))
    _icon_circle(draw, C + 10, C - 6, 12, (255, 200, 100))
    body1 = [(C - 18, C + 20), (C + 6, C + 20), (C + 6, C), (C - 18, C)]
    body2 = [(C - 2, C + 20), (C + 22, C + 20), (C + 22, C), (C - 2, C)]
    draw.polygon(body1, fill=(100, 200, 255))
    draw.polygon(body2, fill=(255, 200, 100))

def _clan(draw):
    _icon_rect(draw, C - 20, C - 14, C + 20, C + 18, (50, 150, 200), radius=6)
    _icon_rect(draw, C - 14, C - 8, C + 14, C + 8, (100, 200, 255), radius=4)
    for i in range(3):
        _icon_rect(draw, C - 10 + i * 10, C + 2, C - 4 + i * 10, C + 14, (50, 150, 200), radius=2)

def _lock(draw):
    _icon_rect(draw, C - 14, C, C + 14, C + 22, (255, 215, 0), radius=4)
    draw.arc([C - 14, C - 22, C + 14, C + 2], 180, 0, fill=(255, 215, 0), width=5)
    _icon_circle(draw, C, C + 10, 4, (200, 130, 0))

def _pointer(draw):
    draw.polygon([(C, C - 20), (C + 14, C + 2), (C, C - 4), (C - 14, C + 2)], fill=(100, 200, 255))

def _copy(draw):
    _icon_rect(draw, C - 12, C - 14, C + 16, C + 18, (100, 200, 255), radius=4)
    _icon_rect(draw, C - 16, C - 18, C + 12, C + 14, (150, 220, 255), radius=4)

def _timer_icon(draw):
    _icon_circle(draw, C, C, 18, (100, 200, 255))
    draw.line([(C, C), (C, C - 14)], fill=(255, 255, 255), width=3)
    draw.line([(C, C), (C + 10, C)], fill=(255, 255, 255), width=3)
    _icon_circle(draw, C, C, 4, (255, 255, 255))

def _calculator(draw):
    _icon_rect(draw, C - 18, C - 20, C + 18, C + 20, (100, 200, 255), radius=4)
    _icon_rect(draw, C - 16, C - 16, C + 16, C - 8, (60, 60, 80))
    for x in range(-12, 16, 8):
        for y in range(0, 20, 8):
            _icon_circle(draw, C + x, C + y, 2, (60, 60, 80))

def _poll(draw):
    for i, h in enumerate([6, 16, 10, 20]):
        x = C - 16 + i * 10
        colors = [(255, 80, 80), (50, 210, 100), (100, 200, 255), (255, 215, 0)]
        _icon_rect(draw, x, C + 18 - h, x + 6, C + 18, colors[i])

def _globe_icon(draw):
    _icon_circle(draw, C, C, 18, (50, 200, 255))

# ══════════════════════════════════════════════════════════════
#  ICON REGISTRY
# ══════════════════════════════════════════════════════════════

def icon_text(draw, text, color):
    f = _font(30)
    bbox = draw.textbbox((0, 0), text, font=f)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    draw.text(((S - tw) // 2, (S - th) // 2 - 2), text, fill=(*color, 255), font=f)

def make_emoji(icon_fn, theme_name, animated=False):
    c1, c2 = THEMES.get(theme_name, THEMES["blue"])
    img, draw = _make_bg(c1, c2)
    icon_fn(draw)
    mask = img.split()[3] if img.mode == "RGBA" else None
    if mask:
        img = Image.composite(img, Image.new("RGBA", img.size, (0, 0, 0, 0)), mask)
    return img

def make_animated(icon_fn, theme_name, frames=15):
    c1, c2 = THEMES.get(theme_name, THEMES["blue"])
    images = []
    for i in range(frames):
        img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        _glow(draw, C, C, 60, c1)
        _gradient_circle(draw, C, C, 52, c1, c2)
        _ring(draw, C, C, 52, 3, (min(255, c2[0] + 60), min(255, c2[1] + 60), min(255, c2[2] + 60)))
        icon_fn(draw)
        images.append(img)
    return images

def _bag(draw):
    _icon_circle(draw, C - 8, C - 4, 8, (255, 215, 0))
    _icon_rect(draw, C - 18, C + 2, C + 18, C + 20, (255, 215, 0), radius=4)
    _icon_rect(draw, C - 10, C - 6, C + 10, C + 2, (255, 215, 0), radius=4)

def _check(draw):
    draw.line([(C - 14, C), (C - 4, C + 12), (C + 14, C - 10)], fill=(50, 210, 100), width=4)

def _moon(draw):
    draw.pieslice([C - 18, C - 18, C + 18, C + 18], 135, 405, fill=(150, 100, 200))
    _icon_circle(draw, C + 4, C - 4, 8, (100, 60, 150))

ICONS = {
    # ── Economy ──
    "CURRENCY":     (_coin, "gold"),
    "WALLET":       (_wallet, "gold"),
    "BANK":         (_bank, "blue"),
    "TOTAL":        (_coin, "gold"),
    "EARNED":       (_chart_bar, "green"),
    "SPENT":        (_chart_bar, "red"),
    "TROPHY":       (_trophy, "gold"),
    "GOLD":         (_medal, "gold"),
    "SILVER":       (_medal, "grey"),
    "BRONZE":       (_medal, "orange"),
    "COOLDOWN":     (_timer_icon, "teal"),
    "DAILY":        (_bell, "gold"),
    "STREAK":       (_fire_roast, "orange"),
    "WORK_BRIEF":   (_briefcase, "blue"),
    "BEGGING":      (_heart, "pink"),
    "CRIME":        (_mask_heist, "dark"),
    "GAMBLE":       (_slot_machine, "purple"),
    "WIN":          (_tada, "green"),
    "LOSE":         (_skull, "red"),
    "ROB":          (_mask_heist, "dark"),
    "SHOP":         (_bag, "gold"),
    "DEPOSIT":      (_bank, "green"),
    "WITHDRAW":     (_bank, "red"),
    "GIVEAWAY":     (_tada, "gold"),
    "GIVEAWAY_WIN": (_trophy, "gold"),
    "HELP_ECONOMY": (_coin, "gold"),
    "HELP_FUN":     (_party, "purple"),
    "HELP_MUSIC":   (_music_note, "teal"),

    # ── Economy Jobs ──
    "JOB_CODER":       (_code_icon, "blue"),
    "JOB_DESIGNER":    (_palette, "purple"),
    "JOB_CONSULTANT":  (_briefcase, "blue"),
    "JOB_TEACHER":     (_books, "green"),
    "JOB_MINER":       (_pickaxe, "orange"),
    "JOB_FISHER":      (_fish, "teal"),
    "JOB_FARMER":      (_seedling, "green"),
    "JOB_CHEF":        (_chef, "orange"),
    "JOB_DOCTOR":      (_caduceus, "teal"),
    "JOB_ENGINEER":    (_gear, "grey"),

    # ── Games ──
    "ROCK":         (_shield_x, "grey"),
    "PAPER":        (_document, "blue"),
    "SCISSORS":     (_crossed_swords, "red"),
    "COINFLIP":     (_coin, "gold"),
    "DICE":         (_dice_icon, "purple"),
    "EIGHT_BALL":   (_crystal, "purple"),
    "SLOT_MACHINE": (_slot_machine, "purple"),
    "SLOT_CHERRY":  (lambda d: icon_text(d, "🍒", (255, 50, 50)), "red"),
    "SLOT_LEMON":   (lambda d: icon_text(d, "🍋", (255, 215, 0)), "gold"),
    "SLOT_ORANGE":  (lambda d: icon_text(d, "🍊", (255, 150, 50)), "orange"),
    "SLOT_GRAPE":   (lambda d: icon_text(d, "🍇", (150, 50, 200)), "purple"),
    "SLOT_DIAMOND": (_crystal, "cyan"),
    "TARGET_GUESS": (_search_icon, "cyan"),
    "TIE_RESULT":   (lambda d: icon_text(d, "=", (255, 255, 255)), "grey"),
    "WIN_RESULT":   (_check, "green"),
    "LOSE_RESULT":  (_skull, "red"),
    "TRIVIA_GAME":  (_would_you, "purple"),

    # ── Music ──
    "PLAY_BUTTON":  (_play, "green"),
    "QUEUE_MUSIC":  (_queue, "teal"),
    "SKIP_TRACK":   (_skip, "teal"),
    "STOP_BUTTON":  (_stop, "red"),
    "PAUSE_BUTTON": (_pause, "teal"),
    "RESUME_BUTTON":(_play, "green"),
    "LEAVE_VC":     (_wave, "red"),
    "HELP_MUSIC":   (_music_note, "teal"),

    # ── Moderation ──
    "CHECK_OK":     (_shield_check, "green"),
    "CROSS_NO":     (_shield_x, "red"),

    # ── Giveaway ──
    "GIVEAWAY":     (_tada, "gold"),
    "GIVEAWAY_WIN": (_trophy, "gold"),

    # ── Suggestions ──
    "SUGGESTION":   (_lightbulb, "gold"),
    "UPVOTE":       (_check, "green"),
    "DOWNVOTE":     (_skull, "red"),

    # ── Link Moderation ──
    "LINK_CHANNEL": (_globe, "blue"),
    "LINK_ROLE":    (_badge, "purple"),

    # ── Server Stats ──
    "STAT_MEMBERS": (_users, "blue"),
    "STAT_HUMANS":  (_users, "green"),
    "STAT_BOTS":    (_gear, "grey"),
    "STAT_CHANNELS":(_document, "orange"),
    "STAT_ROLES":   (_badge, "purple"),
    "ONLINE_DOT":   (_online, "green"),
    "POLL_BAR":     (_poll, "blue"),

    # ── Utility Ext ──
    "AFK_ICON":     (_moon, "purple"),
    "BIRTHDAY_CAKE":(_cake, "pink"),

    # ── Tags ──
    "REMINDER":        (_bell, "teal"),
    "NOTE_SAVE":       (_document, "blue"),
    "TRANSCRIPT_FILE": (_document, "orange"),

    # ── New Economy ──
    "INVEST":       (_chart_bar, "green"),
    "HORSE":        (_horse, "orange"),
    "LOTTERY":      (_ticket_lottery, "gold"),
    "BATTLE":       (_swords, "red"),
    "HEIST":        (_mask_heist, "dark"),
    "FISHING":      (_fish_hook, "teal"),
    "MINING":       (_pickaxe, "orange"),
    "CRAFT":        (_craft, "purple"),
    "AUCTION":      (_gavel_auction, "gold"),
    "PET":          (_paw, "pink"),
    "FARMING":      (_seedling, "green"),

    # ── New AI ──
    "TRANSLATE":    (_translate_icon, "blue"),
    "TLDR":         (_document, "teal"),
    "ROAST":        (_fire_roast, "red"),
    "COMPLIMENT":   (_heart, "pink"),
    "STORY":        (_book, "orange"),
    "POEM":         (_pen, "purple"),
    "EMAIL":        (_document, "blue"),
    "BRAINSTORM":   (_lightbulb, "gold"),
    "QUIZ":         (_would_you, "purple"),

    # ── Fun Games ──
    "CONNECT4":       (_connect4, "blue"),
    "TICTACTOE":      (_tic, "green"),
    "HANGMAN":        (_hangman, "purple"),
    "BLACKJACK":      (_blackjack, "gold"),
    "TYPERACE":       (_type, "cyan"),
    "ANAGRAM":        (_abc, "purple"),
    "WOULDYOU":       (_would_you, "cyan"),
    "NEVERHAVEIEVER": (_never, "red"),
    "TRUTH":          (_truth_icon, "purple"),
    "DARE":           (_dare_icon, "orange"),
    "SHIP":           (_ship_icon, "pink"),
    "HOROSCOPE":      (_horoscope, "gold"),
    "JOKE":           (_joke_icon, "gold"),
    "FACT":           (_document, "blue"),
    "QUOTE":          (_quote_icon, "teal"),

    # ── Music / Media New ──
    "RADIO":        (_radio, "teal"),
    "SOUNDBOARD":   (_soundboard, "orange"),
    "SPOTIFY":      (_headphone, "green"),
    "VOLUME":       (lambda d: icon_text(d, "\U0001f509", (100, 200, 255)), "cyan"),
    "LOOP":         (lambda d: icon_text(d, "\U0001f501", (100, 255, 150)), "teal"),
    "SHUFFLE":      (lambda d: icon_text(d, "\U0001f500", (200, 150, 255)), "purple"),
    "SAVE_MUSIC":   (lambda d: icon_text(d, "\U0001f4be", (100, 180, 255)), "blue"),
    "PLAYLIST":     (lambda d: icon_text(d, "\U0001f4cb", (100, 200, 200)), "teal"),

    # ── Integration ──
    "GITHUB":       (_github, "dark"),
    "TWITCH":       (_twitch, "purple"),
    "YOUTUBE":      (_youtube_icon, "red"),
    "TIMEZONE":     (_globe, "cyan"),
    "CURRENCY_CONV":(_money_exchange, "green"),
    "NEWS":         (_newspaper, "blue"),
    "URBAN":        (_book, "purple"),
    "WIKI":         (_wikipedia, "dark"),
    "IMDB":         (_movie, "gold"),
    "STEAM":        (_steam_icon, "dark"),
    "CRYPTO":       (_bitcoin, "orange"),
    "STOCK":        (_chart_line, "green"),
    "REDDIT":       (_search_icon, "orange"),
    "XKCD":         (_book, "blue"),

    # ── Social ──
    "REP":          (_rep_icon, "gold"),
    "MARRY":        (_heart, "pink"),
    "PROFILE":      (_users, "blue"),
    "BADGES":       (_badge, "gold"),
    "FRIEND":       (_friend, "cyan"),
    "CLAN":         (_clan, "blue"),

    # ── New Utility ──
    "QRCODE":       (lambda d: icon_text(d, "\U0001f4bb", (100, 200, 255)), "blue"),
    "PASSWORD":     (_lock, "cyan"),
    "HASH":         (lambda d: icon_text(d, "\u0023", (180, 100, 255)), "purple"),
    "SHORTEN":      (_lock, "blue"),
    "MATH":         (_calculator, "cyan"),
    "BASE64":       (lambda d: icon_text(d, "b64", (180, 100, 255)), "purple"),
    "LYRICS":       (_microphone, "teal"),
    "MUSIC_NEW":    (_music_note, "teal"),

    # ── Moderation New ──
    "JAIL":         (_lock, "red"),
    "REPORT":       (_flag, "red"),
    "APPEAL":       (_heart, "pink"),
    "NOTEBOOK":     (_document, "orange"),

    # ── Server New ──
    "VOICE":        (_headphone, "teal"),
    "BUTTON":       (_pointer, "cyan"),
    "BIRTHDAY":     (_cake, "pink"),
    "COUNTDOWN":    (_timer_icon, "cyan"),
    "TEMPLATE":     (_document, "blue"),
}

# ══════════════════════════════════════════════════════════════
#  ANIMATED & STATIC LISTS
# ══════════════════════════════════════════════════════════════

ANIMATED = {
    "CURRENCY","COOLDOWN","DAILY","STREAK","CRIME","GAMBLE","WIN","DICE",
    "EIGHT_BALL","SLOT_MACHINE","SLOT_DIAMOND","TARGET_GUESS","WIN_RESULT",
    "COINFLIP","GIVEAWAY","GIVEAWAY_WIN","TROPHY","GOLD",
    "PLAY_BUTTON","QUEUE_MUSIC","SKIP_TRACK","STOP_BUTTON","PAUSE_BUTTON",
    "RESUME_BUTTON","HELP_MUSIC","CHECK_OK","CROSS_NO","ONLINE_DOT","POLL_BAR",
    "REMINDER","SUGGESTION","UPVOTE","DOWNVOTE","HELP_ECONOMY","HELP_FUN",
    "BIRTHDAY_CAKE",
    "INVEST","LOTTERY","BATTLE","HEIST","FISHING","MINING","CRAFT","AUCTION",
    "TRANSLATE","TLDR","ROAST","STORY","QUIZ",
    "CONNECT4","BLACKJACK","TYPERACE",
    "HOROSCOPE","JOKE","QUOTE","NEWS","RADIO",
    "REP","COUNTDOWN","BIRTHDAY",
}

NAMES = [
    "CURRENCY","WALLET","BANK","TOTAL","EARNED","SPENT","TROPHY","GOLD","SILVER","BRONZE",
    "COOLDOWN","DAILY","STREAK","WORK_BRIEF","BEGGING","CRIME","GAMBLE","WIN","LOSE","ROB",
    "SHOP","DEPOSIT","WITHDRAW","GIVEAWAY","GIVEAWAY_WIN","HELP_ECONOMY","HELP_FUN",
    "HELP_MUSIC",
    "JOB_CODER","JOB_DESIGNER","JOB_CONSULTANT","JOB_TEACHER","JOB_MINER","JOB_FISHER",
    "JOB_FARMER","JOB_CHEF","JOB_DOCTOR","JOB_ENGINEER",
    "ROCK","PAPER","SCISSORS","COINFLIP","DICE","EIGHT_BALL","SLOT_MACHINE",
    "SLOT_CHERRY","SLOT_LEMON","SLOT_ORANGE","SLOT_GRAPE","SLOT_DIAMOND",
    "TARGET_GUESS","TIE_RESULT","WIN_RESULT","LOSE_RESULT","TRIVIA_GAME",
    "PLAY_BUTTON","QUEUE_MUSIC","SKIP_TRACK","STOP_BUTTON","PAUSE_BUTTON",
    "RESUME_BUTTON","LEAVE_VC","HELP_MUSIC",
    "CHECK_OK","CROSS_NO",
    "STAT_MEMBERS","STAT_HUMANS","STAT_BOTS","STAT_CHANNELS","STAT_ROLES",
    "ONLINE_DOT","POLL_BAR",
    "REMINDER","NOTE_SAVE","TRANSCRIPT_FILE",
    "AFK_ICON","BIRTHDAY_CAKE","SUGGESTION","UPVOTE","DOWNVOTE",
    "LINK_CHANNEL","LINK_ROLE",
    "HELP_ECONOMY","HELP_FUN","HELP_MUSIC",
    "INVEST","HORSE","LOTTERY","BATTLE","HEIST","FISHING","MINING","CRAFT","AUCTION","PET","FARMING",
    "TRANSLATE","TLDR","ROAST","COMPLIMENT","STORY","POEM","EMAIL","BRAINSTORM","QUIZ",
    "CONNECT4","TICTACTOE","HANGMAN","BLACKJACK","TYPERACE","ANAGRAM","WOULDYOU","NEVERHAVEIEVER",
    "TRUTH","DARE","SHIP","HOROSCOPE","JOKE","FACT","QUOTE",
    "RADIO","SOUNDBOARD","SPOTIFY","VOLUME","LOOP","SHUFFLE","SAVE_MUSIC","PLAYLIST",
    "GITHUB","TWITCH","YOUTUBE","TIMEZONE","CURRENCY_CONV","NEWS","URBAN","WIKI","IMDB","STEAM","CRYPTO","STOCK","REDDIT","XKCD",
    "REP","MARRY","PROFILE","BADGES","FRIEND","CLAN",
    "QRCODE","PASSWORD","HASH","SHORTEN","MATH","BASE64","LYRICS","MUSIC_NEW",
    "JAIL","REPORT","APPEAL","NOTEBOOK",
    "VOICE","BUTTON","BIRTHDAY","COUNTDOWN","TEMPLATE",
]

# ══════════════════════════════════════════════════════════════
#  GENERATION
# ══════════════════════════════════════════════════════════════

def _generate():
    for name in NAMES:
        entry = ICONS.get(name)
        if not entry:
            print(f"  SKIP {name} (no icon)")
            continue
        fn, theme = entry
        animated = name in ANIMATED
        if animated:
            frames = make_animated(fn, theme)
            path = EMOJI_DIR / f"{name}.gif"
            frames[0].save(path, save_all=True, append_images=frames[1:], duration=100, loop=0, disposal=2)
        else:
            img = make_emoji(fn, theme)
            path = EMOJI_DIR / f"{name}.png"
            img.save(path)
        print(f"  {name:20s} -> {path.name:25s} ({path.stat().st_size:>7}b)")

if __name__ == "__main__":
    _generate()
    print(f"\nDone! {len(NAMES)} emojis generated.")
