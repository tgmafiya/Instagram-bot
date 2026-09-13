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
    GENERATED_DIR,
)

from storage import (
    get_history,
    add_history,
    get_settings,
)


logger = logging.getLogger(__name__)


client = genai.Client(
    api_key=GEMINI_API_KEY
)


def make_id(text: str) -> str:
    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()[:20]


def clean_json(text: str) -> str:

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
    settings = get_settings()

    history = get_history()

    recent_topics = [
        x.get("topic", "")
        for x in history[-30:]
        if x.get("topic")
    ]

    channel = (
        settings.get("telegram_channel")
        or ""
    )

    prompt = f"""
Create ONE original Instagram post concept
for an Indian Gen-Z meme/entertainment page.

Language:
{settings.get("content_style", "Hinglish")}

Requirements:

- Funny
- Clever
- Highly shareable
- Short and memorable
- Current social-media style
- Mild double-meaning humor is allowed
- The joke may have an implication that adults understand
- It must remain non-explicit
- No pornography
- No nudity
- No sexual acts
- No explicit sexual descriptions
- No minors
- No hate
- No harassment
- No dangerous instructions
- No copied viral caption
- Do not imitate a specific creator
- Do not use copyrighted characters

Telegram promotion:

{channel}

If the Telegram channel is empty,
do not invent a channel.

Avoid repeating these topics:

{json.dumps(recent_topics, ensure_ascii=False)}

Return ONLY valid JSON.

Schema:

{{
  "topic": "short topic",
  "image_prompt": "original image concept",
  "caption": "complete Instagram caption",
  "hashtags": [
    "#example1",
    "#example2",
    "#example3",
    "#example4",
    "#example5"
  ]
}}
"""

    interaction = client.interactions.create(
        model=TEXT_MODEL,
        input=prompt,
        generation_config={
            "thinking_level": "low"
        }
    )

    raw = clean_json(
        interaction.output_text
    )

    if not raw:
        raise RuntimeError(
            "Gemini returned empty text."
        )

    try:
        data = json.loads(raw)

    except json.JSONDecodeError as exc:

        logger.error(
            "Gemini invalid JSON: %s",
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
                f"Missing field: {key}"
            )

    if not isinstance(
        data["hashtags"],
        list
    ):
        data["hashtags"] = []

    return data


def generate_image(
    image_prompt: str,
    post_id: str
):

    prompt = f"""
Create an ORIGINAL Instagram image.

Format:
- vertical social-media composition
- visually attractive
- modern Indian internet culture
- funny
- clever
- meme-friendly
- clean
- polished

The humor can be mildly suggestive or
double-meaning, but the visual itself must
remain suitable for a general audience.

STRICTLY AVOID:

- nudity
- pornography
- explicit sexual activity
- graphic sexual content
- minors in sexualized situations
- real-person impersonation
- copyrighted characters
- copied logos
- hateful imagery

Concept:

{image_prompt}
"""

    interaction = client.interactions.create(
        model=IMAGE_MODEL,
        input=prompt,
        response_format={
            "type": "image",
            "aspect_ratio": "4:5",
            "image_size": "1K"
        }
    )

    image = getattr(
        interaction,
        "output_image",
        None
    )

    if image is None:
        raise RuntimeError(
            "Gemini returned no image."
        )

    data = image.data

    if isinstance(data, str):
        data = base64.b64decode(data)

    output = (
        GENERATED_DIR /
        f"{post_id}.png"
    )

    output.write_bytes(data)

    return output


def build_caption(data):

    settings = get_settings()

    caption = str(
        data.get(
            "caption",
            ""
        )
    ).strip()

    tags = []

    for tag in data.get(
        "hashtags",
        []
    ):

        tag = str(tag).strip()

        if not tag:
            continue

        if not tag.startswith("#"):
            tag = "#" + tag

        tags.append(tag)

    channel = (
        settings.get(
            "telegram_channel"
        )
        or ""
    ).strip()

    if channel:

        caption += (
            "\n\n🔥 More content: "
            + channel
        )

    if tags:

        caption += (
            "\n\n"
            + " ".join(tags)
        )

    return caption.strip()


def create_content():

    data = generate_post()

    fingerprint = (
        data["topic"]
        + "|"
        + data["caption"]
    )

    post_id = make_id(
        fingerprint
    )

    history = get_history()

    duplicate = any(
        item.get("id") == post_id
        for item in history
    )

    if duplicate:

        raise RuntimeError(
            "Duplicate post detected."
        )

    image_path = generate_image(
        data["image_prompt"],
        post_id
    )

    caption = build_caption(
        data
    )

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

    add_history(record)

    return record
