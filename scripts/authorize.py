"""Autorización OAuth sin ordenador local (Device Flow), en dos pasos.

--request : pide el código de dispositivo a Google, lo imprime, lo escribe en
            el resumen del job y exporta outputs para el siguiente paso.
--poll    : espera a que el usuario autorice y guarda el refresh token como
            secret del repo (cifrado; nunca aparece en el log).

Requiere secrets: YT_CLIENT_ID, YT_CLIENT_SECRET, GH_PAT.
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


def request_code(client_id: str):
    r = requests.post("https://oauth2.googleapis.com/device/code",
                      data={"client_id": client_id, "scope": SCOPES}, timeout=30)
    r.raise_for_status()
    d = r.json()

    msg = (f"1. Abre: {d['verification_url']}\n"
           f"2. Código: {d['user_code']}\n"
           "3. Elige la cuenta del canal y acepta.")
    print("=" * 60, flush=True)
    print("AUTORIZA EL CANAL (tienes ~30 min):", flush=True)
    print(msg, flush=True)
    print("=" * 60, flush=True)

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write("## 🔑 Autoriza el canal (~30 min)\n\n"
                    f"1. Abre **{d['verification_url']}**\n"
                    f"2. Introduce el código: **`{d['user_code']}`**\n"
                    "3. Elige la cuenta del canal y acepta.\n")

    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as f:
            f.write(f"device_code={d['device_code']}\n")
            f.write(f"interval={d.get('interval', 5)}\n")


def poll_and_save(client_id: str, client_secret: str):
    device_code = os.environ["DEVICE_CODE"]
    interval = int(float(os.environ.get("POLL_INTERVAL", "5")))
    while True:
        time.sleep(interval)
        tr = requests.post("https://oauth2.googleapis.com/token", data={
            "client_id": client_id, "client_secret": client_secret,
            "device_code": device_code,
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        }, timeout=30)
        body = tr.json()
        if "refresh_token" in body:
            token = body["refresh_token"]
            break
        if body.get("error") in ("authorization_pending", "slow_down"):
            if body.get("error") == "slow_down":
                interval += 2
            continue
        sys.exit(f"Error de autorización: {body}")

    repo = os.environ["GITHUB_REPOSITORY"]
    pat = os.environ["GH_PAT"]
    h = {"Authorization": f"Bearer {pat}", "Accept": "application/vnd.github+json"}
    k = requests.get(f"https://api.github.com/repos/{repo}/actions/secrets/public-key",
                     headers=h, timeout=30)
    k.raise_for_status()
    key = k.json()
    sealed = public.SealedBox(
        public.PublicKey(key["key"].encode(), encoding.Base64Encoder())
    ).encrypt(token.encode())
    r = requests.put(
        f"https://api.github.com/repos/{repo}/actions/secrets/YT_REFRESH_TOKEN",
        headers=h,
        json={"encrypted_value": base64.b64encode(sealed).decode(),
              "key_id": key["key_id"]},
        timeout=30,
    )
    r.raise_for_status()
    print("✅ Refresh token guardado como secret YT_REFRESH_TOKEN. "
          "Ya puedes lanzar el pipeline.")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write("\n✅ **Canal autorizado.** Refresh token guardado. "
                    "Lanza el workflow \"Vídeo diario\".\n")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "--request"
    if mode == "--request":
        request_code(os.environ["YT_CLIENT_ID"])
    else:
        poll_and_save(os.environ["YT_CLIENT_ID"], os.environ["YT_CLIENT_SECRET"])
