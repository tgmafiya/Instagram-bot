import json
import os
import threading
from datetime import datetime, timezone

from config import DATA_DIR


SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")
HISTORY_FILE = os.path.join(DATA_DIR, "history.json")

_lock = threading.Lock()


DEFAULT_SETTINGS = {
    "enabled": False,
    "interval_hours": 6,
    "daily_limit": 3,
    "telegram_channel": "",
    "content_style": "funny, clever, premium, Gen-Z, slightly teasing",
    "last_post_at": None,
}


def ensure_files():
    os.makedirs(DATA_DIR, exist_ok=True)

    if not os.path.exists(SETTINGS_FILE):
        save_json(SETTINGS_FILE, DEFAULT_SETTINGS.copy())

    if not os.path.exists(HISTORY_FILE):
        save_json(HISTORY_FILE, [])


def load_json(path, default):
    ensure_parent = os.path.dirname(path)

    if ensure_parent:
        os.makedirs(ensure_parent, exist_ok=True)

    if not os.path.exists(path):
        save_json(path, default)
        return default

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)

    temp = path + ".tmp"

    with open(temp, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            indent=2,
            ensure_ascii=False,
        )

    os.replace(temp, path)


def get_settings():
    with _lock:
        settings = load_json(
            SETTINGS_FILE,
            DEFAULT_SETTINGS.copy(),
        )

        changed = False

        for key, value in DEFAULT_SETTINGS.items():
            if key not in settings:
                settings[key] = value
                changed = True

        if changed:
            save_json(SETTINGS_FILE, settings)

        return settings


def update_settings(**kwargs):
    with _lock:
        settings = get_settings()

        for key, value in kwargs.items():
            if value is not None:
                settings[key] = value

        save_json(SETTINGS_FILE, settings)

        return settings


def get_history():
    with _lock:
        return load_json(HISTORY_FILE, [])


def add_history(item):
    with _lock:
        history = load_json(HISTORY_FILE, [])

        history.insert(0, item)

        # Keep last 100 posts
        history = history[:100]

        save_json(HISTORY_FILE, history)

        return history


def posts_today():
    today = datetime.now(timezone.utc).date().isoformat()

    history = get_history()

    count = 0

    for item in history:
        created = item.get("created_at", "")

        if created.startswith(today):
            if item.get("published") is True:
                count += 1

    return count


def can_post_today():
    settings = get_settings()

    return posts_today() < int(
        settings.get("daily_limit", 3)
    )


def mark_last_post():
    update_settings(
        last_post_at=datetime.now(timezone.utc).isoformat()
    )


def find_duplicate(content_hash):
    history = get_history()

    for item in history:
        if item.get("content_hash") == content_hash:
            return True

    return False
