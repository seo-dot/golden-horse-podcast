"""Работа с состоянием: какие URL уже обработаны, список эпизодов."""
import json
from . import config


def load():
    if config.STATE_PATH.exists():
        with open(config.STATE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"processed_urls": [], "episodes": []}


def save(state):
    with open(config.STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def is_processed(state, url):
    return url in state.get("processed_urls", [])


def mark_processed(state, url):
    state.setdefault("processed_urls", [])
    if url not in state["processed_urls"]:
        state["processed_urls"].append(url)


def add_episode(state, episode):
    state.setdefault("episodes", [])
    state["episodes"].append(episode)
