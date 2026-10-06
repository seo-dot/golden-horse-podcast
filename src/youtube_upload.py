"""Загрузка готового видео на YouTube через официальный YouTube Data API v3.

Авторизация — по refresh-токену (получается один раз локально через get_youtube_token.py),
дальше приложение обновляет доступ само, без участия человека. Идеально для автозагрузки.

Загружает видео на тот канал, которому принадлежит refresh-токен (т.е. авторизуйся
Google-аккаунтом, владеющим нужным каналом).
"""
from . import config

SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube.force-ssl"]
TOKEN_URI = "https://oauth2.googleapis.com/token"


def _credentials():
    from google.oauth2.credentials import Credentials
    return Credentials(
        token=None,
        refresh_token=config.YOUTUBE_REFRESH_TOKEN,
        token_uri=TOKEN_URI,
        client_id=config.YOUTUBE_CLIENT_ID,
        client_secret=config.YOUTUBE_CLIENT_SECRET,
        scopes=SCOPES,
    )


def _service():
    from googleapiclient.discovery import build
    return build("youtube", "v3", credentials=_credentials(), cache_discovery=False)


def upload(video_path, title, description, tags=None, srt_path=None):
    """Загружает видео. Возвращает {video_id, url} или бросает исключение."""
    from googleapiclient.http import MediaFileUpload

    yt = _service()
    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:4900],
            "tags": (tags or [])[:30],
            "categoryId": config.YOUTUBE_CATEGORY_ID,
        },
        "status": {
            "privacyStatus": config.YOUTUBE_PRIVACY,
            "selfDeclaredMadeForKids": False,
        },
    }
    media = MediaFileUpload(video_path, mimetype="video/mp4",
                            chunksize=-1, resumable=True)
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        status, response = req.next_chunk()
        if status:
            print(f"[youtube] загрузка {int(status.progress() * 100)}%")
    video_id = response["id"]
    print(f"[youtube] видео загружено: {video_id}")

    # Отдельная дорожка субтитров (лучше для SEO и доступности).
    # Видео не должно падать из-за субтитров — все ошибки логируем и продолжаем.
    if srt_path and config.YOUTUBE_UPLOAD_CAPTIONS:
        try:
            _upload_caption(yt, video_id, srt_path)
        except Exception as e:
            print(f"[youtube] субтитры-дорожка не загрузилась (не критично): {e}")

    return {"video_id": video_id, "url": f"https://youtu.be/{video_id}"}


def _upload_caption(yt, video_id, srt_path, retries=3, delay=45):
    """Грузит SRT как отдельную дорожку субтитров (language='en', name='English').

    captions().insert иногда отдаёт 403, пока видео ещё обрабатывается — поэтому
    делаем несколько попыток с паузой и логируем ПОЛНЫЙ текст ошибки.
    """
    import time
    from googleapiclient.http import MediaFileUpload
    from googleapiclient.errors import HttpError

    last_err = None
    for attempt in range(1, retries + 1):
        try:
            body = {"snippet": {"videoId": video_id, "language": "en",
                                "name": "English", "isDraft": False}}
            media = MediaFileUpload(srt_path, mimetype="application/octet-stream",
                                    resumable=False)
            yt.captions().insert(part="snippet", body=body, media_body=media).execute()
            print("[youtube] дорожка субтитров загружена (en / English)")
            return True
        except HttpError as e:
            content = getattr(e, "content", b"")
            if isinstance(content, (bytes, bytearray)):
                content = content.decode("utf-8", "replace")
            status = getattr(getattr(e, "resp", None), "status", "?")
            last_err = f"HTTP {status}: {content}"
            print(f"[youtube] captions.insert попытка {attempt}/{retries}: {last_err}")
        except Exception as e:
            last_err = repr(e)
            print(f"[youtube] captions.insert попытка {attempt}/{retries}: {last_err}")
        if attempt < retries:
            print(f"[youtube] жду {delay}с (видео может ещё обрабатываться)...")
            time.sleep(delay)

    print(f"[youtube] субтитры-дорожка НЕ загружена после {retries} попыток. "
          f"Точная причина: {last_err}")
    return False
