"""Keep brand names intact in titles/descriptions shown to viewers in other languages.

YouTube may machine-translate a video's title and description for viewers whose language
differs from the video's. Machine translation can change brand names (Octane Rent,
DubiCars, Golden Horse, ...). If the author supplies their own localization for a
language, YouTube shows that text instead of its own translation. We therefore set the
video's default language to English and add a localization for the main languages whose
title/description are the ORIGINAL text, unchanged.

Everything here is fail-safe: it runs after the video is uploaded and any error is logged
and swallowed, so it can never block or fail an upload.

Quota: one videos.update (snippet + localizations) costs 50 units.
Env: YOUTUBE_LOCALIZATIONS=false turns it off; YOUTUBE_LOCALIZATION_LANGS="ru,ar,..." overrides.
"""
from __future__ import annotations

import logging
import os

log = logging.getLogger(__name__)

DEFAULT_LANGUAGE = "en"
DEFAULT_LANGS = ["ru", "ar", "es", "fr", "de", "zh-Hans", "hi", "pt", "tr", "it"]


def enabled() -> bool:
    return os.environ.get("YOUTUBE_LOCALIZATIONS", "true").strip().lower() not in (
        "0", "false", "no", "off")


def languages() -> list[str]:
    raw = os.environ.get("YOUTUBE_LOCALIZATION_LANGS", "").strip()
    langs = [l.strip() for l in raw.split(",") if l.strip()] if raw else list(DEFAULT_LANGS)
    return [l for l in langs if l.lower() != DEFAULT_LANGUAGE]


def build_localizations(title: str, description: str, langs: list[str] | None = None) -> dict:
    """Same original text for every language (brand names untouched)."""
    entry = {"title": title[:100], "description": description[:5000]}
    return {lang: dict(entry) for lang in (langs if langs is not None else languages())}


def apply_localizations(youtube, video_id: str, snippet: dict) -> bool:
    """Add localizations to an existing video. Never raises. Returns True on success."""
    try:
        if not enabled():
            return False
        locs = build_localizations(snippet["title"], snippet.get("description", ""))
        if not locs:
            return False
        body = {
            "id": video_id,
            "snippet": {
                "title": snippet["title"],
                "description": snippet.get("description", ""),
                "tags": snippet.get("tags", []),
                "categoryId": snippet["categoryId"],
                "defaultLanguage": DEFAULT_LANGUAGE,
            },
            "localizations": locs,
        }
        youtube.videos().update(part="snippet,localizations", body=body).execute()
        log.info("Localizations set for %s (%d languages)", video_id, len(locs))
        return True
    except Exception as exc:  # noqa: BLE001 - must never break the upload
        log.warning("Localizations not set (non-fatal): %s", exc)
        return False


def backfill(youtube, limit: int = 20, apply: bool = False) -> list[str]:
    """Add localizations to already published videos that have none. Dry run by default.

    Lists the channel's uploads (cheap reads), updates up to `limit` videos (50 units each).
    Returns the ids that were (or, in a dry run, would be) updated.
    """
    ch = youtube.channels().list(part="contentDetails", mine=True).execute()
    uploads = ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    done: list[str] = []
    token = None
    while len(done) < limit:
        page = youtube.playlistItems().list(
            part="contentDetails", playlistId=uploads, maxResults=50, pageToken=token).execute()
        ids = [i["contentDetails"]["videoId"] for i in page.get("items", [])]
        if ids:
            vids = youtube.videos().list(
                part="snippet,localizations", id=",".join(ids)).execute()
            for v in vids.get("items", []):
                if len(done) >= limit:
                    break
                if v.get("localizations"):
                    continue
                s = v["snippet"]
                if apply:
                    snip = {"title": s["title"], "description": s.get("description", ""),
                            "tags": s.get("tags", []), "categoryId": s["categoryId"]}
                    if not apply_localizations(youtube, v["id"], snip):
                        continue
                done.append(v["id"])
        token = page.get("nextPageToken")
        if not token:
            break
    return done


if __name__ == "__main__":  # python -m src.localizations [--apply] [--limit N]
    import argparse

    from . import youtube_upload

    ap = argparse.ArgumentParser(description="Backfill localizations on published videos")
    ap.add_argument("--apply", action="store_true", help="write changes (default: dry run)")
    ap.add_argument("--limit", type=int, default=20)
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO)
    out = backfill(youtube_upload._service(), a.limit, a.apply)
    print(("Updated" if a.apply else "Would update"), len(out), "videos:", *out)
