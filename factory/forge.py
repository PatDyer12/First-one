"""Forge: renders print-ready typography designs (transparent PNG, 4500x5400 = 15x18in @ 300dpi)."""
import base64
import io
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONTS = Path(__file__).parent / "fonts"
STYLE_FONTS = {
    "retro": "AbrilFatface-Regular.ttf",
    "bold": "BebasNeue-Regular.ttf",
    "script": "Pacifico-Regular.ttf",
}
# (ink, accent) pairs that read well on white / natural / light-heather shirts
PALETTES = [
    ("#2b2b2b", "#c8553d"),
    ("#1f3a5f", "#e0a458"),
    ("#3d405b", "#e07a5f"),
    ("#283618", "#bc6c25"),
    ("#4a2c2a", "#d98f8f"),
]
W, H = 4500, 5400


def _font(style, size):
    return ImageFont.truetype(str(FONTS / STYLE_FONTS.get(style, STYLE_FONTS["retro"])), size)


def render(concept, out_path, seed=None):
    rng = random.Random(seed)
    ink, accent = rng.choice(PALETTES)
    lines, style = concept["lines"], concept["style"]

    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    max_w = int(W * 0.86)

    # Size each line to fill the width (accent line bigger), capped so tall stacks still fit.
    fitted = []
    for i, text in enumerate(lines):
        font_style = "script" if style == "script" and i == concept["accent_line"] else ("retro" if style == "script" else style)
        size = 1400 if i == concept["accent_line"] else 900
        while size > 120:
            font = _font(font_style, size)
            l, t, r, b = draw.textbbox((0, 0), text, font=font)
            if r - l <= max_w:
                break
            size -= 20
        fitted.append((text, font, (l, t, r, b), accent if i == concept["accent_line"] else ink))

    gap = 110
    total = sum(b[3] - b[1] for _, _, b, _ in fitted) + gap * (len(fitted) - 1)
    scale = min(1.0, H * 0.8 / total)
    if scale < 1.0:  # re-fit smaller if the stack is too tall
        fitted = [(t, f.font_variant(size=int(f.size * scale)), None, c) for t, f, _, c in fitted]
        fitted = [(t, f, draw.textbbox((0, 0), t, font=f), c) for t, f, _, c in fitted]
        gap = int(gap * scale)
        total = sum(b[3] - b[1] for _, _, b, _ in fitted) + gap * (len(fitted) - 1)

    y = 260  # sit high on the chest like most tees
    for text, font, (l, t, r, b), color in fitted:
        draw.text(((W - (r - l)) / 2 - l, y - t), text, font=font, fill=color)
        y += (b - t) + gap

    # small rule + stars under the stack for a finished look
    y += 60
    draw.line([(W * 0.3, y), (W * 0.7, y)], fill=ink, width=28)
    for dx in (-0.12, 0, 0.12):
        _star(draw, W * (0.5 + dx), y + 190, 70, accent)

    img = img.crop((0, 0, W, min(H, int(y + 400))))
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    canvas.paste(img, (0, 0))
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_path, optimize=True)
    return out_path


def _star(draw, cx, cy, r, color):
    import math
    pts = []
    for k in range(10):
        rad = r if k % 2 == 0 else r * 0.45
        a = math.pi / 2 + k * math.pi / 5
        pts.append((cx + rad * math.cos(a), cy - rad * math.sin(a)))
    draw.polygon(pts, fill=color)


def thumbnail(design_path, shirt="#f4efe6", size=360):
    """Small shirt-colored preview as a data URI for the dashboard."""
    design = Image.open(design_path)
    bg = Image.new("RGBA", design.size, shirt)
    bg.alpha_composite(design)
    bg = bg.convert("RGB")
    bg.thumbnail((size, size * H // W))
    buf = io.BytesIO()
    bg.save(buf, "JPEG", quality=78)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
