import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data"
GENERATED_DIR = DATA_DIR / "generated"

DATA_DIR.mkdir(parents=True, exist_ok=True)
GENERATED_DIR.mkdir(parents=True, exist_ok=True)


# =========================
# REQUIRED
# =========================

GEMINI_API_KEY = os.getenv(
    "GEMINI_API_KEY",
    ""
).strip()

BOT_TOKEN = os.getenv(
    "BOT_TOKEN",
    ""
).strip()

ADMIN_ID = os.getenv(
    "ADMIN_ID",
    ""
).strip()


# =========================
# CONTENT
# =========================

TELEGRAM_CHANNEL = os.getenv(
    "TELEGRAM_CHANNEL",
    "@yourchannel"
).strip()

CONTENT_LANGUAGE = os.getenv(
    "CONTENT_LANGUAGE",
    "Hinglish"
).strip()


# =========================
# GEMINI
# =========================

TEXT_MODEL = os.getenv(
    "GEMINI_TEXT_MODEL",
    "gemini-3.6-flash"
).strip()

IMAGE_MODEL = os.getenv(
    "GEMINI_IMAGE_MODEL",
    "gemini-3.1-flash-image"
).strip()


# =========================
# SCHEDULER
# =========================

POST_INTERVAL_HOURS = max(
    1,
    int(
        os.getenv(
            "POST_INTERVAL_HOURS",
            "6"
        )
    )
)

DAILY_GENERATION_LIMIT = max(
    1,
    int(
        os.getenv(
            "DAILY_GENERATION_LIMIT",
            "3"
        )
    )
)


# =========================
# SERVER
# =========================

PORT = int(
    os.getenv(
        "PORT",
        "10000"
    )
)


# =========================
# FILES
# =========================

HISTORY_FILE = DATA_DIR / "history.json"
SETTINGS_FILE = DATA_DIR / "settings.json"


def validate_config():
    missing = []

    if not GEMINI_API_KEY:
        missing.append("GEMINI_API_KEY")

    if not BOT_TOKEN:
        missing.append("BOT_TOKEN")

    if not ADMIN_ID:
        missing.append("ADMIN_ID")

    if missing:
        raise RuntimeError(
            "Missing environment variables: "
            + ", ".join(missing)
        )
