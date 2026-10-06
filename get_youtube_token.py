#!/usr/bin/env python3
"""РАЗОВЫЙ скрипт: получить refresh-токен YouTube для автозагрузки.

Запусти ОДИН РАЗ на своём компьютере:

    pip install google-auth-oauthlib
    python get_youtube_token.py

Что нужно заранее (см. README, раздел «Привязка YouTube-канала»):
  1. В Google Cloud Console создать проект, включить "YouTube Data API v3".
  2. Настроить OAuth consent screen (External, добавить себя в Test users).
  3. Создать OAuth client ID типа "Desktop app", скачать client_secret.json
     и положить рядом с этим скриптом (или задать переменные ниже).

Скрипт откроет браузер, попросит войти Google-аккаунтом, ВЛАДЕЮЩИМ нужным каналом,
и подтвердить доступ. В конце распечатает REFRESH TOKEN — его вставишь в GitHub Secrets
как YOUTUBE_REFRESH_TOKEN (а client_id/secret — как YOUTUBE_CLIENT_ID / YOUTUBE_CLIENT_SECRET).
"""
import json
import os
import sys

SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube.force-ssl"]


def main():
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        sys.exit("Установи зависимость: pip install google-auth-oauthlib")

    secrets_file = os.environ.get("CLIENT_SECRETS", "client_secret.json")
    if not os.path.exists(secrets_file):
        sys.exit(f"Не найден {secrets_file}. Скачай OAuth client (Desktop) из Google Cloud Console "
                 f"и положи рядом, либо задай CLIENT_SECRETS=путь.")

    flow = InstalledAppFlow.from_client_secrets_file(secrets_file, SCOPES)
    # Откроет локальный сервер и браузер для входа
    creds = flow.run_local_server(port=0, prompt="consent")

    with open(secrets_file, encoding="utf-8") as f:
        data = json.load(f)
    info = data.get("installed") or data.get("web") or {}

    print("\n" + "=" * 60)
    print("ГОТОВО. Скопируй эти три значения в GitHub Secrets:\n")
    print("YOUTUBE_CLIENT_ID     =", info.get("client_id", "<из client_secret.json>"))
    print("YOUTUBE_CLIENT_SECRET =", info.get("client_secret", "<из client_secret.json>"))
    print("YOUTUBE_REFRESH_TOKEN =", creds.refresh_token)
    print("=" * 60)
    if not creds.refresh_token:
        print("\n⚠ refresh_token пустой. Удали доступ приложения на "
              "https://myaccount.google.com/permissions и запусти скрипт снова.")


if __name__ == "__main__":
    main()
