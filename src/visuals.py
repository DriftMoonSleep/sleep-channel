"""Generador procedural de escenas nocturnas (imagen del vídeo + miniatura).

PIL puro: cada vídeo obtiene una imagen única (paleta, luna, estrellas,
montañas, niebla) derivada de la semilla del día.
"""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1920, 1080

PALETTES = [
    # (cielo arriba, cielo horizonte, acento luna)
    ((8, 10, 28), (40, 48, 92), (235, 235, 210)),
    ((6, 14, 24), (26, 70, 88), (220, 240, 235)),
    ((14, 8, 30), (88, 44, 84), (245, 225, 200)),
    ((4, 6, 18), (30, 34, 60), (200, 215, 245)),
    ((10, 16, 26), (52, 80, 96), (230, 230, 230)),
    ((16, 10, 22), (96, 60, 60), (250, 230, 205)),
]

THEME_WORDS = {
    "gentle_rain":   ("RAIN", "Lluvia suave"),
    "ocean_waves":   ("OCEAN", "Olas del mar"),
    "deep_brown":    ("BROWN NOISE", "Ruido marrón"),
    "night_wind":    ("WIND", "Viento nocturno"),
    "dream_pads":    ("AMBIENT", "Ambient onírico"),
    "rain_and_pads": ("RAIN + AMBIENT", "Lluvia y ambient"),
    "thunder_rain": ("RAIN & THUNDER", "Lluvia y truenos"),
    "wind_drizzle": ("WIND & RAIN", "Viento y llovizna"),
    "light_rain": ("LIGHT RAIN", "Llovizna"),
    "crickets_night": ("NIGHT CRICKETS", "Grillos nocturnos"),
}


def _lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _sky(draw: ImageDraw.ImageDraw, top, bottom, horizon: int):
    for y in range(H):
        t = min(y / max(horizon, 1), 1.0)
        draw.line([(0, y), (W, y)], fill=_lerp(top, bottom, t ** 1.3))


def _stars(img: Image.Image, rng: np.random.Generator, horizon: int):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for _ in range(int(rng.integers(140, 320))):
        x = int(rng.integers(0, W))
        y = int(rng.integers(0, int(horizon * 0.92)))
        r = float(rng.uniform(0.5, 1.9))
        a = int(rng.integers(70, 220))
        d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 245, a))
    img.alpha_composite(layer.filter(ImageFilter.GaussianBlur(0.6)))


def _moon(img: Image.Image, rng: np.random.Generator, color, horizon: int):
    x = int(rng.uniform(W * 0.12, W * 0.88))
    y = int(rng.uniform(H * 0.10, horizon * 0.5))
    r = int(rng.uniform(46, 90))
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(glow)
    for gr, ga in ((r * 3.2, 22), (r * 2.2, 38), (r * 1.5, 60)):
        d.ellipse([x - gr, y - gr, x + gr, y + gr], fill=color + (ga,))
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(18)))
    d2 = ImageDraw.Draw(img)
    d2.ellipse([x - r, y - r, x + r, y + r], fill=color + (255,))


def _mountains(img: Image.Image, rng: np.random.Generator, horizon: int, base_color):
    for layer_i in range(2):
        pts = [(0, H)]
        y0 = horizon - int(rng.uniform(10, 70)) + layer_i * 55
        x = 0
        y = y0 + int(rng.uniform(-30, 30))
        while x < W:
            x += int(rng.uniform(90, 260))
            y = int(np.clip(y + rng.uniform(-90, 90), y0 - 130, y0 + 60))
            pts.append((x, y))
        pts.append((W, H))
        shade = max(2, 8 - layer_i * 3)
        c = tuple(int(v * shade / 24) for v in base_color)
        ImageDraw.Draw(img).polygon(pts, fill=c + (255,))


def _water(img: Image.Image, horizon: int):
    sky = img.crop((0, 0, W, horizon)).transpose(Image.FLIP_TOP_BOTTOM)
    sky = sky.resize((W, H - horizon))
    sky = sky.filter(ImageFilter.GaussianBlur(3))
    dark = Image.new("RGBA", sky.size, (0, 0, 20, 110))
    sky.alpha_composite(dark)
    img.paste(sky, (0, horizon))


