"""Genera el branding completo de Driftmoon Sleep en ./branding/:

- avatar_800.png       (foto de perfil del canal, 800x800)
- banner_2048x1152.png (cabecera; contenido crítico dentro de la zona segura 1235x338)
- watermark_150.png    (marca de agua de vídeos, PNG transparente)
- thumb_example_*.jpg  (3 miniaturas de ejemplo con los 3 layouts)
- about.txt            (textos para la pestaña "Información" del canal)

Se ejecuta con el workflow "Generar branding" y se descarga como artifact.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

CHANNEL = "DRIFTMOON SLEEP"
TAGLINE = "Rain · Ocean · Deep-Sleep Soundscapes"

# Paleta de marca
BG_TOP = (10, 12, 40)
BG_BOT = (26, 32, 82)
CREAM = (242, 239, 216)
LAVENDER = (150, 165, 220)
WAVE_COLORS = [(139, 155, 217), (109, 127, 196), (85, 101, 159)]

OUT = Path("branding")


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


def _gradient(w: int, h: int) -> Image.Image:
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / h
        c = tuple(int(BG_TOP[i] + (BG_BOT[i] - BG_TOP[i]) * t) for i in range(3))
        d.line([(0, y), (w, y)], fill=c)
    return img


def _stars(img: Image.Image, n: int, seed: int = 7):
    import random
    rnd = random.Random(seed)
    d = ImageDraw.Draw(img, "RGBA")
    w, h = img.size
    for _ in range(n):
        x, y = rnd.uniform(0, w), rnd.uniform(0, h)
        r = rnd.uniform(0.6, 2.2)
        a = rnd.randint(60, 200)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 245, a))


def _crescent(size: int) -> Image.Image:
    """Luna creciente con halo, en capa RGBA transparente de `size` px."""
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    # halo
    glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    c, r = size // 2, int(size * 0.32)
    # radios contenidos en la capa: si el halo toca el borde, el blur
    # deja un rectángulo visible al componer sobre el gradiente
    for gr, ga in ((r * 1.38, 26), (r * 1.16, 48)):
        gd.ellipse([c - gr, c - gr, c + gr, c + gr], fill=CREAM + (ga,))
    layer.alpha_composite(glow.filter(ImageFilter.GaussianBlur(size // 16)))
    # creciente por máscara (círculo lleno menos círculo desplazado)
    mask = Image.new("L", (size, size), 0)
    md = ImageDraw.Draw(mask)
    md.ellipse([c - r, c - r, c + r, c + r], fill=255)
    off = int(r * 0.55)
    md.ellipse([c - r + off, c - r - off // 2, c + r + off, c + r - off // 2], fill=0)
    moon = Image.new("RGBA", (size, size), CREAM + (255,))
    layer.paste(moon, (0, 0), mask)
    return layer


def _waves(d: ImageDraw.ImageDraw, cx: int, cy: int, w: int):
    """Tres arcos suaves bajo la luna: la 'deriva' de Driftmoon."""
    for i, col in enumerate(WAVE_COLORS):
        rw = w * (1 + i * 0.45)
        rh = rw * 0.36
        y = cy + i * (w * 0.17)
        d.arc([cx - rw / 2, y - rh / 2, cx + rw / 2, y + rh / 2],
              start=200, end=340, fill=col, width=max(6, int(w * 0.055)))


def avatar():
    S = 800
    img = _gradient(S, S)
    _stars(img, 90, seed=11)
    img = img.convert("RGBA")
    img.alpha_composite(_crescent(560), ((S - 560) // 2, 60))
    _waves(ImageDraw.Draw(img), S // 2, 585, 300)
    # viñeta sutil
    vig = Image.new("L", (S, S), 0)
    ImageDraw.Draw(vig).ellipse([-S * 0.25, -S * 0.25, S * 1.25, S * 1.25], fill=255)
    vig = vig.filter(ImageFilter.GaussianBlur(120))
    black = Image.new("RGBA", (S, S), (0, 0, 10, 255))
    img = Image.composite(img, black, vig)
    img.convert("RGB").save(OUT / "avatar_800.png")


def _spaced_text(d, x, y, text, font, fill, tracking=6):
    for ch in text:
        d.text((x + 3, y + 3), ch, font=font, fill=(0, 0, 0, 160))
        d.text((x, y), ch, font=font, fill=fill)
        x += d.textlength(ch, font=font) + tracking
    return x


def _spaced_width(d, text, font, tracking=6):
    return sum(d.textlength(ch, font=font) + tracking for ch in text) - tracking


def banner():
    W, H = 2048, 1152
    img = _gradient(W, H).convert("RGBA")
    _stars(img, 260, seed=23)
    d = ImageDraw.Draw(img, "RGBA")

    # Zona segura (visible en todos los dispositivos): 1235x338 centrada
    # → todo el lockup debe caber en x∈[406,1641], y∈[407,745]
    f1, f2 = _font(76), _font(36)
    moon = _crescent(170)
    tw = _spaced_width(d, CHANNEL, f1, tracking=8)
    block_w = 170 + 34 + tw
    x0 = (W - block_w) / 2
    img.alpha_composite(moon, (int(x0), int(H / 2 - 118)))
    _spaced_text(d, x0 + 204, H / 2 - 62, CHANNEL, f1, CREAM, tracking=8)
    tag_w = d.textlength(TAGLINE, font=f2)
    d.text((int((W - tag_w) / 2) + 2, int(H / 2 + 38) + 2), TAGLINE,
           font=f2, fill=(0, 0, 0, 160))
    d.text((int((W - tag_w) / 2), int(H / 2 + 38)), TAGLINE, font=f2, fill=LAVENDER)
    img.convert("RGB").save(OUT / "banner_2048x1152.png")


def watermark():
    S = 150
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    img.alpha_composite(_crescent(150), (0, 0))
    img.save(OUT / "watermark_150.png")


def thumbnails():
    from src import visuals
    for i, (seed, theme, hours) in enumerate(
        [(20260101, "gentle_rain", 8), (20260102, "ocean_waves", 3),
         (20260103, "dream_pads", 10)]
    ):
        scene = visuals.render_scene(seed, theme)
        th = visuals.render_thumbnail(scene, hours, theme, "en",
                                      "Driftmoon Sleep", seed)
        th.convert("RGB").save(OUT / f"thumb_example_{i + 1}.jpg", quality=88)


def about():
    (OUT / "about.txt").write_text(
        "=== YouTube > Personalización > Información ===\n\n"
        "🌙 Driftmoon Sleep | Rain, Ocean & Deep-Sleep Soundscapes\n\n"
        "Original sleep soundscapes, crafted fresh for every video — gentle rain, "
        "ocean waves, deep brown noise, night wind and dreamy ambient drones.\n\n"
        "Designed to help you:\n"
        "• Fall asleep faster and stay asleep\n"
        "• Calm a racing mind at bedtime\n"
        "• Mask background noise (light sleepers, night shifts, city apartments)\n"
        "• Focus while studying or working\n\n"
        "Every soundscape and artwork on this channel is original and "
        "algorithmically crafted for Driftmoon Sleep. New videos every week.\n"
        "Press play, dim the lights, and drift off. 🌧🌊\n\n"
        "Contact: driftmoonsleep@gmail.com\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    avatar()
    banner()
    watermark()
    thumbnails()
    about()
    print("Branding generado en ./branding/:")
 