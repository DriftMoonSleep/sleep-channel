"""Pipeline diario: audio → imagen → metadata → vídeo → subida.

Determinista por fecha: la misma fecha produce el mismo vídeo (reintentos
seguros), y cada fecha produce tema/duración/paleta/textos distintos.
"""
from __future__ import annotations

import datetime as dt
import os
import sys
from pathlib import Path

import yaml

from . import audio_engine, metadata, render, visuals


def main():
    cfg = yaml.safe_load(Path("config.yaml").read_text(encoding="utf-8"))
    today = dt.date.today()
    seed = int(today.strftime("%Y%m%d")) + int(cfg.get("seed_salt", 0))

    themes = cfg["themes"]
    theme = os.environ.get("THEME_OVERRIDE") or themes[today.toordinal() % len(themes)]
    hours_pool = cfg["hours_pool"]
    hours = int(os.environ.get("HOURS_OVERRIDE") or hours_pool[today.toordinal() % len(hours_pool)])
    lang = cfg.get("language", "en")

    work = Path("out")
    work.mkdir(exist_ok=True)

    print(f"[1/5] Audio: tema={theme}, segmento={cfg['segment_minutes']} min")
    audio = audio_engine.render_segment(theme, cfg["segment_minutes"], seed)

    print("[2/5] Codificando y loopeando audio")
    seg = render.encode_segment(audio, work)
    del audio
    full_audio = render.loop_audio(seg, hours, work)

    print("[3/5] Imagen y miniatura")
    scene = visuals.render_scene(seed, theme)
    img_path = work / "scene.png"
    scene.convert("RGB").save(img_path)
    thumb_path = work / "thumb.jpg"
    channel_name = cfg.get("channel_name", "")
    visuals.render_thumbnail(scene, hours, theme, lang, channel_name,
                             seed).convert("RGB").save(thumb_path, quality=88)

    print("[4/5] Renderizando vídeo")
    black_min = int(cfg.get("black_screen_minutes", 0) or 0)
    fade_start = black_min * 60 if 0 < black_min * 60 < hours * 3600 else 0
    video = render.make_video(img_path, full_audio, work / "video.mp4",
                              fade_start_sec=fade_start)

    meta = metadata.build_metadata(theme, hours, seed, lang,
                                   channel_name, black_min)
    print(f"      título: {meta['title']}")

    if os.environ.get("SKIP_UPLOAD") == "1":
        print("[5/5] SKIP_UPLOAD=1 → no se sube (modo prueba)")
        return

    print("[5/5] Subiendo a YouTube")
    from .upload import upload_video  # import tardío: no exige credenciales en pruebas
    upload_url = upload_video(video, thumb_path, meta,
                              privacy=cfg.get("privacy_status", "private"), lang=lang)
    print(f"      publicado: {upload_url}")

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write(f"## Vídeo de hoy\n- **{meta['title']}**\n- {upload_url}\n"
                    f"- tema `{theme}`, {hours} h\n")


if __name__ == "__main__":
    sys.exit(main())