def _mist(img: Image.Image, rng: np.random.Generator, horizon: int):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for _ in range(int(rng.integers(4, 9))):
        cx = rng.uniform(0, W)
        cy = rng.uniform(horizon - 60, min(horizon + 160, H - 20))
        rx = rng.uniform(240, 640)
        ry = rng.uniform(18, 60)
        d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=(210, 220, 235, 16))
    img.alpha_composite(layer.filter(ImageFilter.GaussianBlur(24)))


def _grain(img: Image.Image, rng: np.random.Generator):
    g = rng.integers(-7, 8, size=(H, W, 1), dtype=np.int16)
    arr = np.asarray(img.convert("RGB"), dtype=np.int16) + g
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")


def render_scene(seed: int, theme: str) -> Image.Image:
    rng = np.random.default_rng(seed)
    top, bottom, accent = PALETTES[int(rng.integers(0, len(PALETTES)))]
    horizon = int(H * rng.uniform(0.58, 0.72))
    img = Image.new("RGBA", (W, H))
    _sky(ImageDraw.Draw(img), top, bottom, horizon)
    _stars(img, rng, horizon)
    _moon(img, rng, accent, horizon)
    water = theme == "ocean_waves" or rng.random() < 0.35
    if water:
        _water(img, horizon)
    _mountains(img, rng, horizon, bottom)
    _mist(img, rng, horizon)
    return _grain(img, rng)


def _font(size: int) -> ImageFont.FreeTypeFont:
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
    ):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def render_thumbnail(scene: Image.Image, hours: int, theme: str, lang: str = "en",
                     channel_name: str = "", seed: int = 0) -> Image.Image:
    """Tres layouts distintos elegidos por semilla: las miniaturas con estructura
    casi idéntica son una de las señales de la detección de contenido en masa."""
    rng = np.random.default_rng(seed + 424242)
    layout = int(rng.integers(0, 3))
    th = scene.resize((1280, 720))
    d = ImageDraw.Draw(th, "RGBA")
    word = THEME_WORDS[theme][0] if lang == "en" else THEME_WORDS[theme][1].upper()
    line1 = f"{hours} HOURS" if lang == "en" else f"{hours} HORAS"
    accent = tuple(int(v) for v in rng.choice(
        [(180, 215, 255), (255, 214, 165), (198, 255, 221), (230, 200, 255)]))

    def _text(x, y, text, font, fill=(255, 255, 255)):
        d.text((x + 3, y + 3), text, font=font, fill=(0, 0, 0))
        d.text((x, y), text, font=font, fill=fill)

    def _center(text, font, y, fill=(255, 255, 255)):
        _text((1280 - d.textlength(text, font=font)) / 2, y, text, font, fill)

    if layout == 0:      # banda inferior, texto centrado
        d.rectangle([0, 430, 1280, 720], fill=(0, 0, 0, 110))
        _center(line1, _font(130), 455)
        _center(word, _font(72), 605, fill=accent)
        brand_pos = (24, 20)
    elif layout == 1:    # bloque arriba-izquierda
        d.rectangle([0, 0, 1280, 300], fill=(0, 0, 0, 90))
        _text(48, 40, line1, _font(110))
        _text(50, 178, word, _font(64), fill=accent)
        brand_pos = (48, 660)
    else:                # palabra grande abajo + chip de horas arriba-dcha
        d.rectangle([0, 500, 1280, 720], fill=(0, 0, 0, 120))
        _center(word, _font(105), 540, fill=(255, 255, 255))
        chip = f"{hours}H"
        f_ch = _font(64)
        w_ch = d.textlength(chip, font=f_ch)
        d.rounded_rectangle([1280 - w_ch - 72, 32, 1280 - 24, 128], 18,
                            fill=(0, 0, 0, 150))
        _text(1280 - w_ch - 48, 44, chip, f_ch, fill=accent)
        brand_pos = (24, 20)

    if channel_name:
        _text(brand_pos[0], brand_pos[1], channel_name.upper(), _font(30),
              fill=(235, 235, 225))
    return th
