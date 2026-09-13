import base64
import hashlib
import json
import logging
import re
from datetime import datetime, timezone

from google import genai

from config import (
    GEMINI_API_KEY,
    TEXT_MODEL,
    IMAGE_MODEL,
    TELEGRAM_CHANNEL,
    GENERATED_DIR,
    HISTORY_FILE,
)

logger = logging.getLogger(__name__)

if not GEMINI_API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY is missing."
    )

client = genai.Client(
    api_key=GEMINI_API_KEY
)


def load_history():
    if not HISTORY_FILE.exists():
        return []

    try:
        return json.loads(
            HISTORY_FILE.read_text(
                encoding="utf-8"
            )
        )
    except Exception:
        logger.exception(
            "Could not read history.json"
        )
        return []


def save_history(history):
    HISTORY_FILE.write_text(
        json.dumps(
            history,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


def make_id(text):
    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()[:16]


def clean_json(text):
    text = (text or "").strip()

    text = re.sub(
        r"^```json\s*",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"^```\s*",
        "",
        text
    )

    text = re.sub(
        r"\s*```$",
        "",
        text
    )

    return text.strip()


def generate_post():
    history = load_history()

    recent_topics = [
        item.get("topic", "")
        for item in history[-20:]
        if item.get("topic")
    ]

    prompt = f"""
You are an Indian Instagram content strategist.

Create ONE ORIGINAL Instagram post concept.

STYLE:
- Hinglish
- Gen-Z
- funny
- clever
- meme-friendly
- highly shareable
- mild double-meaning humor is allowed
- implication is okay
- NOT explicit

SAFETY:
- no nudity
- no pornographic content
- no sexual acts
- no minors
- no graphic sexual language
- no hateful content
- no harassment
- no illegal instructions
- no copied content
- no copyrighted characters
- no real person's likeness

PROMOTION:
Naturally promote this Telegram channel:
{TELEGRAM_CHANNEL}

The promotion must not look like spam.

Avoid these recently used topics:
{json.dumps(recent_topics, ensure_ascii=False)}

Return ONLY valid JSON in this exact structure:

{{
  "topic": "short topic",
  "image_prompt": "detailed original image concept",
  "caption": "Instagram caption",
  "hashtags": ["hashtag1", "hashtag2", "hashtag3", "hashtag4", "hashtag5"]
}}
"""

    response = client.models.generate_content(
        model=TEXT_MODEL,
        contents=prompt
    )

    raw = clean_json(
        getattr(response, "text", "")
    )

    if not raw:
        raise RuntimeError(
            "Gemini returned an empty response."
        )

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error(
            "Invalid Gemini JSON: %s",
            raw
        )
        raise RuntimeError(
            "Gemini returned invalid JSON."
        ) from exc

    required = (
        "topic",
        "image_prompt",
        "caption",
        "hashtags"
    )

    for key in required:
        if key not in data:
            raise RuntimeError(
                f"Missing Gemini field: {key}"
            )

    if not isinstance(data["hashtags"], list):
        data["hashtags"] = []

    return data


def generate_image(image_prompt, post_id):
    prompt = f"""
Create an ORIGINAL vertical Instagram social-media image.

Visual style:
- modern Indian meme/social-media aesthetic
- visually attractive
- funny
- clever
- clean
- high quality
- suitable for general audiences
- mild suggestive humor can be implied
- NOT explicit

Do NOT include:
- nudity
- pornographic imagery
- sexual acts
- minors
- graphic sexual content
- real people's likeness
- copyrighted characters
- copied brand logos

Concept:

{image_prompt}
"""

    response = client.models.generate_content(
        model=IMAGE_MODEL,
        contents=prompt,
        config={
            "response_modalities": ["IMAGE"]
        }
    )

    candidates = getattr(
        response,
        "candidates",
        []
    )

    for candidate in candidates:
        content = getattr(
            candidate,
            "content",
            None
        )

        if not content:
            continue

        parts = getattr(
            content,
            "parts",
            []
        )

        for part in parts:
            inline_data = getattr(
                part,
                "inline_data",
                None
            )

            if not inline_data:
                continue

            image_data = inline_data.data

            if isinstance(
                image_data,
                str
            ):
                image_data = base64.b64decode(
                    image_data
                )

            output_path = (
                GENERATED_DIR /
                f"{post_id}.png"
            )

            output_path.write_bytes(
                image_data
            )

            return output_path

    raise RuntimeError(
        "Gemini did not return an image."
    )


def build_caption(data):
    caption = str(
        data.get("caption", "")
    ).strip()

    hashtags = data.get(
        "hashtags",
        []
    )

    clean_tags = []

    for tag in hashtags:
        tag = str(tag).strip()

        if not tag:
            continue

        if not tag.startswith("#"):
            tag = "#" + tag

        clean_tags.append(tag)

    promotion = ""

    if TELEGRAM_CHANNEL:
        promotion = (
            f"\n\n🔥 More content: "
            f"{TELEGRAM_CHANNEL}"
        )

    result = (
        caption
        + promotion
        + "\n\n"
        + " ".join(clean_tags)
    )

    return result.strip()


def create_content():
    data = generate_post()

    fingerprint = (
        data["topic"]
        + "|"
        + data["caption"]
    )

    post_id = make_id(fingerprint)

    history = load_history()

    if any(
        item.get("id") == post_id
        for item in history
    ):
        raise RuntimeError(
            "Duplicate content detected."
        )

    image_path = generate_image(
        data["image_prompt"],
        post_id
    )

    caption = build_caption(data)

    record = {
        "id": post_id,
        "topic": data["topic"],
        "caption": caption,
        "image": str(image_path),
        "created_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "status": "generated"
    }

    history.append(record)

    # Keep the file small.
    history = history[-100:]

    save_history(history)

    return record
