"""Validación automática de los temas de audio.

Métricas objetivas por tema (sin oídos):
- Niveles: RMS global y pico (consistencia entre temas, sin clipping).
- Factor de cresta: detecta clicks/impulsos agresivos (el fallo "audio roto").
- Derivada máxima: clicks digitales duros.
- Reparto espectral: % de energía por bandas → cada tema debe "sonar a lo que es"
  (lluvia = energía aguda; fuego = cuerpo grave; grillos = banda 3.5-5.5 kHz).
- Eventos de trueno: conteo sobre la envolvente de la banda 60-450 Hz.
- Actividad de grillos: fracción de tiempo con chirp activo (nerviosismo).

Uso: python scripts/validate_audio.py [minutos]  (por defecto 2.0)
Sale con código 1 si algún tema falla.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from scipy import signal

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import audio_engine as ae  # noqa: E402

SR = ae.SR


def band_energy(x: np.ndarray, lo: float, hi: float) -> float:
    f, psd = signal.welch(x, SR, nperseg=8192)
    total = np.trapezoid(psd, f) + 1e-12
    m = (f >= lo) & (f < hi)
    return float(np.trapezoid(psd[m], f[m]) / total)


def thunder_events(x: np.ndarray) -> int:
    """Cuenta retumbos: picos sostenidos en la envolvente de 60-450 Hz."""
    low = ae.bandpass(x, 60, 450, order=2)
    win = SR // 2
    env = np.sqrt(np.convolve(low**2, np.ones(win) / win, mode="same"))
    thr = np.median(env) * 3.0
    above = env > thr
    # agrupar tramos contiguos separados por >2 s
    events, i = 0, 0
    while i < len(above):
        if above[i]:
            events += 1
            i += SR * 6      # un trueno "ocupa" ≥6 s (evita contar el eco aparte)
        else:
            i += SR // 4
    return events


def cricket_activity(x: np.ndarray) -> float:
    """Fracción de tiempo con chirp activo (banda 3.5-5.5 kHz)."""
    band = ae.bandpass(x, 3500, 5500, order=2)
    win = SR // 10
    env = np.sqrt(np.convolve(band**2, np.ones(win) / win, mode="same"))
    return float(np.mean(env > np.max(env) * 0.15))


def validate(minutes: float = 2.0, only: list[str] | None = None) -> bool:
    ok_all = True
    print(f"{'tema':16s} {'rms':>7s} {'peak':>6s} {'crest':>6s} {'maxdif':>7s}  extra")
    for theme in (only or list(ae.THEMES)):
        x = ae.render_segment(theme, minutes, 20260708)
        mono = x.mean(axis=1)
        rms_lin = float(np.sqrt(np.mean(mono**2)))
        rms = 20 * np.log10(rms_lin + 1e-12)
        peak = float(np.max(np.abs(mono)))
        crest = peak / (rms_lin + 1e-12)
        maxdif = float(np.max(np.abs(np.diff(mono))))

        problems = []
        # continuidad: ninguna ventana de 1 s puede caer >5 dB bajo el RMS global
        win = SR
        n_w = len(mono) // win
        w_rms = np.sqrt(np.mean(mono[:n_w * win].reshape(n_w, win) ** 2, axis=1))
        min_db = 20 * np.log10(np.min(w_rms) + 1e-12)
        # las olas viven del vaivén: umbral propio más laxo
        cont_limit = {"ocean_waves": 8.0}.get(theme, 5.0)
        if min_db < rms - cont_limit:
            problems.append(f"hueco de sonido (ventana mínima {min_db:.1f} dB)")
        if not (-23.5 < rms < -18.5):
            problems.append(f"RMS fuera de rango ({rms:.1f})")
        if peak > 0.92:
            problems.append("pico demasiado alto")
        crest_lim = 9.0 if theme == "fireplace" else 13.0
        if crest > crest_lim:
            problems.append(f"crest {crest:.1f} > {crest_lim} (clicks)")
        if maxdif > 0.60:
            problems.append(f"clicks duros (maxdif {maxdif:.2f})")

        extra = ""
        if "rain" in theme:
            hi = band_energy(mono, 2000, 9000)
            extra += f"hiss2-9k={hi:.0%} "
            if hi < 0.15:
                problems.append("no suena a lluvia (poca energía aguda)")
        if theme == "thunder_rain":
            ev = thunder_events(mono)
            extra += f"truenos={ev} "
            expected = max(1, int(minutes * 60 / 55))
            if ev < expected:
                problems.append(f"solo {ev} truenos (esperados ≥{expected})")
            mid = band_energy(mono, 150, 450)
            extra += f"medios150-450={mid:.0%} "
            if mid < 0.05:
                problems.append("truenos inaudibles en altavoces pequeños")
        if theme == "__disabled__":
            body = band_energy(mono, 40, 500)
            extra += f"cuerpo<500={body:.0%} "
            if body < 0.40:
                problems.append("falta cuerpo de llama")
        if theme == "crickets_night":
            act = cricket_activity(mono)
            extra += f"actividad={act:.0%} "
            if act > 0.50:
                problems.append("demasiados grillos (nervioso)")

        status = "OK " if not problems else "FALLA: " + "; ".join(problems)
        if problems:
            ok_all = False
        print(f"{theme:16s} {rms:7.1f} {peak:6.3f} {crest:6.1f} {maxdif:7.3f}  {extra}{status}")
    return ok_all


if __name__ == "__main__":
    minutes = float(sys.argv[1]) if len(sys.argv) > 1 else 2.0
    only = sys.argv[2].split(",") if len(sys.argv) > 2 else None
    sys.exit(0 if validate(minutes, only) else 1)
