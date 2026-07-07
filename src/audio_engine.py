"""Motor de audio procedural para contenido de sueño/relajación.

Genera un segmento loopeable (sin costura audible) que luego se repite
hasta la duración objetivo del vídeo. Todo es síntesis matemática:
sin muestras externas, sin copyright, coste cero.

Temas: lluvia, ruido marrón, olas, viento, pads ambient, lluvia+pads,
lluvia+truenos, chimenea, lluvia+chimenea, grillos nocturnos.
"""
from __future__ import annotations

import numpy as np
from scipy import signal

SR = 44100


# ----------------------------------------------------------------------
# Utilidades
# ----------------------------------------------------------------------
def _norm(x: np.ndarray, rms_db: float = -20.0) -> np.ndarray:
    rms = np.sqrt(np.mean(x**2)) + 1e-12
    x = x * (10 ** (rms_db / 20) / rms)
    return x.astype(np.float32)


def _sos(kind: str, cutoff, order: int = 4):
    return signal.butter(order, cutoff, kind, fs=SR, output="sos")


def lowpass(x, cutoff, order=4):
    return signal.sosfilt(_sos("low", cutoff, order), x).astype(np.float32)


def highpass(x, cutoff, order=2):
    return signal.sosfilt(_sos("high", cutoff, order), x).astype(np.float32)


def bandpass(x, lo, hi, order=2):
    return signal.sosfilt(_sos("band", [lo, hi], order), x).astype(np.float32)


def _white(n: int, rng: np.random.Generator) -> np.ndarray:
    return rng.standard_normal(n).astype(np.float32)


def _slow_env(n: int, rng: np.random.Generator, hz: float, floor: float = 0.0) -> np.ndarray:
    """Envolvente lenta y orgánica en [floor, 1].

    Se genera a 50 Hz y se interpola: filtrar a 0.02-0.1 Hz directamente a
    44100 Hz produce filtros numéricamente inestables.
    """
    lo_sr = 50.0
    m = max(int(n / SR * lo_sr) + 2, 8)
    w = rng.standard_normal(m)
    sos = signal.butter(2, min(hz, lo_sr / 4), "low", fs=lo_sr, output="sos")
    e = signal.sosfilt(sos, w)
    e = e - e.min()
    e = e / (e.max() + 1e-9)
    out = np.interp(np.arange(n), np.linspace(0, n, m), e)
    return (floor + (1 - floor) * out).astype(np.float32)


# ----------------------------------------------------------------------
# Capas base
# ----------------------------------------------------------------------
def brown_noise(n: int, rng: np.random.Generator) -> np.ndarray:
    """Ruido marrón profundo (integrador con fugas, sin deriva DC)."""
    w = _white(n, rng)
    b = signal.lfilter([1.0], [1.0, -0.999], w)  # ~7 Hz de esquina
    b = highpass(b, 25)
    b = lowpass(b, 450)
    return _norm(b)


def rain(n: int, rng: np.random.Generator) -> np.ndarray:
    """Lluvia: lecho de ruido + gotas individuales dispersas."""
    bed_hi = bandpass(_white(n, rng), 1500, 9000) * 0.95      # hiss = carácter lluvia
    bed_lo = bandpass(_white(n, rng), 150, 700) * 0.40         # cuerpo/rumor
    bed = bed_hi + bed_lo
    bed *= _slow_env(n, rng, 0.05, floor=0.75)                 # intensidad variable

    drops = np.zeros(n, dtype=np.float32)
    rate = rng.uniform(12, 20)                                 # gotas audibles/seg
    k = int(n / SR * rate)
    for _ in range(k):
        dur = int(SR * rng.uniform(0.004, 0.03))
        i = rng.integers(0, n - dur)
        t = np.arange(dur, dtype=np.float32)
        env = np.exp(-t / (dur * rng.uniform(0.15, 0.4)))
        burst = rng.standard_normal(dur).astype(np.float32) * env
        lo = rng.uniform(2000, 5000)
        burst = bandpass(burst, lo, min(lo * rng.uniform(1.5, 2.5), 15000), order=1)
        drops[i:i + dur] += burst * rng.uniform(0.15, 0.7)

    return _norm(bed + drops * 1.1)


