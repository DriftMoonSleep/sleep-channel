"""Subida a YouTube (Data API v3) con OAuth refresh token desde secrets.

Nota: hasta que Google apruebe la auditoría del proyecto API, todo vídeo
subido por API queda BLOQUEADO EN PRIVADO por política de YouTube.

La metadata se intenta en "escalera": si la API rechaza algún campo opcional
(p. ej. containsSyntheticMedia según versión de la API), se reintenta sin él.
"""
from __future__ import annotations

import copy
import os
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload


def _youtube():
    creds = Credentials(
        token=None,
        refresh_token=os.environ["YT_REFRESH_TOKEN"],
        client_id=os.environ["YT_CLIENT_ID"],
        client_secret=os.environ["YT_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
    )
    return build("youtube", "v3", credentials=creds)


# Campos opcionales que se retiran en orden si la API devuelve 400
_DROP_LADDER = [
    [],
    ["status.containsSyntheticMedia"],
    ["status.containsSyntheticMedia",
     "snippet.defaultAudioLanguage", "snippet.defaultLanguage"],
]


def upload_video(video: Path, thumb: Path, meta: dict, privacy: str = "private",
                 lang: str = "en") -> str:
    yt = _youtube()
    body = {
        "snippet": {
            "title": meta["title"],
            "description": meta["description"],
            "tags": [str(t) for t in meta["tags"]],
            "categoryId": "10",  # Música
            "defaultLanguage": lang,
            "defaultAudioLanguage": "zxx",  # sin habla
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
            "containsSyntheticMedia": True,  # divulgación de contenido sintético
        },
    }

    resp = None
    last_error = None
    for drop in _DROP_LADDER:
        b = copy.deepcopy(body)
        for path in drop:
            section, key = path.split(".")
            b[section].pop(key, None)
        media = MediaFileUpload(str(video), chunksize=16 * 1024 * 1024,
                                resumable=True)
        req = yt.videos().insert(part="snippet,status", body=b, media_body=media)
        try:
            resp = None
            while resp is None:
                progress, resp = req.next_chunk()
                if progress:
                    print(f"  subida: {int(progress.progress() * 100)}%", flush=True)
            if drop:
                print(f"  aviso: la API rechazó estos campos y se omitieron: {drop}")
            break
        except HttpError as e:
            last_error = e
            status = getattr(getattr(e, "resp", None), "status", None)
            if status == 400 and drop != _DROP_LADDER[-1]:
                print(f"  metadata rechazada (400) con drop={drop}; "
                      "reintentando con menos campos opcionales…", flush=True)
                continue
            raise
    if resp is None:
        raise last_error

    vid = resp["id"]
    try:
        yt.thumbnails().set(videoId=vid, media_body=str(thumb)).execute()
    except HttpError as e:
        print(f"  aviso: miniatura no aplicada ({getattr(e, 'status_code', '?')}); "
              "requiere cuenta verificada por teléfono en youtube.com/verify")
    return f"https://youtu.be/{vid}"
