"""Subida a YouTube (Data API v3) con OAuth refresh token desde secrets.

Nota: hasta que Google apruebe la auditoría del proyecto API, todo vídeo
subido por API queda BLOQUEADO EN PRIVADO por política de YouTube.
El pipeline funciona igual; publicar son 2 clics en YouTube Studio.
"""
from __future__ import annotations

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


def upload_video(video: Path, thumb: Path, meta: dict, privacy: str = "private",
                 lang: str = "en") -> str:
    yt = _youtube()
    status = {
        "privacyStatus": privacy,
        "selfDeclaredMadeForKids": False,
        "containsSyntheticMedia": True,   # divulgación de contenido sintético
    }
    body = {
        "snippet": {
            "title": meta["title"],
            "description": meta["description"],
            "tags": meta["tags"],
            "categoryId": "10",  # Música
            "defaultLanguage": lang,
            "defaultAudioLanguage": "zxx",  # sin habla
        },
        "status": status,
    }
    media = MediaFileUpload(str(video), chunksize=16 * 1024 * 1024, resumable=True)

    def _insert():
        req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
        resp = None
        while resp is None:
            progress, resp = req.next_chunk()
            if progress:
                print(f"  subida: {int(progress.progress() * 100)}%", flush=True)
        return resp

    try:
        resp = _insert()
    except HttpError as e:
        # compatibilidad: si el campo de divulgación aún no existe en la API
        if b"containsSyntheticMedia" in e.content:
            status.pop("containsSyntheticMedia", None)
            resp = _insert()
        else:
            raise

    vid = resp["id"]
    try:
        yt.thumbnails().set(videoId=vid, media_body=str(thumb)).execute()
    except HttpError as e:
        print(f"  aviso: miniatura no aplicada ({e.status_code}); "
              "requiere cuenta verificada por teléfono en youtube.com/verify")
    return f"https://youtu.be/{vid}"
