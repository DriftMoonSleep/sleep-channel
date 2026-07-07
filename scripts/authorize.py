"""Autorización OAuth sin ordenador local (Device Flow).

Se ejecuta como workflow manual en GitHub Actions:
1. Imprime en el log una URL + código.
2. Abres la URL en el móvil, metes el código y autorizas el canal.
3. El script guarda el refresh token como secret del repo automáticamente
   (cifrado con la clave pública del repo; nunca aparece en el log).

Requiere secrets previos: YT_CLIENT_ID, YT_CLIENT_SECRET, GH_PAT.
"""
from __future__ import annotations

import base64
import os
import sys
import time

import requests
from nacl import encoding, public

SCOPES = ("https://www.googleapis.com/auth/youtube.upload "
          "https://www.googleapis.com/auth/youtube")


def get_refresh_token(client_id: str, client_secret: str) -> str:
    r = requests.post("https://oauth2.googleapis.com/device/code",
                      data={"client_id": client_id, "scope": SCOPES}, timeout=30)
    r.raise_for_status()
    d = r.json()

    print("=" * 60, flush=True)
    print("AUTORIZA EL CANAL (tienes ~30 min):", flush=True)
    print(f"  1. Abre:   {d['verification_url']}", flush=True)
    print(f"  2. Código: {d['user_code']}", flush=True)
    print("  3. Elige la cuenta/canal de YouTube y acepta.", flush=True)
    print("=" * 60, flush=True)

    while True:
        time.sleep(d.get("interval", 5))
        tr = requests.post("https://oauth2.googleapis.com/token", data={
            "client_id": client_id, "client_secret": client_secret,
            "device_code": d["device_code"],
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        }, timeout=30)
        body = tr.json()
        if "refresh_token" in body:
            return body["refresh_token"]
        if body.get("error") in ("authorization_pending", "slow_down"):
            continue
        sys.exit(f"Error de autorización: {body}")


def save_repo_secret(repo: str, pat: str, name: str, value: str):
    h = {"Authorization": f"Bearer {pat}", "Accept": "application/vnd.github+json"}
    k = requests.get(f"https://api.github.com/repos/{repo}/actions/secrets/public-key",
                     headers=h, timeout=30)
    k.raise_for_status()
    key = k.json()
    sealed = public.SealedBox(
        public.PublicKey(key["key"].encode(), encoding.Base64Encoder())
    ).encrypt(value.encode())
    r = requests.put(
        f"https://api.github.com/repos/{repo}/actions/secrets/{name}",
        headers=h,
        json={"encrypted_value": base64.b64encode(sealed).decode(),
              "key_id": key["key_id"]},
        timeout=30,
    )
    r.raise_for_status()


if __name__ == "__main__":
    token = get_refresh_token(os.environ["YT_CLIENT_ID"], os.environ["YT_CLIENT_SECRET"])
    save_repo_secret(os.environ["GITHUB_REPOSITORY"], os.environ["GH_PAT"],
                     "YT_REFRESH_TOKEN", token)
    print("✅ Refresh token guardado como secret YT_REFRESH_TOKEN. Ya puedes lanzar el pipeline.")
