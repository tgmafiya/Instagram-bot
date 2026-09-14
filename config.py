import os
from dotenv import load_dotenv

load_dotenv()


def env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def env_int(name: str, default: int) -> int:
    value = env(name, str(default))
    try:
        return int(value)
    except ValueError:
        return default


BOT_TOKEN = env("BOT_TOKEN")
ADMIN_ID = env_int("ADMIN_ID", 0)

GEMINI_API_KEY = env("GEMINI_API_KEY")

GEMINI_TEXT_MODEL = env(
    "GEMINI_TEXT_MODEL",
    "gemini-3.6-flash",
)

GEMINI_IMAGE_MODEL = env(
    "GEMINI_IMAGE_MODEL",
    "gemini-3.1-flash-image",
)

# Instagram / Meta
INSTAGRAM_ACCESS_TOKEN = env("INSTAGRAM_ACCESS_TOKEN")
INSTAGRAM_USER_ID = env("INSTAGRAM_USER_ID")

# Example: vXX.X
GRAPH_API_VERSION = env(
    "GRAPH_API_VERSION",
    "v24.0",
)

# Public Render URL.
# Example: https://instagram-ai-publisher.onrender.com
PUBLIC_BASE_URL = env("PUBLIC_BASE_URL").rstrip("/")

# Telegram promotion
TELEGRAM_CHANNEL = env(
    "TELEGRAM_CHANNEL",
    "@yourchannel",
)

CONTENT_LANGUAGE = env(
    "CONTENT_LANGUAGE",
    "Hinglish",
)

CONTENT_STYLE = env(
    "CONTENT_STYLE",
    "funny, clever, premium, Gen-Z, slightly teasing",
)

POST_INTERVAL_HOURS = env_int(
    "POST_INTERVAL_HOURS",
    6,
)

DAILY_POST_LIMIT = env_int(
    "DAILY_POST_LIMIT",
    3,
)

PORT = env_int(
    "PORT",
    10000,
)

MEDIA_DIR = "data/media"
DATA_DIR = "data"
