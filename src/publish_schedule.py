"""Естественное время публикации на YouTube (без ручной работы).

Видео заливается как private и получает publishAt — случайное время внутри
вечернего окна канала (по Asia/Dubai). Выбор детерминирован: зависит только от
канала и даты, поэтому повторный запуск в тот же день выберет то же время.

Если выбрать/поставить время не удалось — вызывающий код публикует сразу
(как раньше), так что видео не теряется.

Настройки (все необязательны, переменные окружения / GitHub Variables):
  RANDOM_PUBLISH=false      выключить отложенную публикацию совсем
  PUBLISH_WINDOW=18:00-21:30  окно по местному времени
  PUBLISH_TZ=Asia/Dubai     часовой пояс окна
  RANDOM_SKIP_DAYS=false    выключить пропуск 1-2 дней в неделю (только подкасты)

Проверка без загрузки:  python -m src.publish_schedule
"""
import datetime as dt
import hashlib
import os
import random

CHANNEL = "golden-horse-podcast"
DEFAULT_WINDOW = "19:30-23:30"
DEFAULT_TZ = "Asia/Dubai"
SKIP_DAYS_SUPPORTED = True   # пропуск дней — только для ежедневных подкастов
MIN_LEAD_MINUTES = 20            # publishAt всегда минимум на столько позже «сейчас»


def _env(name, default=""):
    v = os.environ.get(name)
    return v.strip() if v and v.strip() else default


def _flag(name, default=True):
    v = _env(name)
    if not v:
        return default
    return v.lower() in ("1", "true", "yes", "on")


def _tz():
    name = _env("PUBLISH_TZ", DEFAULT_TZ)
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(name)
    except Exception:
        return dt.timezone(dt.timedelta(hours=4))  # Dubai, без перехода на летнее время


def parse_window(text):
    """'18:00-21:30' -> (минуты от полуночи начала, конца). Некорректное -> окно по умолчанию."""
    for candidate in (text, DEFAULT_WINDOW):
        try:
            a, b = candidate.split("-")
            ah, am = (int(x) for x in a.strip().split(":"))
            bh, bm = (int(x) for x in b.strip().split(":"))
            start, end = ah * 60 + am, bh * 60 + bm
            if 0 <= start < end <= 24 * 60:
                return start, end
        except Exception:
            continue
    raise ValueError("bad DEFAULT_WINDOW")


def _rng(*parts):
    digest = hashlib.sha256("|".join(str(p) for p in parts).encode()).digest()
    return random.Random(int.from_bytes(digest[:8], "big"))


def local_today(now=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    return now.astimezone(_tz()).date()


def pick_publish_at(now=None, extra="", window=None, tz=None, channel=None):
    """Время публикации (aware datetime в UTC): случайное в окне, строго в будущем.

    Берём слот на сегодняшнюю (местную) дату; если он уже прошёл или ближе
    MIN_LEAD_MINUTES — слот на следующую дату (до 3 дней вперёд).
    `extra` — доп. ключ (например, название ролика), если за запуск несколько видео.
    """
    now = (now or dt.datetime.now(dt.timezone.utc)).astimezone(dt.timezone.utc)
    tz = tz or _tz()
    start, end = window or parse_window(_env("PUBLISH_WINDOW", DEFAULT_WINDOW))
    channel = channel or CHANNEL
    earliest = now + dt.timedelta(minutes=MIN_LEAD_MINUTES)
    day = now.astimezone(tz).date()
    for _ in range(4):
        offset = _rng("publish", channel, day, extra).randrange(start * 60, end * 60)
        local_midnight = dt.datetime.combine(day, dt.time(0, 0), tzinfo=tz)
        cand = (local_midnight + dt.timedelta(seconds=offset)).astimezone(dt.timezone.utc)
        if cand >= earliest:
            return cand
        day += dt.timedelta(days=1)
    raise RuntimeError("не удалось подобрать слот публикации")


def publish_at_iso(**kw):
    """Строка RFC 3339 для поля status.publishAt."""
    return pick_publish_at(**kw).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def schedule_enabled(privacy):
    """Отложенная публикация только если канал сознательно публикует видео как public.
    private/unlisted (тесты, ручная проверка) не трогаем."""
    return _flag("RANDOM_PUBLISH", True) and str(privacy).strip().lower() == "public"


def skip_days_for_week(iso_year, iso_week, channel=None):
    """Дни недели (0=пн … 5=сб), в которые выпуск пропускается: 1 или 2 в неделю,
    не соседние; воскресенье не пропускается, поэтому подряд пропущенных дней не бывает."""
    rng = _rng("skip", channel or CHANNEL, iso_year, iso_week)
    want = rng.choice([1, 2])
    days = list(range(6))
    rng.shuffle(days)
    chosen = []
    for d in days:
        if len(chosen) == want:
            break
        if all(abs(d - c) > 1 for c in chosen):
            chosen.append(d)
    return sorted(chosen)


def should_skip_today(now=None):
    if not (SKIP_DAYS_SUPPORTED and _flag("RANDOM_SKIP_DAYS", True)):
        return False
    d = local_today(now)
    iso = d.isocalendar()
    return d.weekday() in skip_days_for_week(iso[0], iso[1])


if __name__ == "__main__":
    # dry-run: слоты и пропуски на ближайшие 14 дней
    base = dt.datetime.now(dt.timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    tz = _tz()
    print(f"канал={CHANNEL} окно={_env('PUBLISH_WINDOW', DEFAULT_WINDOW)} tz={tz}")
    for i in range(14):
        moment = base + dt.timedelta(days=i, hours=8)  # «запуск» в 08:00 UTC
        slot = pick_publish_at(now=moment).astimezone(tz)
        skip = " (ПРОПУСК дня)" if should_skip_today(moment) else ""
        print(f"{moment.date()} -> публикация {slot:%Y-%m-%d %H:%M}{skip}")