def ocean(n: int, rng: np.random.Generator) -> np.ndarray:
    """Olas: ruido con envolventes lentas + rompiente esporádica."""
    base = lowpass(_white(n, rng), 900)
    swell = _slow_env(n, rng, rng.uniform(0.06, 0.11), floor=0.25) ** 1.6
    wash = bandpass(_white(n, rng), 800, 4000)
    crash_env = np.clip(swell - 0.55, 0, None) * 2.2           # solo en las crestas
    x = base * swell + wash * crash_env
    return _norm(x)


def wind(n: int, rng: np.random.Generator) -> np.ndarray:
    """Viento: ruido grave modulado + silbido suave errante."""
    body = lowpass(_white(n, rng), 500) * _slow_env(n, rng, 0.035, floor=0.35)
    w1 = bandpass(_white(n, rng), 550, 850, order=2)
    w2 = bandpass(_white(n, rng), 900, 1400, order=2)
    m = _slow_env(n, rng, 0.02)
    whistle = (w1 * m + w2 * (1 - m)) * _slow_env(n, rng, 0.05, floor=0.1) * 0.35
    return _norm(body + whistle)


# Acordes consonantes (semitonos sobre la raíz) — sin tensiones que despierten
_CHORDS = [
    (0, 7, 12, 19),        # raíz + quintas
    (0, 7, 12, 16),        # mayor
    (0, 7, 12, 14),        # add9 abierto
    (0, 5, 12, 17),        # cuartal suave
    (-12, 0, 7, 16),       # mayor con bajo
    (0, 3, 7, 12),         # menor
    (0, 3, 10, 12),        # menor 7 abierto
]


def pads(n: int, rng: np.random.Generator) -> np.ndarray:
    """Drone armónico lento: voces desafinadas + sub-drone + shimmer + reverb."""
    root = rng.uniform(98.0, 165.0)          # G2..E3 aprox
    seq_len = rng.integers(2, 5)
    seq = [_CHORDS[rng.integers(0, len(_CHORDS))] for _ in range(seq_len)]
    hold = rng.uniform(35, 55)               # seg por acorde
    xf = 10.0                                # crossfade entre acordes

    t = np.arange(n, dtype=np.float64) / SR
    out = np.zeros(n, dtype=np.float32)
    total = hold * seq_len
    for ci, chord in enumerate(seq):
        pos = (t - ci * hold) % total
        env = np.clip(np.minimum(pos / xf, (hold + xf - pos) / xf), 0, 1)
        env = (env ** 2).astype(np.float32)
        for st in chord:
            f = root * 2 ** (st / 12)
            for det in (1.0, 1.0 + rng.uniform(0.001, 0.002), 1.0 - rng.uniform(0.001, 0.002)):
                ph = rng.uniform(0, 2 * np.pi)
                v = np.sin(2 * np.pi * f * det * t + ph)
                v += 0.30 * np.sin(2 * np.pi * 2 * f * det * t + ph)
                v += 0.10 * np.sin(2 * np.pi * 3 * f * det * t + ph)
                v += 0.05 * np.sin(2 * np.pi * 4 * f * det * t + ph)   # shimmer
                trem = 1 + 0.12 * np.sin(2 * np.pi * rng.uniform(0.05, 0.09) * t + rng.uniform(0, 6.28))
                out += (v * trem).astype(np.float32) * env * (0.9 / (len(chord) * 3))

    # Sub-drone continuo una octava por debajo de la raíz
    out += (0.20 * np.sin(2 * np.pi * (root / 2) * t)).astype(np.float32)

    # Reverb: convolución con IR exponencial sintética
    ir_len = int(SR * 2.8)
    ir = rng.standard_normal(ir_len).astype(np.float32) * np.exp(
        -np.arange(ir_len, dtype=np.float32) / (SR * 0.9)
    )
    ir /= np.sqrt(np.sum(ir**2)) + 1e-9
    wet = signal.oaconvolve(out, ir)[:n].astype(np.float32)
    return _norm(out * 0.5 + wet * 0.5)


