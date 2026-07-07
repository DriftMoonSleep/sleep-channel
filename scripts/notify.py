"""Avisos post-subida: email (Gmail) y WhatsApp (CallMeBot).

Uso: python scripts/notify.py email|whatsapp
Lee out/last_upload.txt (título y URL) y config.yaml (destinos).
Si falta el secret correspondiente, sale sin error (aviso opcional).
"""
from __future__ import annotations

import os
import smtplib
import sys
from email.mime.text import MIMEText
from pathlib import Path

import requests
import yaml


def _load():
    cfg = yaml.safe_load(Path("config.yaml").read_text(encoding="utf-8"))
    lines = Path("out/last_upload.txt").read_text(encoding="utf-8").splitlines()
    return cfg, lines[0], lines[1]


def email():
    pw = os.environ.get("GMAIL_APP_PASSWORD", "").strip()
    if not pw:
        print("GMAIL_APP_PASSWORD no configurado → aviso por email omitido")
        return
    cfg, title, url = _load()
    sender = cfg.get("notify_from", "driftmoonsleep@gmail.com")
    to = cfg["notify_email"]
    body = (f"Nuevo vídeo subido en PRIVADO:\n\n{title}\n{url}\n\n"
            "Publícalo: YouTube Studio → Contenido → visibilidad → Público.\n"
            "Después cierra la issue correspondiente en GitHub.\n\n"
            f"— {cfg.get('channel_name', 'Driftmoon Sleep')} (aviso automático)")
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = f"📼 Publicar: {title}"
    msg["From"] = sender
    msg["To"] = to
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as s:
        s.login(sender, pw)
        s.send_message(msg)
    print(f"email enviado a {to}")


def whatsapp():
    key = os.environ.get("CALLMEBOT_APIKEY", "").strip()
    if not key:
        print("CALLMEBOT_APIKEY no configurado → aviso por WhatsApp omitido")
        return
    cfg, title, url = _load()
    phone = str(cfg["notify_phone"])
    text = f"🌙 Nuevo vídeo listo para publicar (privado):\n{title}\n{url}"
    r = requests.get("https://api.callmebot.com/whatsapp.php",
                     params={"phone": phone, "text": text, "apikey": key},
                     timeout=45)
    print(f"whatsapp → HTTP {r.status_code}: {r.text[:120]}")


if __name__ == "__main__":
    {"email": email, "whatsapp": whatsapp}[sys.argv[1]]()
