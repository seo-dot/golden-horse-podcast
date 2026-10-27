"""Догоняющая загрузка видео на YouTube для выпусков, у которых нет youtube_url.

Выпуски, сделанные, пока токен YouTube не работал, остались без видео: в репозитории
есть аудио (.mp3), субтитры (.srt) и запись в state.json, но нет .mp4. Скрипт собирает
видео заново (как src/main.py: заставка + фото + аудио), заливает его на канал вместе
с субтитрами и записывает youtube_url в state.json. Самые старые выпуски идут первыми.

Запуск:  python -m src.backfill [--limit N] [--dry-run]
  --limit N   сколько видео залить за один запуск (по умолчанию BACKFILL_LIMIT или 2;
              ограничение нужно из-за суточной квоты YouTube API)
  --dry-run   только собрать видео, ничего не загружать и не менять в state.json

Коды выхода: 0 = всё в порядке (в том числе «нечего догонять» и «упёрлись в квоту»),
             1 = была ошибка, которую стоит посмотреть.
"""
import os
import sys

from . import config, state as st, fetch_car, generate_script, build_video

TAGS = ["Golden Horse", "car service", "car service Dubai",
        "car repair Dubai", "auto repair", "oil change", "AC repair",
        "car maintenance", "Dubai"]

# Ошибки YouTube, при которых нет смысла пробовать следующий выпуск.
_QUOTA_MARKERS = ("quotaExceeded", "uploadLimitExceeded", "dailyLimitExceeded",
                  "rateLimitExceeded")
_AUTH_MARKERS = ("invalid_grant", "unauthorized_client", "invalid_client")


def pending_episodes(state):
    """Выпуски без ссылки на YouTube, у которых сохранено аудио. Старые первыми."""
    out = []
    for ep in state.get("episodes", []):
        if ep.get("youtube_url"):
            continue
        name = ep.get("file")
        if not name or not (config.EPISODES_DIR / name).exists():
            continue
        out.append(ep)
    out.sort(key=lambda e: e["file"])
    return out


def build_for(ep):
    """Собирает mp4 для выпуска. Возвращает (video_path, srt_path)."""
    base = ep["file"].rsplit(".", 1)[0]
    audio_path = str(config.EPISODES_DIR / ep["file"])
    srt_path = str(config.EPISODES_DIR / ep.get("srt", f"{base}.srt"))

    # Название и фото берём с исходной страницы, как при обычной сборке.
    # Если страница недоступна, используем то, что сохранено в state.json.
    title_text = None
    image_url = ep.get("image", "")
    try:
        car = fetch_car.parse_car(ep["source_url"])
        title_text = generate_script.clean_car_name(car["title"])
        image_url = car.get("image") or image_url
    except Exception as e:
        print(f"[backfill] страницу {ep.get('source_url')} разобрать не удалось ({e}),"
              " беру данные из state.json")
    if not title_text:
        title_text = generate_script.clean_car_name(ep.get("title") or base)

    config.TMP_DIR.mkdir(parents=True, exist_ok=True)
    img_path = build_video.download_image(image_url, str(config.TMP_DIR / f"{base}.jpg"))
    video_path = str(config.VIDEOS_DIR / f"{base}.mp4")
    info = build_video.build_video(
        image_path=img_path, audio_path=audio_path, title_text=title_text,
        out_path=video_path, tmp_dir=str(config.TMP_DIR))
    print(f"[backfill] видео: {info['duration_sec']}с -> {base}.mp4")
    return video_path, srt_path


def _cleanup(*paths):
    for p in paths:
        try:
            os.remove(p)
        except OSError:
            pass


def main(argv):
    dry_run = "--dry-run" in argv
    limit = int(os.environ.get("BACKFILL_LIMIT", "2") or "2")
    if "--limit" in argv:
        limit = int(argv[argv.index("--limit") + 1])

    if not dry_run and not (config.YOUTUBE_ENABLED and config.YOUTUBE_CLIENT_ID
                            and config.YOUTUBE_CLIENT_SECRET
                            and config.YOUTUBE_REFRESH_TOKEN):
        print("[backfill] нет доступа к YouTube (секреты BACKFILL_YOUTUBE_* не заданы),"
              " ничего не делаю.")
        return 0

    state = st.load()
    todo = pending_episodes(state)
    print(f"[backfill] без видео на YouTube: {len(todo)}; за этот запуск: {min(limit, len(todo))}")

    done = failed = 0
    for ep in todo[:limit]:
        print(f"[backfill] {ep['file']}")
        try:
            video_path, srt_path = build_for(ep)
        except Exception as e:
            print(f"[backfill] сборка видео не удалась ({e})")
            failed += 1
            continue

        if dry_run:
            print(f"[backfill] dry-run: загрузку пропускаю ({video_path})")
            _cleanup(video_path)
            continue

        try:
            from . import youtube_upload
            res = youtube_upload.upload(
                video_path,
                title=ep.get("youtube_title") or ep.get("title") or ep["file"],
                description=ep.get("description", ""),
                tags=TAGS, srt_path=srt_path)
        except Exception as e:
            msg = str(e)
            print(f"[backfill] загрузка на YouTube не удалась ({msg})")
            _cleanup(video_path)
            if any(m in msg for m in _QUOTA_MARKERS):
                print("[backfill] суточная квота исчерпана, продолжу в следующий раз.")
                break
            failed += 1
            if any(m in msg for m in _AUTH_MARKERS):
                print("[backfill] токен YouTube не принят, дальше не пробую.")
                break
            continue

        ep["youtube_url"] = res["url"]
        st.save(state)  # сохраняем после каждого успеха, чтобы не потерять прогресс
        print(f"[backfill] YouTube: {res['url']}")
        done += 1
        _cleanup(video_path)

    left = len(pending_episodes(state)) if not dry_run else len(todo)
    print(f"[backfill] загружено: {done}, ошибок: {failed}, осталось без видео: {left}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