# ----------------------------------------------------------------------
# Capas nuevas (2026-07-07)
# ----------------------------------------------------------------------
def thunder(n: int, rng: np.random.Generator) -> np.ndarray:
    """Truenos lejanos: retumbo con cuerpo en medios (audible en cualquier
    altavoz), chasquido inicial y eco rodante. Capa de eventos sin normalizar."""
    out = np.zeros(n, dtype=np.float32)

    def _one_rumble(dur: int, brightness: float) -> np.ndarray:
        tt = np.arange(dur, dtype=np.float32)
        attack = 1 - np.exp(-tt / (SR * rng.uniform(0.06, 0.25)))
        decay = np.exp(-tt / (dur * rng.uniform(0.20, 0.32)))
        low = lowpass(rng.standard_normal(dur).astype(np.float32),
                      rng.uniform(70, 130))
        mid = bandpass(rng.standard_normal(dur).astype(np.float32),
                       150, 450, order=2)
        r = (low + mid * brightness) * attack * decay
        return _norm(r, -13)

    t_pos = rng.uniform(8, 25) * SR
    while t_pos < n - SR * 16:
        i = int(t_pos)
        dur = int(SR * rng.uniform(3.5, 7))
        main = _one_rumble(dur, rng.uniform(0.5, 0.8))
        # chasquido inicial casi siempre (es lo que "anuncia" el trueno)
        if rng.random() < 0.85:
            cd = int(SR * rng.uniform(0.2, 0.5))
            ce = np.exp(-np.arange(cd, dtype=np.float32) / (cd * 0.3))
            crack = bandpass(rng.standard_normal(cd).astype(np.float32),
                             250, 1400, order=2) * ce
            main[:cd] += _norm(crack, -15)[:cd] * 0.7
        out[i:i + dur] += main * rng.uniform(0.7, 1.0)
        # eco rodante: segundo retumbo más suave 1.5-3.5 s después
        if rng.random() < 0.7:
            gap = int(SR * rng.uniform(1.5, 3.5))
            dur2 = int(SR * rng.uniform(2.5, 5))
            j = i + gap
            if j + dur2 < n:
                out[j:j + dur2] += _one_rumble(dur2, rng.uniform(0.3, 0.5)) * rng.uniform(0.35, 0.55)
        t_pos += rng.uniform(18, 55) * SR
    return np.clip(out, -1, 1)


def fireplace(n: int, rng: np.random.Generator) -> np.ndarray:
    """Hoguera: roar de llama con flutter + crujidos resonantes con cuerpo
    (senos amortiguados, no impulsos) + pops graves ocasionales."""
    # llama: rumor grave con aleteo lento característico
    flame = lowpass(_white(n, rng), 380)
    t = np.arange(n, dtype=np.float32) / SR
    flutter = 1 + 0.18 * np.sin(2 * np.pi * rng.uniform(5, 9) * t) \
                * _slow_env(n, rng, 0.15, floor=0.3)
    flame = _norm(flame * flutter, -21)

    def _crackle(dur: int, f: float, noise_mix: float) -> np.ndarray:
        tt = np.arange(dur, dtype=np.float32) / SR
        env = np.exp(-tt / (dur / SR * rng.uniform(0.15, 0.35)))
        tone = np.sin(2 * np.pi * f * tt + rng.uniform(0, 6.28)).astype(np.float32)
        nz = bandpass(rng.standard_normal(dur).astype(np.float32),
                      f * 0.6, min(f * 1.8, 9000), order=1)
        return (tone * (1 - noise_mix) + nz * noise_mix) * env

    crackles = np.zeros(n, dtype=np.float32)
    i = int(rng.uniform(0.2, 0.8) * SR)
    while i < n - SR:
        # crujido con cuerpo: 8-40 ms, resonancia 800-2600 Hz
        dur = int(SR * rng.uniform(0.008, 0.040))
        c = _crackle(dur, rng.uniform(800, 2600), rng.uniform(0.3, 0.6))
        crackles[i:i + dur] += c * rng.uniform(0.10, 0.45)
        # a veces una mini-ráfaga pegada (madera que se parte)
        if rng.random() < 0.30:
            for _ in range(int(rng.integers(1, 4))):
                i += int(SR * rng.uniform(0.03, 0.12))
                dur = int(SR * rng.uniform(0.006, 0.025))
                if i + dur >= n:
                    break
                c = _crackle(dur, rng.uniform(1000, 3000), rng.uniform(0.3, 0.6))
                crackles[i:i + dur] += c * rng.uniform(0.08, 0.35)
        i += int(SR * rng.uniform(0.25, 0.9))          # 1-4 crujidos/seg

    # pops graves ocasionales ("thunk" de tronco)
    pops = np.zeros(n, dtype=np.float32)
    i = int(rng.uniform(2, 6) * SR)
    while i < n - SR:
        dur = int(SR * rng.uniform(0.04, 0.09))
        p = _crackle(dur, rng.uniform(140, 380), 0.25)
        pops[i:i + dur] += p * rng.uniform(0.25, 0.5)
        i += int(SR * rng.uniform(3, 10))

    hiss = bandpass(_white(n, rng), 2500, 6500) * _slow_env(n, rng, 0.1, floor=0.3) * 0.05
    mix = flame * 1.0 + crackles * 0.9 + pops * 0.9 + hiss
    return _norm(mix)


