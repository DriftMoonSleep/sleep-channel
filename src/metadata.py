"""Títulos, descripciones y tags con variación combinatoria por semilla.

Sin LLM: pools de plantillas → coste 0 y sin dependencia de otra API.
La variación real por vídeo (título, texto, tags, imagen, audio) es también
la defensa frente a la política de "contenido inauténtico" de YouTube.
"""
from __future__ import annotations

import numpy as np

THEME_NAMES = {
    "en": {
        "gentle_rain": "Gentle Rain Sounds",
        "ocean_waves": "Ocean Waves",
        "deep_brown": "Deep Brown Noise",
        "night_wind": "Night Wind Sounds",
        "dream_pads": "Dreamy Ambient Music",
        "rain_and_pads": "Rain & Ambient Music",
    },
    "es": {
        "gentle_rain": "Sonido de Lluvia Suave",
        "ocean_waves": "Olas del Mar",
        "deep_brown": "Ruido Marrón Profundo",
        "night_wind": "Viento Nocturno",
        "dream_pads": "Música Ambient para Soñar",
        "rain_and_pads": "Lluvia y Música Ambient",
    },
}

BENEFITS = {
    "en": ["Fall Asleep Fast", "Deep Sleep", "Insomnia Relief", "Calm Your Mind",
           "Relax & Sleep", "Stress Relief", "Sleep Through the Night", "Study & Focus"],
    "es": ["Duerme Profundamente", "Contra el Insomnio", "Calma tu Mente",
           "Relájate y Duerme", "Adiós al Estrés", "Descanso Total", "Concentración y Calma"],
}

DESC_INTRO = {
    "en": [
        "Tonight, let {theme_l} carry you into deep, restful sleep.",
        "Close your eyes and drift away with {hours} hours of {theme_l}.",
        "Soothing {theme_l} designed to quiet a racing mind at bedtime.",
        "Put this on, dim the lights, and let sleep come naturally.",
    ],
    "es": [
        "Esta noche, deja que {theme_l} te lleve a un sueño profundo y reparador.",
        "Cierra los ojos y déjate llevar por {hours} horas de {theme_l}.",
        "{theme_l} pensado para calmar la mente antes de dormir.",
        "Pon este sonido, baja las luces y deja que el sueño llegue solo.",
    ],
}

DESC_BODY = {
    "en": [
        "Ideal for sleeping, relaxing, studying, meditation or masking background noise.",
        "Perfect as white-noise style masking for light sleepers, babies' rooms or night shifts.",
        "Use it for bedtime routines, naps, reading or deep-focus work sessions.",
    ],
    "es": [
        "Ideal para dormir, relajarse, estudiar, meditar o tapar ruidos de fondo.",
        "Perfecto para personas de sueño ligero, siestas o turnos de noche.",
        "Úsalo en tu rutina de sueño, para leer o para sesiones de concentración.",
    ],
}

DISCLOSURE = {
    "en": "Audio and artwork in this video are original and algorithmically generated for this channel.",
    "es": "El audio y la imagen de este vídeo son originales, generados algorítmicamente para este canal.",
}

TAG_POOL = {
    "en": ["sleep sounds", "relaxing sounds", "deep sleep", "insomnia relief", "white noise",
           "brown noise", "rain sounds for sleeping", "ocean sounds", "ambient sleep music",
           "calm music", "sleep meditation", "study sounds", "asmr sleep", "8 hours sleep",
           "relaxation", "stress relief", "nature sounds", "fall asleep fast"],
    "es": ["sonidos para dormir", "sonidos relajantes", "sueño profundo", "insomnio",
           "ruido blanco", "ruido marrón", "lluvia para dormir", "olas del mar",
           "música ambiental para dormir", "música relajante", "meditación para dormir",
           "sonidos de la naturaleza", "dormir rápido", "relajación", "8 horas"],
}


def _chapters(theme_name: str, hours: int, black_min: int, lang: str) -> str:
    """Capítulos honestos (≥3 marcas → YouTube los muestra). Señal anti-plantilla."""
    half = max(hours // 2, 1)
    if lang == "en":
        lines = [f"0:00 {theme_name} begins"]
        if black_min:
            lines.append(f"{black_min}:00 Screen fades to black")
        lines += [f"{half}:00:00 Deep sleep continues",
                  f"{hours}:00:00 End"]
    else:
        lines = [f"0:00 Comienza: {theme_name.lower()}"]
        if black_min:
            lines.append(f"{black_min}:00 La pantalla se funde a negro")
        lines += [f"{half}:00:00 Sueño profundo", f"{hours}:00:00 Fin"]
    return "\n".join(lines)


def build_metadata(theme: str, hours: int, seed: int, lang: str = "en",
                   channel_name: str = "", black_screen_min: int = 0) -> dict:
    rng = np.random.default_rng(seed + 7919)
    name = THEME_NAMES[lang][theme]
    benefit = str(rng.choice(BENEFITS[lang]))
    sep = str(rng.choice(["|", "•", "–"]))
    if lang == "en":
        title = f"{hours} Hours of {name} for {benefit} {sep} Sleep Sounds"
    else:
        title = f"{hours} Horas de {name} {sep} {benefit}"
    if black_screen_min:
        bs_label = str(rng.choice(["Black Screen", "Dark Screen"])) if lang == "en" \
            else "Pantalla Negra"
        title = f"{title[:80].rstrip()} ({bs_label})"

    theme_l = name.lower()
    intro = str(rng.choice(DESC_INTRO[lang])).format(theme_l=theme_l, hours=hours)
    body = str(rng.choice(DESC_BODY[lang]))
    chapters = _chapters(name, hours, black_screen_min, lang)
    signature = ""
    if channel_name:
        signature = (f"🌙 {channel_name} — new original sleep soundscapes every week. "
                     "Subscribe so tonight's sound is easy to find."
                     if lang == "en" else
                     f"🌙 {channel_name} — nuevos paisajes sonoros para dormir cada semana.")
    parts = [intro, body, chapters, signature, DISCLOSURE[lang]]
    description = "\n\n".join(p for p in parts if p)

    tags = list(rng.choice(TAG_POOL[lang], size=min(12, len(TAG_POOL[lang])), replace=False))
    tags.insert(0, theme_l)
    if black_screen_min:
        tags.append("black screen" if lang == "en" else "pantalla negra")
    return {"title": title[:99], "description": description, "tags": tags}
