import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
GENERATED_DIR = DATA_DIR / "generated"
HISTORY_FILE = DATA_DIR / "history.json"

DATA_DIR.mkdir(parents=True, exist_ok=True)
GENERATED_DIR.mkdir(parents=True, exist_ok=True)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

TELEGRAM_CHANNEL = os.getenv(
    "TELEGRAM_CHANNEL",
    "@yourchannel"
).strip()

PORT = int(os.getenv("PORT", "10000"))

POST_INTERVAL_HOURS = max(
    1,
    int(os.getenv("POST_INTERVAL_HOURS", "6"))
)

DAILY_GENERATION_LIMIT = max(
    1,
    int(os.getenv("DAILY_GENERATION_LIMIT", "3"))
)

TEXT_MODEL = os.getenv(
    "GEMINI_TEXT_MODEL",
    "gemini-2.5-flash"
)

IMAGE_MODEL = os.getenv(
    "GEMINI_IMAGE_MODEL",
    "gemini-2.5-flash-image"
)
