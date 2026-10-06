"""Генерация RSS-фида подкаста (RSS 2.0 + iTunes-теги) из state.json.

Именно этот feed.xml сабмитится в YouTube Music / Spotify / Apple один раз,
дальше они сами подтягивают новые эпизоды.
"""
import datetime
from email.utils import format_datetime
from feedgen.feed import FeedGenerator
from . import config


def build(state):
    fg = FeedGenerator()
    fg.load_extension("podcast")

    feed_url = f"{config.PUBLIC_BASE_URL}/feed.xml"
    fg.id(feed_url)
    fg.title(config.PODCAST_TITLE)
    fg.author({"name": config.PODCAST_AUTHOR, "email": config.PODCAST_EMAIL})
    fg.link(href=config.PODCAST_SITE, rel="alternate")
    fg.link(href=feed_url, rel="self")
    fg.language(config.PODCAST_LANGUAGE)
    fg.description(config.PODCAST_DESCRIPTION)
    fg.logo(f"{config.PUBLIC_BASE_URL}/assets/cover.jpg")

    # iTunes / podcast namespace
    fg.podcast.itunes_author(config.PODCAST_AUTHOR)
    fg.podcast.itunes_summary(config.PODCAST_DESCRIPTION)
    fg.podcast.itunes_category(config.PODCAST_CATEGORY)
    fg.podcast.itunes_explicit("no")
    fg.podcast.itunes_owner(name=config.PODCAST_AUTHOR, email=config.PODCAST_EMAIL)
    fg.podcast.itunes_image(f"{config.PUBLIC_BASE_URL}/assets/cover.jpg")

    # Эпизоды (в фиде — от новых к старым; feedgen добавляет сверху,
    # поэтому идём в прямом порядке)
    for ep in state.get("episodes", []):
        fe = fg.add_entry()
        ep_url = f"{config.PUBLIC_BASE_URL}/episodes/{ep['file']}"
        fe.id(ep_url)
        fe.title(ep["title"])
        fe.description(ep.get("description", ""))
        fe.link(href=ep.get("source_url", config.PODCAST_SITE))
        fe.enclosure(ep_url, str(ep.get("bytes", 0)), "audio/mpeg")
        fe.published(ep["pub_date"])
        if ep.get("duration_sec"):
            fe.podcast.itunes_duration(_fmt_duration(ep["duration_sec"]))
        # Картинку на уровне эпизода НЕ ставим: горизонтальное фото машины (1920×743)
        # площадки режут в квадрат. Эпизоды наследуют квадратную обложку канала
        # (assets/cover.jpg) — без искажений.

    fg.rss_file(str(config.FEED_PATH), pretty=True)
    return str(config.FEED_PATH)


def _fmt_duration(sec):
    h, rem = divmod(int(sec), 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def now_rfc2822():
    return format_datetime(datetime.datetime.now(datetime.timezone.utc))
