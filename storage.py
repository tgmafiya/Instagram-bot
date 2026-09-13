import json
import threading
from pathlib import Path

from config import (
    HISTORY_FILE,
    SETTINGS_FILE,
)


LOCK = threading.RLock()


DEFAULT_SETTINGS = {
    "enabled": True,
    "interval_hours": 6,
    "daily_limit": 3,
    "telegram_channel": "",
    "content_style": (
        "funny, clever, Gen-Z, "
        "mild double meaning but non-explicit"
    ),
}


def _read_json(
    path: Path,
    default
):
    with LOCK:

        if not path.exists():
            return default

        try:
            return json.loads(
                path.read_text(
                    encoding="utf-8"
                )
            )

        except Exception:
            return default


def _write_json(
    path: Path,
    data
):
    with LOCK:

        temp = path.with_suffix(
            path.suffix + ".tmp"
        )

        temp.write_text(
            json.dumps(
                data,
                ensure_ascii=False,
                indent=2
            ),
            encoding="utf-8"
        )

        temp.replace(path)


def get_history():
    return _read_json(
        HISTORY_FILE,
        []
    )


def save_history(history):
    _write_json(
        HISTORY_FILE,
        history[-200:]
    )


def add_history(record):
    history = get_history()

    history.append(record)

    save_history(history)


def get_settings():
    settings = _read_json(
        SETTINGS_FILE,
        DEFAULT_SETTINGS.copy()
    )

    merged = DEFAULT_SETTINGS.copy()
    merged.update(settings)

    return merged


def save_settings(settings):
    _write_json(
        SETTINGS_FILE,
        settings
    )


def update_settings(**kwargs):
    settings = get_settings()

    for key, value in kwargs.items():

        if value is not None:
            settings[key] = value

    save_settings(settings)

    return settings
