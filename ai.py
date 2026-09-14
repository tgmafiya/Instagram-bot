import asyncio
import hashlib
import json
import os
import re
import uuid

from google import genai

from config import (
    GEMINI_API_KEY,
    GEMINI_TEXT_MODEL,
    GEMINI_IMAGE_MODEL,
    CONTENT_LANGUAGE,
    CONTENT_STYLE,
    TELEGRAM_CHANNEL,
    MEDIA_DIR,
)

from storage import find_duplicate


if not GEMINI_API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY is missing."
    )


client = genai.Client(
    api_key=GEMINI_API_KEY
)


def clean_json_text(text: str) -> str:
    text = text.strip()

    if text.startswith("```"):
        text = re.sub(
            r"^```(?:json)?",
            "",
            text,
            flags=re.IGNORECASE,
        )

        text = re.sub(
            r"```$",
            "",
            text,
        )

    return text.strip()


def extract_json(text: str):
    text = clean_json_text(text)

    try:
        return json.loads(text)
    except Exception:
        pass

    start = text.find("{")
    end = text.rfind("}")

    if start >= 0 and end > start:
        return json.loads(
            text[start:end + 1]
        )

    raise ValueError(
        "Gemini did not return valid JSON."
    )


async def generate_content():
    prompt = f"""
You are the content strategist for an Instagram page.

Create ONE original highly shareable Instagram post.

Language:
{CONTENT_LANGUAGE}

Style:
{CONTENT_STYLE}

Telegram channel to promote:
{TELEGRAM_CHANNEL}

The content should feel:
- modern
- clever
- humorous
- highly relatable
- Gen-Z friendly
- curiosity-driven
- premium
- visually interesting

A mild teasing/double-meaning tone is acceptable,
but DO NOT create:
- pornography
- explicit sexual content
- sexual acts
- nudity
- sexualized minors
- hate
- harassment
- dangerous instructions
- illegal instructions
- copied captions
- copyrighted character imitation

The post must NOT claim guaranteed virality.

Return ONLY valid JSON.

Required structure:

{{
  "topic": "short topic",
  "image_prompt": "detailed safe image generation prompt",
  "caption": "complete Instagram caption",
  "hashtags": ["hashtag1", "hashtag2", "hashtag3", "hashtag4", "hashtag5"]
}}

Make the image prompt suitable for a vertical Instagram image.

The image should be:
- 4:5 portrait
- social-media friendly
- visually attractive
- realistic or premium editorial style
- no logos
- no watermark
- no readable text inside the image
"""

    interaction = await asyncio.to_thread(
        client.interactions.create,
        model=GEMINI_TEXT_MODEL,
        input=prompt,
    )

    text = getattr(
        interaction,
        "output_text",
        None,
    )

    if not text:
        raise RuntimeError(
            "Gemini returned no text."
        )

    data = extract_json(text)

    topic = str(
        data.get("topic", "")
    ).strip()

    image_prompt = str(
        data.get("image_prompt", "")
    ).strip()

    caption = str(
        data.get("caption", "")
    ).strip()

    hashtags = data.get(
        "hashtags",
        [],
    )

    if not topic:
        raise RuntimeError(
            "AI topic is empty."
        )

    if not image_prompt:
        raise RuntimeError(
            "AI image prompt is empty."
        )

    if not caption:
        raise RuntimeError(
            "AI caption is empty."
        )

    if not isinstance(
        hashtags,
        list,
    ):
        hashtags = []

    hashtags = [
        str(x).strip()
        for x in hashtags
        if str(x).strip()
    ]

    hashtags = hashtags[:15]

    if TELEGRAM_CHANNEL:
        caption += (
            f"\n\n📲 More updates: {TELEGRAM_CHANNEL}"
        )

    if hashtags:
        caption += (
            "\n\n"
            + " ".join(
                h if h.startswith("#") else f"#{h}"
                for h in hashtags
            )
        )

    return {
        "topic": topic,
        "image_prompt": image_prompt,
        "caption": caption,
        "hashtags": hashtags,
    }


async def generate_image(
    image_prompt: str,
):
    os.makedirs(
        MEDIA_DIR,
        exist_ok=True,
    )

    prompt = f"""
Create a high-quality Instagram portrait image.

Aspect ratio: 4:5.

Prompt:
{image_prompt}

Requirements:
- safe for Instagram
- no nudity
- no explicit sexual content
- no sexual acts
- no minors
- no copyrighted logos
- no watermark
- no visible text
- polished professional composition
- realistic social-media aesthetic
"""

    interaction = await asyncio.to_thread(
        client.interactions.create,
        model=GEMINI_IMAGE_MODEL,
        input=prompt,
        response_format={
            "type": "image",
            "aspect_ratio": "4:5",
            "image_size": "1K",
        },
    )

    output_image = getattr(
        interaction,
        "output_image",
        None,
    )

    if output_image is None:
        raise RuntimeError(
            "Gemini did not return an image."
        )

    image_data = getattr(
        output_image,
        "data",
        None,
    )

    if not image_data:
        raise RuntimeError(
            "Gemini image data is empty."
        )

    post_id = uuid.uuid4().hex

    filename = (
        f"{post_id}.png"
    )

    path = os.path.join(
        MEDIA_DIR,
        filename,
    )

    if isinstance(
        image_data,
        str,
    ):
        import base64

        image_data = base64.b64decode(
            image_data
        )

    with open(
        path,
        "wb",
    ) as f:
        f.write(image_data)

    return {
        "id": post_id,
        "filename": filename,
        "path": path,
    }


def content_hash(
    topic,
    caption,
):
    raw = (
        topic.strip().lower()
        + "|"
        + caption.strip().lower()
    )

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()


async def generate_post():
    content = await generate_content()

    digest = content_hash(
        content["topic"],
        content["caption"],
    )

    if find_duplicate(digest):
        raise RuntimeError(
            "Duplicate content detected. "
            "Generate again."
        )

    image = await generate_image(
        content["image_prompt"]
    )

    content["content_hash"] = digest
    content["image"] = image

    return content