def crickets(n: int, rng: np.random.Generator) -> np.ndarray:
    """Grillos nocturnos: pocos individuos, cadencia tranquila."""
    out = np.zeros(n, dtype=np.float32)
    for _ in range(int(rng.integers(2, 4))):           # 2-3 grillos
        f0 = rng.uniform(3600, 4600)
        pulse_rate = rng.uniform(24, 38)
        period = rng.uniform(1.6, 3.2)                 # más pausa entre chirps
        gain = rng.uniform(0.08, 0.16)
        pos = rng.uniform(0, period) * SR
        while pos < n - SR:
            dur = int(SR * rng.uniform(0.25, 0.6))
            if pos + dur >= n:
                break
            tt = np.arange(dur, dtype=np.float64) / SR
            am = np.clip(np.sin(2 * np.pi * pulse_rate * tt), 0, None) ** 2
            hann = np.hanning(dur)
            chirp = np.sin(2 * np.pi * f0 * tt) * am * hann * gain
            i = int(pos)
            out[i:i + dur] += chirp.astype(np.float32)
            pos += period * SR * rng.uniform(0.9, 1.3)
    out = lowpass(out, 5200, order=2)                  # lima la aspereza
    return _norm(out, -23)                             # más discretos en la mezcla


# ----------------------------------------------------------------------
# Temas (recetas de mezcla)
# ----------------------------------------------------------------------
THEMES = {
    "gentle_rain":    [(rain, 0.90), (brown_noise, 0.22)],
    "ocean_waves":    [(ocean, 0.90), (wind, 0.18)],
    "deep_brown":     [(brown_noise, 1.00)],
    "night_wind":     [(wind, 0.85), (brown_noise, 0.30)],
    "dream_pads":     [(pads, 0.95), (brown_noise, 0.12)],
    "rain_and_pads":  [(rain, 0.55), (pads, 0.60)],
    "thunder_rain":   [(rain, 1.00), (thunder, 1.10), (brown_noise, 0.10)],
    "fireplace":      [(fireplace, 1.00)],
    "rain_fireplace": [(rain, 0.55), (fireplace, 0.75)],
    "crickets_night": [(crickets, 0.60), (wind, 0.25), (brown_noise, 0.25)],
}


def _stereoize(x: np.ndarray) -> np.ndarray:
    """Estéreo por descorrelación mid/side sutil."""
    side = np.roll(x, 617)
    side = bandpass(side, 250, 5000, order=1) * 0.22
    left = x + side
    right = x - side
    return np.stack([left, right], axis=1)


def _make_loopable(x: np.ndarray, xf_sec: float = 4.0) -> np.ndarray:
    """Funde el final sobre el principio para que el loop no tenga costura."""
    m = int(xf_sec * SR)
    ramp = np.linspace(0, 1, m, dtype=np.float32)
    out = x[:-m].copy()
    out[:m] = x[-m:] * (1 - ramp) + x[:m] * ramp
    return out


def render_segment(theme: str, minutes: float, seed: int) -> np.ndarray:
    """Devuelve audio estéreo float32 loopeable de `minutes` de duración."""
    rng = np.random.default_rng(seed)
    n = int(minutes * 60 * SR) + int(4.0 * SR)  # margen para el crossfade de loop
    mix = np.zeros(n, dtype=np.float32)
    for layer_fn, gain in THEMES[theme]:
        mix += layer_fn(n, rng) * gain
    mix = _norm(mix, rms_db=-20.0)
    mix = np.tanh(mix * 1.1) * 0.85             # limitador suave
    mix = _make_loopable(mix)
    return _stereoize(mix)
