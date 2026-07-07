"""Ensamblado del vídeo con ffmpeg: audio loopeado sin recodificar + imagen fija."""
from __future__ import annotations

import math
import subprocess
from pathlib import Path

import numpy as np
import soundfile as sf

from .audio_engine import SR


def _run(cmd: list[str]):
    subprocess.run(cmd, check=True, capture_output=True)


def encode_segment(audio: np.ndarray, workdir: Path) -> Path:
    """PCM → AAC una sola vez (lo caro); el loop luego es copia sin pérdida."""
    wav = workdir / "segment.wav"
    m4a = workdir / "segment.m4a"
    sf.write(wav, audio, SR, subtype="PCM_16")
    _run(["ffmpeg", "-y", "-i", str(wav), "-c:a", "aac", "-b:a", "160k", str(m4a)])
    try:
        wav.unlink()
    except OSError:
        pass  # liberar disco es deseable, no crítico
    return m4a


def loop_audio(segment: Path, target_hours: float, workdir: Path) -> Path:
    info = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(segment)],
        check=True, capture_output=True, text=True,
    )
    seg_dur = float(info.stdout.strip())
    n = math.ceil(target_hours * 3600 / seg_dur)
    lst = workdir / "loop.txt"
    lst.write_text(f"file '{segment.resolve().as_posix()}'\n" * n, encoding="utf-8")
    out = workdir / "full_audio.m4a"
    _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
          "-c", "copy", str(out)])
    return out


def make_video(image: Path, audio: Path, out: Path, fps: int = 2,
               fade_start_sec: int = 0):
    """fade_start_sec > 0 → la imagen se funde a negro en ese segundo
    (formato "black screen" estándar del nicho sleep) y el resto del
    vídeo queda en negro, que además comprime a casi nada."""
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-framerate", str(fps), "-i", str(image),
        "-i", str(audio),
    ]
    if fade_start_sec:
        cmd += ["-vf", f"fade=t=out:st={fade_start_sec}:d=45:color=black"]
    cmd += [
        "-c:v", "libx264", "-tune", "stillimage", "-preset", "veryfast",
        "-crf", "22", "-pix_fmt", "yuv420p", "-r", str(fps), "-g", str(fps * 30),
        "-c:a", "copy", "-shortest", "-movflags", "+faststart",
        str(out),
    ]
    _run(cmd)
    return out
